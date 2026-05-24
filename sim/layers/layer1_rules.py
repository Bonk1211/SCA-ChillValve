"""Layer 1 — deterministic rules. PRD §5.1.

Fires every tick. Microsecond response. Never overridden by Layer 2 or 3.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

from sim.types import RuleAction, ValveState

CRITICAL_ACTIONS = frozenset({"emergency_close", "use_last_known_good", "raise_fault"})

FLOW_CEILING_MULTIPLIER = 1.10
DP_FAILSAFE_KPA = 600.0
ACTUATOR_TIMEOUT_S = 30.0
ACTUATOR_TOLERANCE = 0.05


def _isnan_or_outlier(v: float) -> bool:
    if v is None:
        return True
    return isinstance(v, float) and (math.isnan(v) or math.isinf(v))


@dataclass
class Layer1Rules:
    """Deterministic rules. Always active. Cannot be overridden."""

    flow_max_gpm_per_valve: Dict[str, float] = field(default_factory=dict)
    last_known_good: Dict[str, Tuple[float, float, float]] = field(default_factory=dict)
    # valve_id -> (commanded_position_unit, t_commanded_seconds)
    commanded_position_timestamps: Dict[str, Tuple[float, float]] = field(default_factory=dict)

    def evaluate(self, state: ValveState, t_seconds: float) -> Optional[RuleAction]:
        vid = state.valve_id

        # Rule 1: position clamp (informational - HydraulicSystem clamps too).
        if not 0.0 <= state.position_pct <= 100.0:
            return RuleAction(
                action="clamp_position",
                value=max(0.0, min(100.0, state.position_pct)),
                reason="position_out_of_bounds",
            )

        # Rule 2: flow ceiling.
        flow_max = self.flow_max_gpm_per_valve.get(vid)
        if flow_max is not None and state.flow_gpm > flow_max * FLOW_CEILING_MULTIPLIER:
            return RuleAction(
                action="reduce_position",
                value=state.position_pct * 0.9,
                reason="flow_exceeds_max_110pct",
            )

        # Rule 3: dP failsafe.
        if state.dP_kPa > DP_FAILSAFE_KPA:
            return RuleAction(
                action="emergency_close",
                value=0.0,
                reason="dP_exceeds_600kPa",
            )

        # Rule 4: sensor validity.
        if any(_isnan_or_outlier(v) for v in [state.flow_gpm, state.dT_C, state.dP_kPa]):
            last = self.last_known_good.get(vid)
            return RuleAction(
                action="use_last_known_good",
                value=last[0] if last else None,
                reason="sensor_invalid",
            )

        # Rule 5: actuator timeout.
        ts = self.commanded_position_timestamps.get(vid)
        if ts is not None:
            commanded_unit, t_commanded = ts
            if (
                (t_seconds - t_commanded) > ACTUATOR_TIMEOUT_S
                and abs(state.position_pct / 100.0 - commanded_unit) > ACTUATOR_TOLERANCE
            ):
                return RuleAction(
                    action="raise_fault",
                    value=None,
                    reason="actuator_unresponsive",
                )

        # No rule fired — record last known good.
        self.last_known_good[vid] = (state.flow_gpm, state.dT_C, state.dP_kPa)
        return None

    def validate_command(self, commanded_position_pct: float, state: ValveState) -> float:
        """Final sanity check on a position command. Clamps to [0, 100]; forces 0 on dP failsafe."""
        if state.dP_kPa > DP_FAILSAFE_KPA:
            return 0.0
        return max(0.0, min(100.0, commanded_position_pct))

    def record_command(self, valve_id: str, commanded_position_unit: float, t_seconds: float) -> None:
        self.commanded_position_timestamps[valve_id] = (commanded_position_unit, t_seconds)
