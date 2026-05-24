"""Scenario definitions and load disturbance generators. PRD §4.4."""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import List


@dataclass
class Scenario:
    """A scenario describes per-tick load fractions per valve."""

    name: str
    duration_seconds: int
    base_load_fraction: float
    fluctuation_amplitude: float    # ± fraction
    fluctuation_period_seconds: int
    valve_ids: List[str] = field(default_factory=list)

    def load_fraction(self, valve_id: str, t_seconds: int) -> float:
        # Per-valve phase offset prevents synchronous peaks.
        phase = (hash(valve_id) % 1000) / 1000.0
        omega = 2.0 * math.pi / self.fluctuation_period_seconds
        delta = self.fluctuation_amplitude * math.sin(omega * t_seconds + phase * 2 * math.pi)
        return max(0.0, self.base_load_fraction + delta)

    @classmethod
    def load(cls, path: Path) -> "Scenario":
        return cls(**json.loads(path.read_text()))
