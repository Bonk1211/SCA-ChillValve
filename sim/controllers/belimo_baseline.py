"""Belimo Energy Valve baseline controller. PRD §6."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from sim.types import ValveCommand, ValveState

TARGET_DT_C = 5.0
DEADBAND_C = 0.5
STEP_PCT = 2.0


@dataclass
class BelimoController:
    """Per-valve independent ΔT control. No peer awareness.

    PRD §6 logic:
      ΔT < target - 0.5  → too much flow, close (reduce position)
      ΔT > target + 0.5  → too little flow, open (increase position)
      else              → hold
    """

    target_dT_C: float = TARGET_DT_C
    deadband_C: float = DEADBAND_C
    step_pct: float = STEP_PCT

    def step(self, states: List[ValveState]) -> Dict[str, ValveCommand]:
        commands: Dict[str, ValveCommand] = {}
        for s in states:
            if s.dT_C < self.target_dT_C - self.deadband_C:
                new_pos = max(0.0, s.position_pct - self.step_pct)
            elif s.dT_C > self.target_dT_C + self.deadband_C:
                new_pos = min(100.0, s.position_pct + self.step_pct)
            else:
                new_pos = s.position_pct
            commands[s.valve_id] = ValveCommand(position_pct=new_pos)
        return commands
