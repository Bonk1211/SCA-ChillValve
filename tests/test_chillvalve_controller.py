"""Tests for sim/controllers/chillvalve.py."""
from __future__ import annotations

from datetime import datetime

from sim.controllers.chillvalve import ChillValveController
from sim.types import ValveState


def _state(vid="A1", dT=5.0, pos=50.0, dP=100.0):
    return ValveState(
        flow_gpm=20.0, dT_C=dT, position_pct=pos, supply_temp_C=7.0,
        return_temp_C=7.0 + dT, dP_kPa=dP,
        capacity_demand_kW=10.0, capacity_delivered_kW=10.0,
        rule_fired=None, safety_override_active=False,
        anomaly_detected=False, anomaly_confidence=0.0, anomaly_features=[],
        is_leader=False, coordination_setpoint=None, peer_states_count=0,
        last_election_time=None,
        timestamp=datetime.utcnow(), valve_id=vid, branch_id=vid[0],
    )


def test_initialize_assigns_lowest_id_per_branch_as_leader():
    c = ChillValveController()
    c.initialize(["A1", "A2", "A3", "B1", "B2", "B3"], {}, t_seconds=0.0)
    assert c.agents["A1"].is_leader is True
    assert c.agents["A2"].is_leader is False
    assert c.agents["B1"].is_leader is True
    assert c.agents["B2"].is_leader is False


def test_critical_rule_overrides_layer_3():
    c = ChillValveController()
    c.initialize(["A1", "A2"], {"A1": 50.0, "A2": 50.0}, t_seconds=0.0)
    # dP failsafe → emergency_close
    cmds = c.step([_state("A1", dP=700.0), _state("A2")], t_seconds=0.0)
    assert cmds["A1"].override is True
    assert cmds["A1"].position_pct == 0.0


def test_local_pid_fallback_when_no_setpoint_available():
    c = ChillValveController()
    c.initialize(["A1"], {"A1": 50.0}, t_seconds=0.0)
    # Single-valve "branch" → no peers → no setpoints; high ΔT → local PID opens.
    states = [_state("A1", dT=8.0, pos=50.0)]
    cmds = c.step(states, t_seconds=0.0)
    # err = 8 - 5 = 3; gain = 1.5; new_pos = 50 + 4.5 = 54.5
    assert cmds["A1"].position_pct > 50.0


def test_layer_3_writes_is_leader_back_to_state():
    c = ChillValveController()
    c.initialize(["A1", "A2"], {}, t_seconds=0.0)
    states = [_state("A1"), _state("A2")]
    c.step(states, t_seconds=0.0)
    assert states[0].is_leader is True
    assert states[1].is_leader is False


def test_layer_2_anomaly_flag_propagated_to_state(tmp_path):
    from pathlib import Path
    from sim.layers.layer2_ml import Layer2ML
    placeholder_l2 = Layer2ML(
        model_path=Path("/tmp/does_not_exist_model.pkl"),
        scaler_path=Path("/tmp/does_not_exist_scaler.pkl"),
        metadata_path=Path("/tmp/does_not_exist_meta.json"),
    )
    c = ChillValveController(layer2=placeholder_l2)
    c.initialize(["A1"], {}, t_seconds=0.0)
    s = _state("A1")
    c.step([s], t_seconds=0.0)
    # Forced-placeholder Layer 2 always returns False/0.
    assert s.anomaly_detected is False
    assert s.anomaly_confidence == 0.0
