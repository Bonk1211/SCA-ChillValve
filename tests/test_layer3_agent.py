"""Tests for sim/layers/layer3_agent.py."""
from __future__ import annotations

from datetime import datetime
from typing import List

from sim.broker import MessageBroker
from sim.layers.layer3_agent import (
    ELECTION_WINDOW_S,
    HEARTBEAT_TIMEOUT_S,
    ValveAgent,
)
from sim.types import ValveState


def _state(vid: str, dT: float = 5.0, pos: float = 50.0, deficit_kW: float = 0.0):
    return ValveState(
        flow_gpm=20.0, dT_C=dT, position_pct=pos, supply_temp_C=7.0,
        return_temp_C=7.0 + dT, dP_kPa=100.0,
        capacity_demand_kW=10.0 + deficit_kW,
        capacity_delivered_kW=10.0,
        rule_fired=None, safety_override_active=False,
        anomaly_detected=False, anomaly_confidence=0.0, anomaly_features=[],
        is_leader=False, coordination_setpoint=None, peer_states_count=0,
        last_election_time=None,
        timestamp=datetime.utcnow(), valve_id=vid, branch_id=vid[0],
    )


def _step_all(agents: dict, ids: List[str], t: float):
    for ag in agents.values():
        ag.broadcast_state(_state(ag.valve_id), t)
    for ag in agents.values():
        ag.process(ids, t)


def test_initial_state_has_no_peers():
    a = ValveAgent(valve_id="A1", branch_id="A", broker=MessageBroker())
    assert a.peer_states == {}
    assert a.is_leader is False


def test_two_phase_tick_collects_all_peers():
    br = MessageBroker()
    agents = {vid: ValveAgent(valve_id=vid, branch_id="A", broker=br) for vid in ["A1", "A2", "A3"]}
    agents["A1"].is_leader = True
    ids = list(agents.keys())
    for t in range(5):
        _step_all(agents, ids, float(t))
    # Every agent should see every other agent.
    assert sorted(agents["A1"].peer_states.keys()) == ["A2", "A3"]
    assert sorted(agents["A2"].peer_states.keys()) == ["A1", "A3"]
    assert sorted(agents["A3"].peer_states.keys()) == ["A1", "A2"]


def test_election_converges_to_lowest_id_after_timeout():
    br = MessageBroker()
    agents = {vid: ValveAgent(valve_id=vid, branch_id="A", broker=br) for vid in ["A1", "A2", "A3"]}
    ids = list(agents.keys())
    # No initial leader → all will trigger election after HEARTBEAT_TIMEOUT_S.
    elapsed_required = HEARTBEAT_TIMEOUT_S + ELECTION_WINDOW_S + 2.0
    for t in range(int(elapsed_required) + 1):
        _step_all(agents, ids, float(t))
    leaders = [vid for vid, ag in agents.items() if ag.is_leader]
    assert leaders == ["A1"]  # lowest id


def test_non_leader_receives_setpoint_from_leader():
    br = MessageBroker()
    agents = {vid: ValveAgent(valve_id=vid, branch_id="A", broker=br) for vid in ["A1", "A2"]}
    agents["A1"].is_leader = True
    ids = list(agents.keys())
    # Need 5 sim-seconds elapsed for COORDINATION_CADENCE_S to trigger.
    for t in range(10):
        _step_all(agents, ids, float(t))
    # A2 should have received at least one setpoint.
    # consume_setpoint pops; after multiple ticks the latest should be non-None.
    assert agents["A2"].latest_setpoint is not None


def test_consume_setpoint_is_one_shot():
    a = ValveAgent(valve_id="A2", branch_id="A", broker=MessageBroker())
    a.latest_setpoint = 75.0
    assert a.consume_setpoint() == 75.0
    assert a.consume_setpoint() is None


def test_branch_isolation_election_does_not_leak():
    br = MessageBroker()
    agents = {
        "A1": ValveAgent(valve_id="A1", branch_id="A", broker=br),
        "A2": ValveAgent(valve_id="A2", branch_id="A", broker=br),
        "B1": ValveAgent(valve_id="B1", branch_id="B", broker=br),
        "B2": ValveAgent(valve_id="B2", branch_id="B", broker=br),
    }
    ids = list(agents.keys())
    elapsed = HEARTBEAT_TIMEOUT_S + ELECTION_WINDOW_S + 2.0
    for t in range(int(elapsed) + 1):
        _step_all(agents, ids, float(t))
    # One leader per branch.
    assert agents["A1"].is_leader and not agents["A2"].is_leader
    assert agents["B1"].is_leader and not agents["B2"].is_leader
