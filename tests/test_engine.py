"""End-to-end test for sim/engine.py — 60-min Belimo run."""
from __future__ import annotations

import json

import pytest

from sim.engine import run


@pytest.mark.slow
def test_belimo_full_scenario_produces_realistic_energy():
    out = run("steady_state", "belimo", log_every=10**9)
    assert out.exists()
    records = [json.loads(line) for line in out.read_text().splitlines()]
    assert len(records) == 3600
    # Sum pump energy
    total_kwh = sum(r["pump_kw"] for r in records) / 3600.0
    # PRD §4.1 pump has ~8 kW max; at 70% load operating ~3-5 kW expected.
    assert 1.0 <= total_kwh <= 10.0, f"got {total_kwh} kWh"
    # Mean ΔT should be near design 5°C under Belimo control.
    mean_dT = sum(st["dT_C"] for r in records for st in r["valves"]) / (len(records) * 6)
    assert 3.5 <= mean_dT <= 6.5, f"got mean_dT={mean_dT}"


def test_engine_rejects_unsupported_mode():
    with pytest.raises(ValueError):
        run("steady_state", "chillvalve")
