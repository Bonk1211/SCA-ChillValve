"""Scenario definitions and load disturbance generators. PRD §4.4."""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class Scenario:
    """A scenario describes per-tick load fractions and optional fault injection."""

    name: str
    duration_seconds: int
    base_load_fraction: float
    fluctuation_amplitude: float
    fluctuation_period_seconds: int
    valve_ids: List[str] = field(default_factory=list)

    # Optional fault injection (PRD §4.4 Scenario C).
    # Target valve's effective flow is scaled by (1 - severity), where severity
    # ramps linearly from 0 to fault_max_severity between fault_start_seconds
    # and fault_start_seconds + fault_ramp_seconds, then holds.
    fault_target_valve_id: Optional[str] = None
    fault_start_seconds: int = 0
    fault_ramp_seconds: int = 1200
    fault_max_severity: float = 0.0

    # Demo control: when true, Layer-3 LLM debate is suppressed so the scenario
    # exercises only L1 (deterministic rules) + L2 (ML anomaly detection).
    disable_debate: bool = False

    def load_fraction(self, valve_id: str, t_seconds: int) -> float:
        phase = (hash(valve_id) % 1000) / 1000.0
        omega = 2.0 * math.pi / self.fluctuation_period_seconds
        delta = self.fluctuation_amplitude * math.sin(omega * t_seconds + phase * 2 * math.pi)
        return max(0.0, self.base_load_fraction + delta)

    def fault_severity(self, valve_id: str, t_seconds: int) -> float:
        if not self.fault_target_valve_id or valve_id != self.fault_target_valve_id:
            return 0.0
        if t_seconds < self.fault_start_seconds:
            return 0.0
        elapsed = t_seconds - self.fault_start_seconds
        ramp = min(1.0, elapsed / max(1, self.fault_ramp_seconds))
        return ramp * self.fault_max_severity

    @classmethod
    def load(cls, path: Path) -> "Scenario":
        return cls(**json.loads(path.read_text()))
