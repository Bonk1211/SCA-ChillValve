"""6-valve hydraulic system with shared pump. PRD §4."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Tuple

from scipy.optimize import brentq

from sim.coil import Coil
from sim.pump import Pump
from sim.types import ValveCommand, ValveSpec, ValveState
from sim.valve import Valve

# Branch topology per PRD §4.1. tuple = (valve_id, spec, design_flow_gpm)
BRANCH_TOPOLOGY: Dict[str, List[Tuple[str, ValveSpec, float]]] = {
    "A": [
        ("A1", ValveSpec.DN65, 50.0),
        ("A2", ValveSpec.DN65, 50.0),
        ("A3", ValveSpec.DN65, 50.0),
    ],
    "B": [
        ("B1", ValveSpec.DN100, 150.0),
        ("B2", ValveSpec.DN100, 150.0),
        ("B3", ValveSpec.DN100, 150.0),
    ],
}

SUPPLY_TEMP_C = 7.0   # PRD §4.1
DESIGN_DT_C = 5.0     # PRD §4.1


@dataclass
class ValveRecord:
    """Static metadata + mutable per-tick state for one valve."""

    valve_id: str
    branch_id: str
    spec: ValveSpec
    valve: Valve
    coil: Coil
    position: float = 0.5
    commanded_position: float = 0.5


@dataclass
class HydraulicSystem:
    """6-valve / 2-branch network with one shared pump.

    Per tick: given current valve positions and the pump curve, solves the
    network for total flow by 1-D root finding (pump curve == valve-supply curve).
    """

    pump: Pump = field(default_factory=Pump)
    valves: Dict[str, ValveRecord] = field(default_factory=dict)

    @classmethod
    def build_default(cls) -> "HydraulicSystem":
        sys = cls()
        for branch_id, members in BRANCH_TOPOLOGY.items():
            for vid, spec, design_flow in members:
                sys.valves[vid] = ValveRecord(
                    valve_id=vid,
                    branch_id=branch_id,
                    spec=spec,
                    valve=Valve(spec=spec),
                    coil=Coil(design_flow_gpm=design_flow, design_dT_C=DESIGN_DT_C),
                )
        return sys

    def set_positions(self, commands: Dict[str, ValveCommand]) -> None:
        for vid, cmd in commands.items():
            rec = self.valves[vid]
            rec.commanded_position = max(0.0, min(1.0, cmd.position_pct / 100.0))
            # Phase 2 assumes instantaneous actuator.
            rec.position = rec.commanded_position

    def _total_supply_at_head(self, head_kpa: float) -> float:
        """Sum of valve flows in both branches at a common available head."""
        return sum(
            rec.valve.flow_gpm(rec.position, head_kpa)
            for rec in self.valves.values()
        )

    def solve_network(self) -> float:
        """Return equilibrium total flow [GPM] where pump curve == valve-supply curve."""

        def residual(q: float) -> float:
            head = self.pump.head_kpa(q)
            return self._total_supply_at_head(head) - q

        lo, hi = 1e-6, self.pump.max_flow_gpm - 1e-6
        f_lo = residual(lo)
        f_hi = residual(hi)
        if f_lo <= 0:
            return 0.0
        if f_hi >= 0:
            return hi
        return brentq(residual, lo, hi, xtol=1e-3)

    def tick(self, t_seconds: int) -> List[ValveState]:
        total_flow = self.solve_network()
        head = self.pump.head_kpa(total_flow)
        now = datetime.utcnow()
        out: List[ValveState] = []
        for rec in self.valves.values():
            flow = rec.valve.flow_gpm(rec.position, head)
            dT = rec.coil.achieved_dT(flow)
            out.append(ValveState(
                flow_gpm=flow,
                dT_C=dT,
                position_pct=rec.position * 100.0,
                supply_temp_C=SUPPLY_TEMP_C,
                return_temp_C=SUPPLY_TEMP_C + dT,
                dP_kPa=head,
                capacity_demand_kW=rec.coil.capacity_demand_kw,
                capacity_delivered_kW=rec.coil.delivered_capacity_kw(flow),
                rule_fired=None,
                safety_override_active=False,
                anomaly_detected=False,
                anomaly_confidence=0.0,
                anomaly_features=[],
                is_leader=False,
                coordination_setpoint=None,
                peer_states_count=0,
                last_election_time=None,
                timestamp=now,
                valve_id=rec.valve_id,
                branch_id=rec.branch_id,
            ))
        return out

    def pump_power_kw(self) -> float:
        q = self.solve_network()
        return self.pump.power_kw(q, self.pump.head_kpa(q))
