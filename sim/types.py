"""Core data types for the ChillValve simulation."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List, Optional


class ValveSpec(Enum):
    """Datasheet specs from PRD §4.1."""

    DN65 = ("DN65", 47.0)    # CRAH branch (A)
    DN100 = ("DN100", 150.0)  # AHU branch (B)

    def __init__(self, label: str, cv_max: float):
        self.label = label
        self.cv_max = cv_max


RANGEABILITY = 50.0  # PRD §4.2 R = 50
SG_WATER = 1.0       # PRD §4.2


@dataclass
class ValveState:
    # Sensor inputs
    flow_gpm: float
    dT_C: float
    # 0–100 percent (dashboard-facing). Hydraulic model in sim/valve.py uses [0, 1].
    position_pct: float
    supply_temp_C: float
    return_temp_C: float
    dP_kPa: float

    # Computed
    capacity_demand_kW: float
    capacity_delivered_kW: float

    # Layer 1 output
    rule_fired: Optional[str]
    safety_override_active: bool

    # Layer 2 output
    anomaly_detected: bool
    anomaly_confidence: float
    anomaly_features: List[float]

    # Layer 3 output
    is_leader: bool
    coordination_setpoint: Optional[float]
    peer_states_count: int
    last_election_time: Optional[datetime]

    # Meta
    timestamp: datetime
    valve_id: str
    branch_id: str


@dataclass
class ValveCommand:
    position_pct: float
    override: bool = False


@dataclass
class RuleAction:
    # "clamp_position" | "reduce_position" | "emergency_close" | "use_last_known_good" | "raise_fault"
    action: str
    value: Optional[float]
    reason: str


@dataclass
class AnomalyResult:
    anomaly_detected: bool
    confidence: float
    raw_score: float
    features: List[float]
    timestamp: datetime
