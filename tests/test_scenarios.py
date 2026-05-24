"""Tests for sim/scenarios.py."""
from __future__ import annotations

from pathlib import Path

from sim.scenarios import Scenario


def test_load_fraction_stays_within_amplitude():
    s = Scenario(
        name="t", duration_seconds=3600, base_load_fraction=0.7,
        fluctuation_amplitude=0.05, fluctuation_period_seconds=300,
    )
    for t in range(0, 3600, 17):
        f = s.load_fraction("A1", t)
        assert 0.65 <= f <= 0.75


def test_different_valves_have_different_phases():
    s = Scenario(
        name="t", duration_seconds=3600, base_load_fraction=0.7,
        fluctuation_amplitude=0.05, fluctuation_period_seconds=300,
    )
    # At t=0, phase differences should produce different load fractions.
    seen = {s.load_fraction(vid, 0) for vid in ["A1", "A2", "A3", "B1", "B2", "B3"]}
    assert len(seen) >= 3  # at least some valves differ


def test_load_fraction_never_negative():
    s = Scenario(
        name="t", duration_seconds=3600, base_load_fraction=0.05,
        fluctuation_amplitude=0.5, fluctuation_period_seconds=300,
    )
    for t in range(0, 3600, 7):
        assert s.load_fraction("A1", t) >= 0.0


def test_load_steady_state_json():
    p = Path(__file__).resolve().parents[1] / "data" / "scenarios" / "steady_state.json"
    s = Scenario.load(p)
    assert s.name == "steady_state"
    assert s.duration_seconds == 3600
    assert s.base_load_fraction == 0.70
