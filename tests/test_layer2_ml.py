"""Tests for sim/layers/layer2_ml.py.

When the trained model is present in data/models/, the layer scores real
inputs. When absent, it falls back to a benign placeholder. We exercise
both paths.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from sim.layers.layer2_ml import Layer2ML
from sim.types import ValveState


def _state():
    return ValveState(
        flow_gpm=20.0, dT_C=5.0, position_pct=50.0, supply_temp_C=7.0,
        return_temp_C=12.0, dP_kPa=100.0,
        capacity_demand_kW=10.0, capacity_delivered_kW=10.0,
        rule_fired=None, safety_override_active=False,
        anomaly_detected=False, anomaly_confidence=0.0, anomaly_features=[],
        is_leader=False, coordination_setpoint=None, peer_states_count=0,
        last_election_time=None,
        timestamp=datetime.utcnow(), valve_id="A1", branch_id="A",
    )


def _force_placeholder() -> Layer2ML:
    return Layer2ML(
        model_path=Path("/tmp/does_not_exist_model.pkl"),
        scaler_path=Path("/tmp/does_not_exist_scaler.pkl"),
        metadata_path=Path("/tmp/does_not_exist_meta.json"),
    )


def test_placeholder_returns_no_anomaly_when_artifacts_missing():
    ml = _force_placeholder()
    assert ml._loaded is False
    result = ml.evaluate(_state())
    assert result.anomaly_detected is False
    assert result.confidence == 0.0
    assert result.raw_score == 0.0
    assert result.features == []


def test_placeholder_preserves_state_timestamp():
    ml = _force_placeholder()
    s = _state()
    result = ml.evaluate(s)
    assert result.timestamp == s.timestamp


def test_real_model_loads_when_artifacts_present():
    """When the trained Isolation Forest is present, the layer loads it."""
    ml = Layer2ML()  # default paths under data/models/
    if not Path("data/models/isolation_forest.pkl").exists():
        # No model in this repo state — skip the live-model assertions.
        return
    assert ml._loaded is True
    result = ml.evaluate(_state(), tick_seconds=0)
    # Real scores are non-zero and features list is populated.
    assert len(result.features) == 5
    assert isinstance(result.confidence, float)


def test_real_model_builds_5_element_feature_vector_in_order():
    from sim.layers.layer2_ml import _build_feature_vector
    s = _state()
    s.position_pct = 50.0
    s.dT_C = 5.0
    s.flow_gpm = 22.0
    features = _build_feature_vector(s, tick_seconds=43200)  # noon
    assert len(features) == 5
    assert features[0] == 0.5      # position_pct / 100 = CHWC_VLV
    assert features[1] == 5.0      # dT_C = dT_coil
    assert features[2] == 22.0     # flow_gpm = SA_CFM
    # hour_sin/cos at noon = (sin(π), cos(π)) ≈ (0, -1)
    assert abs(features[3]) < 1e-6
    assert abs(features[4] - (-1.0)) < 1e-6
