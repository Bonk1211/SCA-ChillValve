"""LLM-backed explanations for leader-change events.

Operator-facing only. Does NOT participate in the control loop — Layer 1
deterministic rules, Layer 2 ML inference, and Layer 3 bully election all
run identically regardless of whether explanations are enabled. The
explainer reads events that already happened and generates a one-line
narration for the dashboard's event log.

Provider: Gemini 2.5 Flash via google-genai. Cheap, fast (~0.5–1s),
caches deterministically.

Failure modes:
- GEMINI_API_KEY (or GOOGLE_API_KEY) not set → falls back to a
  deterministic explanation string. No exception, no log spam.
- Network error / quota exceeded → falls back, logs a single warning.
"""
from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass, field
from typing import Dict, Optional

import sim._env  # noqa: F401  — auto-loads .env

log = logging.getLogger(__name__)

MODEL = "gemini-2.5-flash"

SYSTEM_PROMPT = (
    "You are an HVAC operator's assistant. You narrate leader-election events "
    "in a distributed valve-control system. Each branch (A or B) has a 'leader' "
    "valve that coordinates flow allocation among its peers using a bully "
    "algorithm. When the current leader stops sending heartbeats, the "
    "lowest-id remaining valve wins re-election within ~20 simulated seconds. "
    "Write a single concise sentence (≤ 25 words) explaining what happened, "
    "phrased for a building operator looking at a dashboard event log. "
    "Avoid jargon like 'bully' or 'heartbeat'. State the practical outcome."
)


@dataclass
class Explainer:
    cache: Dict[str, str] = field(default_factory=dict)
    _client: Optional[object] = field(default=None, repr=False)
    _enabled: bool = False
    _warned: bool = False

    def __post_init__(self) -> None:
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            log.info("Gemini API key not set — explanations will use deterministic fallback")
            return
        try:
            from google import genai
            self._client = genai.Client(api_key=api_key)
            self._enabled = True
            log.info("Gemini explainer enabled (%s)", MODEL)
        except Exception as e:
            log.warning("failed to init Gemini client: %s", e)

    async def explain_leader_change(
        self,
        branch_id: str,
        previous_leader: Optional[str],
        new_leader: str,
        cause: str,
        t_seconds: float,
    ) -> str:
        key = f"{branch_id}|{previous_leader}|{new_leader}|{cause}"
        if key in self.cache:
            return self.cache[key]

        if not self._enabled:
            text = self._fallback(branch_id, previous_leader, new_leader, cause)
        else:
            text = await asyncio.to_thread(
                self._sync_call, branch_id, previous_leader, new_leader, cause, t_seconds
            )
        self.cache[key] = text
        return text

    def _sync_call(self, branch_id, previous_leader, new_leader, cause, t_seconds) -> str:
        prompt = (
            f"Branch: {branch_id}\n"
            f"Previous leader: {previous_leader or '(none, boot)'}\n"
            f"New leader: {new_leader}\n"
            f"Cause: {cause}\n"
            f"Simulated time: t={t_seconds:.0f}s\n"
        )
        try:
            from google.genai import types
            resp = self._client.models.generate_content(
                model=MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    temperature=0.4,
                    max_output_tokens=80,
                ),
            )
            text = (resp.text or "").strip()
            if not text:
                return self._fallback(branch_id, previous_leader, new_leader, cause)
            return text
        except Exception as e:
            if not self._warned:
                log.warning("Gemini call failed (further warnings suppressed): %s", e)
                self._warned = True
            return self._fallback(branch_id, previous_leader, new_leader, cause)

    @staticmethod
    def _fallback(branch_id, previous_leader, new_leader, cause) -> str:
        if previous_leader is None:
            return f"Branch {branch_id}: {new_leader} elected as initial leader at boot."
        if cause == "killed":
            return (
                f"Branch {branch_id}: {previous_leader} stopped responding; "
                f"{new_leader} took over as new leader within ~20 simulated seconds."
            )
        return f"Branch {branch_id}: leader changed from {previous_leader} to {new_leader} ({cause})."
