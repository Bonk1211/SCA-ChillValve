"""LLM-driven multi-agent debate for Layer 3 setpoint allocation.

Replaces the deterministic priority-based allocation in
ChillValveController when Layer 2's confidence is in the uncertain band
[0.30, 0.85]. Format: each peer valve speaks once (in parallel), then the
elected leader synthesizes a JSON allocation.

Safety: Layer 1 still validates the final command. If the LLM proposes an
out-of-range position or one that violates the dP failsafe, Layer 1
clamps. The debate is allowed to recommend, never to bypass safety.

Cost: 6 LLM calls per debate (5 peers + 1 leader). At Gemini 2.5 Flash
rates (~$0.0003/call), full scenario costs $0.02–0.10 depending on
trigger frequency. Cooldown of 30 sim-seconds per branch bounds it.

Failure modes:
- No GEMINI_API_KEY / GOOGLE_API_KEY → returns None (controller falls
  back to deterministic allocation)
- LLM call fails or returns malformed JSON → returns None
- LLM proposes positions outside [0, 100] → clamped at the boundary
  (Layer 1 also validates downstream)
"""
from __future__ import annotations

import asyncio
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

MODEL = "gemini-2.5-flash"
DEBATE_COOLDOWN_S = 30.0     # sim-seconds per branch
PEER_SPEECH_MAX_TOKENS = 80
LEADER_SYNTHESIS_MAX_TOKENS = 250

UNCERTAINTY_LO = 0.30
UNCERTAINTY_HI = 0.85

PEER_SYSTEM_PROMPT = (
    "You are an autonomous HVAC valve in a chilled-water distribution branch. "
    "You debate your sibling valves to set the right per-valve position when "
    "the ML anomaly detector is uncertain. Speak in first person as the "
    "valve. Be terse: ≤ 25 words, one sentence. State (a) your current "
    "condition (flow, ΔT, position, anomaly status) and (b) what you want "
    "to happen next (open more, hold, close more) and why. Do not propose "
    "numbers; the leader decides allocations."
)

LEADER_SYSTEM_PROMPT = (
    "You are the elected leader of a chilled-water valve branch. Your job "
    "is to synthesize the peer speeches and your own state into a final "
    "per-valve position allocation. Output ONLY valid JSON of the form "
    '{"allocations": {"valve_id": position_pct, ...}, '
    '"rationale": "one-sentence reason"}. Positions are 0–100. Stay near '
    "current positions unless a peer's condition strongly justifies a change. "
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
class DebateRunner:
    cache: Dict[str, DebateRound] = field(default_factory=dict)
    last_debate_at: Dict[str, float] = field(default_factory=dict)   # branch_id → sim_t
    _client: Optional[object] = field(default=None, repr=False)
    _enabled: bool = False
    _warned: bool = False

    def __post_init__(self) -> None:
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            log.info("Gemini API key not set — debate disabled, deterministic L3 used")
            return
        try:
            from google import genai
            self._client = genai.Client(api_key=api_key)
            self._enabled = True
            log.info("DebateRunner enabled (%s)", MODEL)
        except Exception as e:
            log.warning("failed to init Gemini client for debate: %s", e)

    def can_debate(self, branch_id: str, t_seconds: float) -> bool:
        if not self._enabled:
            return False
        last = self.last_debate_at.get(branch_id, -1e9)
        return (t_seconds - last) >= DEBATE_COOLDOWN_S

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
        self.last_debate_at[branch_id] = t_seconds

        fingerprint = state_fingerprint(valves)
        cache_key = f"{branch_id}|{fingerprint}"
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            cached.cached = True
            cached.tick = int(t_seconds)
            return cached

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
                continue
            speeches.append({"valve_id": v["valve_id"], "text": result})

        # Phase 2: leader synthesis.
        synthesis = await self._leader_synthesis(branch_id, leader, peers, speeches)
        if synthesis is None:
            return None

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
        self.cache[cache_key] = round_
        return round_

    async def _peer_speech(
        self,
        branch_id: str,
        valve: Dict[str, Any],
        all_peers_view: List[Dict[str, Any]],
    ) -> str:
        prompt = (
            f"Branch: {branch_id}\n"
            f"You are valve {valve['valve_id']}.\n"
            f"Your state: flow={valve['flow_gpm']:.1f} GPM, "
            f"ΔT={valve['dT_C']:.1f}°C, position={valve['position_pct']:.0f}%, "
            f"anomaly_confidence={valve['anomaly_confidence']:.2f}\n"
            f"Peer states:\n"
        )
        for p in all_peers_view:
            if p["valve_id"] == valve["valve_id"]:
                continue
            prompt += (
                f"  {p['valve_id']}: flow={p['flow_gpm']:.0f}, "
                f"ΔT={p['dT_C']:.1f}, pos={p['position_pct']:.0f}, "
                f"conf={p['anomaly_confidence']:.2f}\n"
            )
        prompt += "Speak now (≤ 25 words):"
        text = await asyncio.to_thread(
            self._call_llm, PEER_SYSTEM_PROMPT, prompt, PEER_SPEECH_MAX_TOKENS
        )
        return text or "(silent)"

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
            from google.genai import types
            resp = self._client.models.generate_content(
                model=MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.4,
                    max_output_tokens=max_tokens,
                ),
            )
            text = (resp.text or "").strip()
            return text or None
        except Exception as e:
            if not self._warned:
                log.warning("debate LLM call failed (further warnings suppressed): %s", e)
                self._warned = True
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
