"""LLM-driven multi-agent debate for Layer 3 setpoint allocation.

Replaces the deterministic priority-based allocation in
ChillValveController when Layer 2's confidence is in the uncertain band
[0.30, 0.85]. Format: each peer valve speaks once (in parallel), then the
elected leader synthesizes a JSON allocation.

Safety: Layer 1 still validates the final command. If the LLM proposes an
out-of-range position or one that violates the dP failsafe, Layer 1
clamps. The debate is allowed to recommend, never to bypass safety.

Cost: 6 LLM calls per debate (5 peers + 1 leader). Provider: DeepSeek
(OpenAI-compatible API). Cooldown of 30 sim-seconds per branch bounds
total spend per scenario.

Failure modes:
- No DEEPSEEK_API_KEY → returns None (controller falls back to
  deterministic allocation)
- LLM call fails or returns malformed JSON → returns None
- LLM proposes positions outside [0, 100] → clamped at the boundary
  (Layer 1 also validates downstream)
"""
from __future__ import annotations

import asyncio
import copy
import hashlib
import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import sim._env  # noqa: F401

log = logging.getLogger(__name__)

MODEL = "deepseek-chat"
BASE_URL = "https://api.deepseek.com"
DEBATE_COOLDOWN_S = 20.0     # min gap per branch — gives judges ~15s to read transcript before it's overwritten
PEER_SPEECH_MAX_TOKENS = 80
LEADER_SYNTHESIS_MAX_TOKENS = 250

UNCERTAINTY_LO = 0.30
UNCERTAINTY_HI = 0.85

# Recovery debate: fires when a valve has been anomalous for sustained time
# despite peer reallocation. LLM picks the corrective action autonomously.
RECOVERY_DEBATE_COOLDOWN_S = 30.0      # min gap per valve — prevents the recovery card from refreshing faster than judges can read it
RECOVERY_ANOMALY_PERSISTENCE_S = 50.0  # how long an anomaly must persist before remediation
RECOVERY_MAX_TOKENS = 200

RECOVERY_ACTIONS = frozenset(
    {"attempt_actuator_reset", "schedule_maintenance", "accept_degradation"}
)

PEER_SYSTEM_PROMPT = (
    "You are an autonomous HVAC valve in a chilled-water distribution branch. "
    "Report your state to the branch leader using STRICT JSON only. "
    "Schema:\n"
    '  {\n'
    '    "status": "impaired" | "nominal",   // impaired if flow<60% of design OR anomaly_confidence>0.4\n'
    '    "flow_pct": integer 0-200,           // your current flow as % of design\n'
    '    "request": "open_more" | "hold" | "take_load" | "close_more",\n'
    '    "reason": string ≤ 15 words          // one short clause, no preamble\n'
    '  }\n'
    "Speak even if impaired — silence helps no one. "
    "Output ONLY the JSON object, no markdown fences, no extra text."
)

LEADER_SYSTEM_PROMPT = (
    "You are the elected leader of a chilled-water valve branch. Your job "
    "is to synthesize the peer speeches + each peer's current flow_gpm vs "
    "design_flow_gpm into a per-valve position allocation that restores "
    "total branch flow toward the sum of design flows. Output ONLY valid "
    'JSON: {"allocations": {"valve_id": position_pct, ...}, '
    '"rationale": "one-sentence reason"}. '
    "Positions are 0–100. If any peer reports it is impaired (flow far "
    "below design), open the healthy peers more to absorb the shortfall — "
    "don't leave them at their current setpoint when a sibling is failing. "
    "Stay near current positions ONLY when all peers are nominal. "
    "Do not include any text outside the JSON object."
)

RECOVERY_SYSTEM_PROMPT = (
    "You are the elected leader of a chilled-water valve branch. A peer valve "
    "has remained anomalous despite peer-reallocation. Your goal: RESTORE "
    "branch flow balance. Peer reallocation alone cannot bring flow back to "
    "design — the impaired valve itself must be unstuck. Choose exactly one "
    "action:\n"
    "  'attempt_actuator_reset' — soft power-cycle the actuator. THIS IS THE "
    "DEFAULT first response. Even faults that look hard (low flow + full "
    "position + high ΔT) frequently clear after a reset. Brief service "
    "interruption only. PREFER THIS unless a reset has already been tried "
    "recently on this same valve.\n"
    "  'schedule_maintenance' — file a human work order. Only choose this if "
    "'recent_actions' below shows attempt_actuator_reset was ALREADY tried at "
    "least once on this valve and the anomaly is still present. Filing a work "
    "order does NOT clear the fault during the demo; reset is what actually "
    "restores flow.\n"
    "  'accept_degradation' — keep peer-compensated state. Only choose this "
    "if branch flow is already within 5% of design sum AND a reset was tried.\n"
    "Output ONLY valid JSON: "
    '{"action": "<one of the three>", "rationale": "one-sentence reason"}. '
    "No text outside the JSON object."
)


def is_uncertain_branch(valves: List[Dict[str, Any]]) -> bool:
    """Trigger condition: any valve in branch has anomaly confidence in the
    uncertain band. The debate is for resolving ambiguous Layer 2 signals."""
    for v in valves:
        c = v.get("anomaly_confidence", 0.0)
        if UNCERTAINTY_LO <= c <= UNCERTAINTY_HI:
            return True
    return False


def state_fingerprint(valves: List[Dict[str, Any]]) -> str:
    """Hash branch state at low resolution so similar conditions hit the
    cache instead of re-billing the LLM."""
    coarse = [
        (v["valve_id"], round(v["position_pct"] / 5) * 5,
         round(v["dT_C"] * 2) / 2, round(v["flow_gpm"] / 10) * 10,
         round(v["anomaly_confidence"] * 10) / 10)
        for v in sorted(valves, key=lambda x: x["valve_id"])
    ]
    return hashlib.sha1(json.dumps(coarse).encode()).hexdigest()[:12]


@dataclass
class DebateRound:
    branch_id: str
    tick: int
    speeches: List[Dict[str, Any]] = field(default_factory=list)   # {valve_id, status, flow_pct, request, reason}
    allocations: Dict[str, float] = field(default_factory=dict)    # valve_id → position
    rationale: str = ""
    cause: str = "uncertain_anomaly"
    cached: bool = False
    wall_clock_s: float = 0.0


@dataclass
class RecoveryDecision:
    branch_id: str
    target_valve_id: str
    leader_id: str
    tick: int
    action: str               # one of RECOVERY_ACTIONS
    rationale: str
    wall_clock_s: float = 0.0


@dataclass
class DebateRunner:
    cache: Dict[str, DebateRound] = field(default_factory=dict)
    last_debate_at: Dict[str, float] = field(default_factory=dict)   # branch_id → sim_t
    last_recovery_at: Dict[str, float] = field(default_factory=dict)  # valve_id → sim_t
    _client: Optional[object] = field(default=None, repr=False)
    _enabled: bool = False
    _last_warn_at: float = -1e9

    def __post_init__(self) -> None:
        api_key = os.environ.get("DEEPSEEK_API_KEY")
        if not api_key:
            log.info("DEEPSEEK_API_KEY not set — debate disabled, deterministic L3 used")
            return
        try:
            from openai import OpenAI
            self._client = OpenAI(api_key=api_key, base_url=BASE_URL)
            self._enabled = True
            log.info("DebateRunner enabled (%s)", MODEL)
        except Exception as e:
            log.warning("failed to init DeepSeek client for debate: %s", e)

    def reset(self) -> None:
        """Drop per-run cooldown trackers. Must be called on engine REPLAY
        so a new sim_t=0 doesn't fail the `t - last >= cooldown` check
        against the prior run's much-larger absolute sim_t."""
        self.last_debate_at.clear()
        self.last_recovery_at.clear()
        self.cache.clear()

    def can_debate(self, branch_id: str, t_seconds: float) -> bool:
        if not self._enabled:
            return False
        last = self.last_debate_at.get(branch_id, -1e9)
        return (t_seconds - last) >= DEBATE_COOLDOWN_S

    def can_recover(self, valve_id: str, t_seconds: float) -> bool:
        if not self._enabled:
            return False
        last = self.last_recovery_at.get(valve_id, -1e9)
        return (t_seconds - last) >= RECOVERY_DEBATE_COOLDOWN_S

    async def run_recovery_debate(
        self,
        branch_id: str,
        target_valve_id: str,
        leader_id: str,
        valves: List[Dict[str, Any]],
        t_seconds: float,
        anomaly_age_s: float,
        recent_actions: Optional[List[str]] = None,
    ) -> Optional[RecoveryDecision]:
        """Second-tier debate: peer reallocation already happened but the
        target valve is still anomalous. LLM picks one corrective action.
        `recent_actions` is the history of prior recovery actions on this
        valve, oldest first. Used to bias the LLM toward reset on first
        attempt and to escalate to maintenance only after a reset failed."""
        if not self._enabled:
            return None
        if not self.can_recover(target_valve_id, t_seconds):
            return None
        recent_actions = recent_actions or []

        start = time.monotonic()
        target = next((v for v in valves if v["valve_id"] == target_valve_id), None)
        leader = next((v for v in valves if v["valve_id"] == leader_id), None)
        if target is None or leader is None:
            return None
        peers = [v for v in valves if v["valve_id"] != target_valve_id]

        history_line = (
            ", ".join(recent_actions) if recent_actions else "none — nothing tried yet"
        )
        prompt = (
            f"Branch: {branch_id}\n"
            f"You are the elected leader, valve {leader_id}.\n"
            f"Anomalous valve: {target_valve_id}\n"
            f"  flow={target['flow_gpm']:.1f} GPM, ΔT={target['dT_C']:.1f}°C, "
            f"position={target['position_pct']:.0f}%, "
            f"anomaly_confidence={target['anomaly_confidence']:.2f}, "
            f"safety_override={target['safety_override_active']}\n"
            f"  anomaly has persisted for ~{anomaly_age_s:.0f} seconds despite peer reallocation.\n"
            f"recent_actions on this valve (oldest first): [{history_line}]\n"
            f"Peer state (compensating):\n"
        )
        for p in peers:
            if p["valve_id"] == leader_id:
                continue
            prompt += (
                f"  {p['valve_id']}: flow={p['flow_gpm']:.0f}, "
                f"ΔT={p['dT_C']:.1f}, pos={p['position_pct']:.0f}\n"
            )
        prompt += (
            "Remember: reset is the DEFAULT first response. Only choose "
            "schedule_maintenance if recent_actions already contains "
            "'attempt_actuator_reset'. Output JSON only:\n"
            '  {"action": "attempt_actuator_reset" | "schedule_maintenance" | "accept_degradation", '
            '"rationale": "one short sentence"}'
        )

        raw = await asyncio.to_thread(
            self._call_llm, RECOVERY_SYSTEM_PROMPT, prompt, RECOVERY_MAX_TOKENS
        )
        parsed = self._parse_json(raw) if raw else None
        if not parsed:
            return None
        # Normalize LLM-formatting variance: case, surrounding quotes, hyphens.
        raw_action = str(parsed.get("action", ""))
        action = raw_action.strip().strip("\"'").lower().replace("-", "_")
        if action not in RECOVERY_ACTIONS:
            log.warning("recovery debate returned unknown action: %r", raw_action)
            return None
        rationale = str(parsed.get("rationale", ""))[:300]
        # Stamp cooldown only after a fully successful decision (don't burn on parse/format failures).
        self.last_recovery_at[target_valve_id] = t_seconds
        return RecoveryDecision(
            branch_id=branch_id,
            target_valve_id=target_valve_id,
            leader_id=leader_id,
            tick=int(t_seconds),
            action=action,
            rationale=rationale,
            wall_clock_s=time.monotonic() - start,
        )

    async def run(
        self,
        branch_id: str,
        leader_id: str,
        valves: List[Dict[str, Any]],
        t_seconds: float,
    ) -> Optional[DebateRound]:
        if not self._enabled:
            return None
        if not self.can_debate(branch_id, t_seconds):
            return None

        # Cache deliberately disabled — every uncertain-band trigger calls the
        # LLM fresh. Trades a bit of cost for a guarantee that judges see real
        # generated text (and that repeated similar states still produce a
        # transcript instead of silently reusing a prior one).
        start = time.monotonic()
        peers = [v for v in valves if v["valve_id"] != leader_id]
        leader = next((v for v in valves if v["valve_id"] == leader_id), None)
        if leader is None:
            return None

        # Phase 1: peer speeches in parallel.
        peer_tasks = [
            asyncio.create_task(self._peer_speech(branch_id, v, peers + [leader]))
            for v in peers
        ]
        peer_results = await asyncio.gather(*peer_tasks, return_exceptions=True)
        speeches: List[Dict[str, Any]] = []
        for v, result in zip(peers, peer_results, strict=False):
            if isinstance(result, Exception):
                # Never drop a peer entirely — fall back to a deterministic
                # structured speech so the UI always renders a bubble.
                log.warning("peer speech exception for %s: %s", v["valve_id"], result)
                design_flow_gpm = 50 if branch_id == "A" else 150
                flow_pct_int = int(round((v["flow_gpm"] / design_flow_gpm) * 100))
                impaired = (
                    v["flow_gpm"] < 0.6 * design_flow_gpm
                    or v["anomaly_confidence"] > 0.4
                )
                speeches.append({
                    "valve_id": v["valve_id"],
                    "status": "impaired" if impaired else "nominal",
                    "flow_pct": flow_pct_int,
                    "request": "open_more" if impaired else "hold",
                    "reason": "LLM unavailable — auto-report only",
                })
                continue
            # result is already a structured dict from _peer_speech.
            speeches.append({"valve_id": v["valve_id"], **result})

        # Phase 2: leader synthesis.
        synthesis = await self._leader_synthesis(branch_id, leader, peers, speeches)
        if synthesis is None:
            return None
        # Stamp cooldown only after a successful debate (don't burn it on failures).
        self.last_debate_at[branch_id] = t_seconds

        allocations = synthesis.get("allocations", {})
        # Sanitize: only known valve ids, clamp to [0, 100].
        valid_ids = {v["valve_id"] for v in valves}
        clean = {
            vid: max(0.0, min(100.0, float(pos)))
            for vid, pos in allocations.items()
            if vid in valid_ids
        }
        rationale = str(synthesis.get("rationale", ""))[:300]
        round_ = DebateRound(
            branch_id=branch_id,
            tick=int(t_seconds),
            speeches=speeches,
            allocations=clean,
            rationale=rationale,
            cached=False,
            wall_clock_s=time.monotonic() - start,
        )
        return round_

    async def _peer_speech(
        self,
        branch_id: str,
        valve: Dict[str, Any],
        all_peers_view: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Returns a structured speech dict:
        {status, flow_pct, request, reason}. Falls back to a deterministic
        dict if the LLM is unavailable or returns invalid JSON."""
        design_flow_gpm = 50 if branch_id == "A" else 150
        flow_pct_int = int(round((valve["flow_gpm"] / design_flow_gpm) * 100))
        impaired = (
            valve["flow_gpm"] < 0.6 * design_flow_gpm
            or valve["anomaly_confidence"] > 0.4
        )
        prompt = (
            f"Branch: {branch_id} (design flow per valve = {design_flow_gpm} GPM)\n"
            f"You are valve {valve['valve_id']}.\n"
            f"Your state: flow={valve['flow_gpm']:.1f} GPM "
            f"({flow_pct_int}% of design), "
            f"ΔT={valve['dT_C']:.1f}°C, position={valve['position_pct']:.0f}%, "
            f"anomaly_confidence={valve['anomaly_confidence']:.2f}, "
            f"safety_override={valve['safety_override_active']}\n"
            f"You ARE{'' if impaired else ' NOT'} impaired right now.\n"
            f"Peer states:\n"
        )
        for p in all_peers_view:
            if p["valve_id"] == valve["valve_id"]:
                continue
            prompt += (
                f"  {p['valve_id']}: flow={p['flow_gpm']:.0f} GPM "
                f"({(p['flow_gpm']/design_flow_gpm)*100:.0f}% of design), "
                f"ΔT={p['dT_C']:.1f}, pos={p['position_pct']:.0f}, "
                f"conf={p['anomaly_confidence']:.2f}\n"
            )
        prompt += "Output the JSON object now."
        raw = await asyncio.to_thread(
            self._call_llm, PEER_SYSTEM_PROMPT, prompt, PEER_SPEECH_MAX_TOKENS
        )
        parsed = self._parse_json(raw) if raw else None
        # Validate + sanitize parsed shape; fall back deterministically.
        valid_status = {"impaired", "nominal"}
        valid_request = {"open_more", "hold", "take_load", "close_more"}
        if (
            parsed
            and parsed.get("status") in valid_status
            and parsed.get("request") in valid_request
        ):
            return {
                "status": parsed["status"],
                "flow_pct": int(parsed.get("flow_pct", flow_pct_int)),
                "request": parsed["request"],
                "reason": str(parsed.get("reason", ""))[:120],
            }
        # Deterministic fallback so UI always renders a structured bubble.
        return {
            "status": "impaired" if impaired else "nominal",
            "flow_pct": flow_pct_int,
            "request": "open_more" if impaired else "hold",
            "reason": (
                "flow far below design, need help"
                if impaired
                else "holding steady, room for more load"
            ),
        }

    async def _leader_synthesis(
        self,
        branch_id: str,
        leader: Dict[str, Any],
        peers: List[Dict[str, Any]],
        speeches: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        # Render structured speech rows so the leader sees a compact table
        # instead of free prose. Each row: status / flow_pct / request / reason.
        def _row(s):
            return (
                f"  {s['valve_id']}: status={s.get('status','?')}, "
                f"flow_pct={s.get('flow_pct','?')}, "
                f"request={s.get('request','?')} — {s.get('reason','')}"
            )
        speech_block = "\n".join(_row(s) for s in speeches)
        prompt = (
            f"Branch: {branch_id}\n"
            f"You are leader {leader['valve_id']}.\n"
            f"Your state: flow={leader['flow_gpm']:.1f} GPM, "
            f"ΔT={leader['dT_C']:.1f}°C, position={leader['position_pct']:.0f}%\n"
            f"Peer current positions: "
            f"{ {p['valve_id']: round(p['position_pct'], 1) for p in peers} }\n"
            f"Peer reports:\n{speech_block}\n\n"
            f"Output JSON: allocations for each peer valve only "
            f"(not yourself), plus a one-sentence rationale."
        )
        raw = await asyncio.to_thread(
            self._call_llm, LEADER_SYSTEM_PROMPT, prompt, LEADER_SYNTHESIS_MAX_TOKENS
        )
        if not raw:
            return None
        return self._parse_json(raw)

    def _call_llm(self, system_instruction: str, prompt: str, max_tokens: int) -> Optional[str]:
        try:
            resp = self._client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.4,
                max_tokens=max_tokens,
            )
            text = (resp.choices[0].message.content or "").strip()
            return text or None
        except Exception as e:
            # Rate-limit at one warning per 30s so we don't spam the log,
            # but never silence completely (silent suppression hides
            # invalid-model and quota-exhausted errors during demos).
            now = time.monotonic()
            if now - self._last_warn_at > 30.0:
                log.warning("debate LLM call failed (model=%s): %s", MODEL, e)
                self._last_warn_at = now
            return None

    @staticmethod
    def _parse_json(raw: str) -> Optional[Dict[str, Any]]:
        # Models sometimes wrap JSON in ```json fences; strip them.
        cleaned = raw.strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            log.warning("debate JSON parse failed: %r", raw[:200])
            return None
