"""Tests for sim/layers/layer1_rules.py — PRD §5.1."""
from __future__ import annotations

from datetime import datetime

import pytest

from sim.layers.layer1_rules import CRITICAL_ACTIONS, Layer1Rules
from sim.types import ValveState


def _state(vid="A1", flow=20.0, dT=5.0, pos=50.0, dP=100.0):
    return ValveState(
        flow_gpm=flow, dT_C=dT, position_pct=pos, supply_temp_C=7.0,
        return_temp_C=7.0 + dT, dP_kPa=dP,
        capacity_demand_kW=10.0, capacity_delivered_kW=8.0,
        rule_fired=None, safety_override_active=False,
        anomaly_detected=False, anomaly_confidence=0.0, anomaly_features=[],
        is_leader=False, coordination_setpoint=None, peer_states_count=0,
        last_election_time=None,
        timestamp=datetime.utcnow(), valve_id=vid, branch_id=vid[0],
    )


def test_happy_path_returns_none():
    r = Layer1Rules(flow_max_gpm_per_valve={"A1": 50.0})
    assert r.evaluate(_state(), 0.0) is None


def test_rule1_position_out_of_bounds_fires_clamp():
    r = Layer1Rules()
    action = r.evaluate(_state(pos=120.0), 0.0)
    assert action is not None
    assert action.action == "clamp_position"
    assert action.value == 100.0
    assert action.reason == "position_out_of_bounds"


def test_rule2_flow_ceiling_fires_at_110pct():
    r = Layer1Rules(flow_max_gpm_per_valve={"A1": 50.0})
    # 55.1 GPM > 50 × 1.10 = 55.0 → fires.
    action = r.evaluate(_state(flow=55.1, pos=50.0), 0.0)
    assert action is not None
    assert action.action == "reduce_position"
    assert action.value == pytest.approx(45.0)
    assert action.reason == "flow_exceeds_max_110pct"


def test_rule2_no_fire_without_flow_max_configured():
    r = Layer1Rules()  # no flow_max configured
    assert r.evaluate(_state(flow=99999.0), 0.0) is None


def test_rule3_dP_failsafe_fires_emergency_close():
    r = Layer1Rules(flow_max_gpm_per_valve={"A1": 50.0})
    action = r.evaluate(_state(dP=700.0), 0.0)
    assert action is not None
    assert action.action == "emergency_close"
    assert action.value == 0.0
    assert action.action in CRITICAL_ACTIONS


def test_rule4_sensor_nan_returns_last_known_good():
    r = Layer1Rules(flow_max_gpm_per_valve={"A1": 50.0})
    r.evaluate(_state(flow=20.0), 0.0)  # populate last_known_good
    action = r.evaluate(_state(flow=float("nan")), 1.0)
    assert action is not None
    assert action.action == "use_last_known_good"
    assert action.value == 20.0
    assert action.action in CRITICAL_ACTIONS


def test_rule5_actuator_timeout_after_30s_with_divergence():
    r = Layer1Rules(flow_max_gpm_per_valve={"A1": 50.0})
    # Commanded 0.30, actual 0.50 (divergence > 0.05), time > 30s.
    r.record_command("A1", 0.30, t_seconds=0.0)
    action = r.evaluate(_state(pos=50.0), t_seconds=31.0)
    assert action is not None
    assert action.action == "raise_fault"
    assert action.reason == "actuator_unresponsive"


def test_validate_command_clamps_to_unit_range():
    r = Layer1Rules()
    assert r.validate_command(150.0, _state()) == 100.0
    assert r.validate_command(-5.0, _state()) == 0.0
    assert r.validate_command(50.0, _state()) == 50.0


def test_validate_command_forces_zero_on_dp_failsafe():
    r = Layer1Rules()
    assert r.validate_command(80.0, _state(dP=700.0)) == 0.0


def test_critical_actions_set_contains_expected_members():
    expected = {"emergency_close", "use_last_known_good", "raise_fault"}
    assert CRITICAL_ACTIONS == expected
