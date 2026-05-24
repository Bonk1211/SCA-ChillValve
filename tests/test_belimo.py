"""Tests for sim/controllers/belimo_baseline.py — PRD §6."""
from __future__ import annotations

from datetime import datetime

from sim.controllers.belimo_baseline import BelimoController
from sim.types import ValveState


def _state(valve_id: str, dT: float, pos: float) -> ValveState:
    return ValveState(
        flow_gpm=10.0, dT_C=dT, position_pct=pos, supply_temp_C=7.0,
        return_temp_C=7.0 + dT, dP_kPa=100.0,
        capacity_demand_kW=0.0, capacity_delivered_kW=0.0,
        rule_fired=None, safety_override_active=False,
        anomaly_detected=False, anomaly_confidence=0.0, anomaly_features=[],
        is_leader=False, coordination_setpoint=None,
        peer_states_count=0, last_election_time=None,
        timestamp=datetime.utcnow(), valve_id=valve_id, branch_id="A",
    )


def test_low_dT_closes_valve():
    c = BelimoController(target_dT_C=5.0, deadband_C=0.5, step_pct=2.0)
    cmd = c.step([_state("A1", dT=3.0, pos=50.0)])
    assert cmd["A1"].position_pct == 48.0


def test_high_dT_opens_valve():
    c = BelimoController(target_dT_C=5.0, deadband_C=0.5, step_pct=2.0)
    cmd = c.step([_state("A1", dT=7.0, pos=50.0)])
    assert cmd["A1"].position_pct == 52.0


def test_in_deadband_holds_position():
    c = BelimoController()
    cmd = c.step([_state("A1", dT=5.2, pos=50.0)])
    assert cmd["A1"].position_pct == 50.0


def test_lower_bound_clamps_at_zero():
    c = BelimoController()
    cmd = c.step([_state("A1", dT=0.0, pos=1.0)])
    assert cmd["A1"].position_pct == 0.0


def test_upper_bound_clamps_at_one_hundred():
    c = BelimoController()
    cmd = c.step([_state("A1", dT=99.0, pos=99.0)])
    assert cmd["A1"].position_pct == 100.0


def test_multiple_valves_each_handled_independently():
    c = BelimoController()
    cmd = c.step([
        _state("A1", dT=3.0, pos=50.0),   # low → close
        _state("B2", dT=7.0, pos=50.0),   # high → open
        _state("A3", dT=5.0, pos=50.0),   # in band → hold
    ])
    assert cmd["A1"].position_pct == 48.0
    assert cmd["B2"].position_pct == 52.0
    assert cmd["A3"].position_pct == 50.0
