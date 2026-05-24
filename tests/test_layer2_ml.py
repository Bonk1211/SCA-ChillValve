"""Tests for sim/layers/layer2_ml.py — Phase 3 placeholder."""
from __future__ import annotations

from datetime import datetime

from sim.layers.layer2_ml import Layer2ML
from sim.types import ValveState


def _state():
    return ValveState(
        flow_gpm=20.0, dT_C=5.0, position_pct=50.0, supply_temp_C=7.0,
        return_temp_C=12.0, dP_kPa=100.0,
        capacity_demand_kW=10.0, capacity_delivered_kW=8.0,
        rule_fired=None, safety_override_active=False,
        anomaly_detected=False, anomaly_confidence=0.0, anomaly_features=[],
        is_leader=False, coordination_setpoint=None, peer_states_count=0,
        last_election_time=None,
        timestamp=datetime.utcnow(), valve_id="A1", branch_id="A",
    )


def test_placeholder_returns_no_anomaly():
    ml = Layer2ML()
    result = ml.evaluate(_state())
    assert result.anomaly_detected is False
    assert result.confidence == 0.0
    assert result.raw_score == 0.0
    assert result.features == []


def test_placeholder_preserves_state_timestamp():
    ml = Layer2ML()
    s = _state()
    result = ml.evaluate(s)
    assert result.timestamp == s.timestamp
