"""Layer 3 — distributed multi-agent coordination. PRD §5.3.

Each valve runs one ValveAgent. Two-phase tick:
  Phase A: all agents broadcast their state.
  Phase B: all agents collect peer state, run election logic, leader broadcasts setpoints.

Two-phase avoids the within-tick ordering bug where the first-iterated agent
would never see its peers' broadcasts.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from sim.broker import MessageBroker
from sim.types import ValveState

HEARTBEAT_TIMEOUT_S = 15.0
ELECTION_WINDOW_S = 3.0
COORDINATION_CADENCE_S = 5.0


def _branch_member_ids(branch_id: str, all_ids: List[str]) -> List[str]:
    return [vid for vid in all_ids if vid.startswith(branch_id)]


@dataclass
class ElectionState:
    in_progress: bool = False
    started_at: float = 0.0


@dataclass
class ValveAgent:
    """Distributed agent. One per valve."""

    valve_id: str
    branch_id: str
    broker: MessageBroker
    peer_states: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    is_leader: bool = False
    last_leader_heartbeat: float = 0.0
    last_collected_at: float = -1.0
    last_setpoint_broadcast_at: float = -1e9
    latest_setpoint: Optional[float] = None
    election: ElectionState = field(default_factory=ElectionState)

    def _state_channel(self) -> str:
        return f"branch/{self.branch_id}/state"

    def _election_channel(self) -> str:
        return f"branch/{self.branch_id}/election"

    def _setpoint_channel(self) -> str:
        return f"branch/{self.branch_id}/setpoints"

    # --- Phase A: broadcast own state ---
    def broadcast_state(self, my_state: ValveState, t_seconds: float) -> None:
        self.broker.broadcast(
            self._state_channel(),
            self.valve_id,
            {
                "flow_gpm": my_state.flow_gpm,
                "dT_C": my_state.dT_C,
                "position_pct": my_state.position_pct,
                "capacity_demand_kW": my_state.capacity_demand_kW,
                "capacity_delivered_kW": my_state.capacity_delivered_kW,
                "anomaly_detected": my_state.anomaly_detected,
            },
            t_seconds,
        )

    # --- Phase B: collect peer messages, run election + leader logic ---
    def process(self, all_valve_ids: List[str], t_seconds: float) -> None:
        for msg in self.broker.collect(self._state_channel(), self.last_collected_at, t_seconds):
            if msg.sender_id != self.valve_id:
                self.peer_states[msg.sender_id] = msg.payload

        for msg in self.broker.collect(self._setpoint_channel(), self.last_collected_at, t_seconds):
            if msg.payload.get("leader_alive"):
                self.last_leader_heartbeat = t_seconds
            if not self.is_leader:
                vp = msg.payload.get("valve_setpoints", {}).get(self.valve_id)
                if vp is not None:
                    self.latest_setpoint = vp

        self._election_tick(all_valve_ids, t_seconds)

        if self.is_leader and (t_seconds - self.last_setpoint_broadcast_at) >= COORDINATION_CADENCE_S:
            self._leader_broadcast(all_valve_ids, t_seconds)

        self.last_collected_at = t_seconds

    def _election_tick(self, all_valve_ids: List[str], t_seconds: float) -> None:
        if (
            (not self.is_leader)
            and not self.election.in_progress
            and (t_seconds - self.last_leader_heartbeat) > HEARTBEAT_TIMEOUT_S
        ):
            self._start_election(t_seconds)

        if self.election.in_progress and (t_seconds - self.election.started_at) >= ELECTION_WINDOW_S:
            self._resolve_election(all_valve_ids, t_seconds)

    def _start_election(self, t_seconds: float) -> None:
        self.election.in_progress = True
        self.election.started_at = t_seconds
        self.broker.broadcast(
            self._election_channel(), self.valve_id,
            {"candidate_id": self.valve_id}, t_seconds,
        )

    def _resolve_election(self, all_valve_ids: List[str], t_seconds: float) -> None:
        candidates = {self.valve_id}
        branch_members = set(_branch_member_ids(self.branch_id, all_valve_ids))
        for msg in self.broker.collect(
            self._election_channel(), self.election.started_at - 1e-9, t_seconds,
        ):
            cid = msg.payload.get("candidate_id")
            if cid in branch_members:
                candidates.add(cid)
        new_leader = min(candidates)
        self.is_leader = (new_leader == self.valve_id)
        self.election.in_progress = False
        self.last_leader_heartbeat = t_seconds
        if self.is_leader:
            self.last_setpoint_broadcast_at = -1e9

    def _leader_broadcast(self, all_valve_ids: List[str], t_seconds: float) -> None:
        branch_ids = _branch_member_ids(self.branch_id, all_valve_ids)
        peer_vals = [self.peer_states.get(vid, {}) for vid in branch_ids if vid != self.valve_id]
        peer_vals = [v for v in peer_vals if v]
        total_demand = sum(v.get("capacity_demand_kW", 0.0) for v in peer_vals)

        allocations: Dict[str, float] = {}
        for vid in branch_ids:
            if vid == self.valve_id:
                continue
            vp = self.peer_states.get(vid, {})
            deficit = max(
                0.0,
                vp.get("capacity_demand_kW", 0.0) - vp.get("capacity_delivered_kW", 0.0),
            )
            anomaly_penalty = 1.5 if vp.get("anomaly_detected") else 1.0
            priority = deficit * anomaly_penalty
            current_pos = vp.get("position_pct", 50.0)
            allocations[vid] = max(0.0, min(100.0, current_pos + priority * 0.02))

        self.broker.broadcast(
            self._setpoint_channel(), self.valve_id,
            {
                "leader_id": self.valve_id,
                "leader_alive": True,
                "branch_total_demand_kW": total_demand,
                "valve_setpoints": allocations,
            },
            t_seconds,
        )
        self.last_setpoint_broadcast_at = t_seconds

    def consume_setpoint(self) -> Optional[float]:
        s = self.latest_setpoint
        self.latest_setpoint = None
        return s
