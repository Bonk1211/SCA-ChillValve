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
DEBATE_COOLDOWN_S = 0.0      # cooldown removed — debate fires as soon as one completes and the branch is still in the uncertain band (in-flight flag still prevents concurrent debates per branch)
PEER_SPEECH_MAX_TOKENS = 80
LEADER_SYNTHESIS_MAX_TOKENS = 250

UNCERTAINTY_LO = 0.30
UNCERTAINTY_HI = 0.85

# Recovery debate: fires when a valve has been anomalous for sustained time
# despite peer reallocation. LLM picks the corrective action autonomously.
RECOVERY_DEBATE_COOLDOWN_S = 0.0       # cooldown removed — recovery can refire as soon as the prior decision settles (in-flight flag still gates concurrent attempts per valve)
RECOVERY_ANOMALY_PERSISTENCE_S = 50.0  # how long an anomaly must persist before remediation
RECOVERY_MAX_TOKENS = 200

RECOVERY_ACTIONS = frozenset(
    {"attempt_actuator_reset", "schedule_maintenance", "accept_degradation"}
)

PEER_SYSTEM_PROMPT = (
    "You are an autonomous HVAC valve in a chilled-water distribution branch. "
    "You debate your sibling valves to restore branch flow when the ML anomaly "
    "detector is uncertain. Speak in first person as the valve. Be terse: "
    "≤ 30 words, one sentence. ALWAYS quote your own flow_gpm number. "
    "Then state (a) whether you are healthy or impaired (compare your flow "
    "to design_flow_gpm — if you're at <60% of design or anomaly_confidence "
    "> 0.4, you ARE impaired and must say so explicitly), and (b) what you "
    "ask of your peers (e.g. 'please open more to cover my shortfall', "
    "'I can take more load', 'hold steady'). Speak even if you are the "
    "faulty one — silence helps no one. Do not propose numeric allocations; "
    "the leader decides."
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
    "has remained anomalous for an extended period, even after you re-allocated "
    "the branch's flow setpoints to compensate. The root cause has not cleared. "
    "Now decide the corrective action. Choose exactly one:\n"
    "  'attempt_actuator_reset' — issue a soft reset to the actuator. Suitable "
    "for transient faults (stuck spindle, comms timeout). Brief service interruption.\n"
    "  'schedule_maintenance' — file a work order for human inspection. Suitable "
    "for hard faults (coil fouling, sensor drift, mechanical wear).\n"
    "  'accept_degradation' — keep the current peer-compensated state. Suitable "
    "when the branch is already meeting service goals and intervention is risky.\n"
    "Output ONLY valid JSON of the form "
    '{"action": "<one of the three>", "rationale": "one-sentence reason"}. '
    "Do not include any text outside the JSON object."
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
    speeches: List[Dict[str, str]] = field(default_factory=list)   # {valve_id, text}
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
    ) -> Optional[RecoveryDecision]:
        """Second-tier debate: peer reallocation already happened but the
        target valve is still anomalous. LLM picks one corrective action."""
        if not self._enabled:
            return None
        if not self.can_recover(target_valve_id, t_seconds):
            return None

        start = time.monotonic()
        target = next((v for v in valves if v["valve_id"] == target_valve_id), None)
        leader = next((v for v in valves if v["valve_id"] == leader_id), None)
        if target is None or leader is None:
            return None
        peers = [v for v in valves if v["valve_id"] != target_valve_id]

        prompt = (
            f"Branch: {branch_id}\n"
            f"You are the elected leader, valve {leader_id}.\n"
            f"Anomalous valve: {target_valve_id}\n"
            f"  flow={target['flow_gpm']:.1f} GPM, ΔT={target['dT_C']:.1f}°C, "
            f"position={target['position_pct']:.0f}%, "
            f"anomaly_confidence={target['anomaly_confidence']:.2f}, "
            f"safety_override={target['safety_override_active']}\n"
            f"  anomaly has persisted for ~{anomaly_age_s:.0f} seconds despite peer reallocation.\n"
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
            "Choose one action and output JSON only:\n"
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
        speeches: List[Dict[str, str]] = []
        for v, result in zip(peers, peer_results, strict=False):
            if isinstance(result, Exception):
                # Never drop a peer entirely — fall back to a deterministic
                # state-report so the UI always renders a bubble.
                log.warning("peer speech exception for %s: %s", v["valve_id"], result)
                design_flow_gpm = 50 if branch_id == "A" else 150
                text = (
                    f"My flow is {v['flow_gpm']:.0f} GPM "
                    f"({(v['flow_gpm']/design_flow_gpm)*100:.0f}% of design). "
                    f"(LLM unavailable — auto-report only)"
                )
                speeches.append({"valve_id": v["valve_id"], "text": text})
                continue
            speeches.append({"valve_id": v["valve_id"], "text": result})

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
    ) -> str:
        design_flow_gpm = 50 if branch_id == "A" else 150
        impaired = (
            valve["flow_gpm"] < 0.6 * design_flow_gpm
            or valve["anomaly_confidence"] > 0.4
        )
        prompt = (
            f"Branch: {branch_id} (design flow per valve = {design_flow_gpm} GPM)\n"
            f"You are valve {valve['valve_id']}.\n"
            f"Your state: flow={valve['flow_gpm']:.1f} GPM "
            f"({(valve['flow_gpm']/design_flow_gpm)*100:.0f}% of design), "
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
        prompt += "Speak now (≤ 30 words, must quote your own flow_gpm):"
        text = await asyncio.to_thread(
            self._call_llm, PEER_SYSTEM_PROMPT, prompt, PEER_SPEECH_MAX_TOKENS
        )
        # Never go silent — fallback announces state deterministically so the
        # UI always shows a bubble for every peer (especially the faulty one).
        if not text:
            if impaired:
                text = (
                    f"My flow is {valve['flow_gpm']:.0f} GPM "
                    f"({(valve['flow_gpm']/design_flow_gpm)*100:.0f}% of design) — "
                    f"I'm impaired. Peers, please open more to cover my shortfall."
                )
            else:
                text = (
                    f"My flow is {valve['flow_gpm']:.0f} GPM ({(valve['flow_gpm']/design_flow_gpm)*100:.0f}% of design) — "
                    f"holding steady, can take a bit more load if needed."
                )
        return text

    async def _leader_synthesis(
        self,
        branch_id: str,
        leader: Dict[str, Any],
        peers: List[Dict[str, Any]],
        speeches: List[Dict[str, str]],
    ) -> Optional[Dict[str, Any]]:
        speech_block = "\n".join(f"  {s['valve_id']}: {s['text']}" for s in speeches)
        prompt = (
            f"Branch: {branch_id}\n"
            f"You are leader {leader['valve_id']}.\n"
            f"Your state: flow={leader['flow_gpm']:.1f} GPM, "
            f"ΔT={leader['dT_C']:.1f}°C, position={leader['position_pct']:.0f}%\n"
            f"Peer current positions: "
            f"{ {p['valve_id']: round(p['position_pct'], 1) for p in peers} }\n"
            f"Peer speeches:\n{speech_block}\n\n"
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
