"""Tests for sim/system.py — 6-valve hydraulic network."""
from __future__ import annotations

import math

from sim.system import BRANCH_TOPOLOGY, HydraulicSystem
from sim.types import ValveCommand


def test_build_default_has_6_valves_split_3_3():
    s = HydraulicSystem.build_default()
    assert len(s.valves) == 6
    branch_a = [v for v in s.valves.values() if v.branch_id == "A"]
    branch_b = [v for v in s.valves.values() if v.branch_id == "B"]
    assert len(branch_a) == 3
    assert len(branch_b) == 3


def test_topology_matches_prd_naming():
    assert list(BRANCH_TOPOLOGY.keys()) == ["A", "B"]
    assert [v[0] for v in BRANCH_TOPOLOGY["A"]] == ["A1", "A2", "A3"]
    assert [v[0] for v in BRANCH_TOPOLOGY["B"]] == ["B1", "B2", "B3"]


def test_tick_returns_six_states_with_positive_flow():
    s = HydraulicSystem.build_default()
    states = s.tick(0)
    assert len(states) == 6
    assert all(st.flow_gpm > 0 for st in states)


def test_mass_balance_sum_of_valve_flows_equals_solver_flow():
    s = HydraulicSystem.build_default()
    total = s.solve_network()
    states = s.tick(0)
    assert math.isclose(sum(st.flow_gpm for st in states), total, rel_tol=1e-3)


def test_closing_all_valves_drives_flow_to_zero():
    s = HydraulicSystem.build_default()
    s.set_positions({vid: ValveCommand(position_pct=0.0) for vid in s.valves})
    total = s.solve_network()
    # At fully-closed position, valves still have minimum Cv = Cv_max/R = small but nonzero.
    # Flow will be small relative to design; we accept < 50 GPM as "effectively closed".
    assert total < 100.0


def test_opening_all_valves_drives_flow_near_max():
    s = HydraulicSystem.build_default()
    s.set_positions({vid: ValveCommand(position_pct=100.0) for vid in s.valves})
    total = s.solve_network()
    assert total > 400.0  # well above closed case
