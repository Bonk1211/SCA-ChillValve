"""End-to-end tests for fault injection scenario C and leader failover."""
from __future__ import annotations

import asyncio
import json

import pytest

from backend.orchestrator import EngineService
from sim.engine import run
from sim.scenarios import Scenario


def test_scenario_fault_severity_ramps_from_zero():
    s = Scenario(
        name="t", duration_seconds=1800, base_load_fraction=0.7,
        fluctuation_amplitude=0.0, fluctuation_period_seconds=300,
        fault_target_valve_id="B2", fault_start_seconds=60,
        fault_ramp_seconds=600, fault_max_severity=0.5,
    )
    # Before start: zero severity for any valve.
    assert s.fault_severity("B2", 0) == 0.0
    assert s.fault_severity("B2", 59) == 0.0
    # At start: zero.
    assert s.fault_severity("B2", 60) == 0.0
    # Half-way through ramp.
    assert abs(s.fault_severity("B2", 360) - 0.25) < 0.01
    # After full ramp: max severity.
    assert abs(s.fault_severity("B2", 660) - 0.5) < 0.01
    assert abs(s.fault_severity("B2", 1799) - 0.5) < 0.01
    # Non-targeted valves: always zero.
    assert s.fault_severity("A1", 1000) == 0.0
    assert s.fault_severity("B1", 1000) == 0.0


def test_scenario_fault_target_only_affects_one_valve():
    s = Scenario(
        name="t", duration_seconds=100, base_load_fraction=0.7,
        fluctuation_amplitude=0.0, fluctuation_period_seconds=10,
        fault_target_valve_id="B2", fault_start_seconds=0,
        fault_ramp_seconds=10, fault_max_severity=0.5,
    )
    for vid in ["A1", "A2", "A3", "B1", "B3"]:
        assert s.fault_severity(vid, 50) == 0.0
    assert s.fault_severity("B2", 50) > 0.0


@pytest.mark.slow
def test_fault_injection_scenario_layer2_catches_target_valve():
    """Run the fault_injection scenario and assert Layer 2 flags B2 more than peers."""
    out = run("fault_injection", "chillvalve", log_every=10**9)
    records = [json.loads(line) for line in out.read_text().splitlines()]
    counts: dict[str, int] = {}
    for r in records:
        for v in r["valves"]:
            counts.setdefault(v["valve_id"], 0)
            if v["anomaly_detected"]:
                counts[v["valve_id"]] += 1
    b2 = counts.get("B2", 0)
    peers_avg = sum(counts.get(v, 0) for v in ["A1", "A2", "A3", "B1", "B3"]) / 5
    # B2 should flag substantially more than the peer average.
    assert b2 > peers_avg * 2, f"B2={b2}, peers_avg={peers_avg:.1f}"


async def _failover_check():
    e = EngineService(tick_period_s=0.001)
    await e.start("steady_state", "chillvalve")
    await asyncio.sleep(0.1)
    agents = e._controller.agents
    assert agents["A1"].is_leader is True
    await e.kill_leader("A1")
    await asyncio.sleep(0.5)
    assert agents["A1"].is_dead is True
    assert agents["A1"].is_leader is False
    # Lowest-id non-dead branch-A valve wins.
    assert agents["A2"].is_leader is True
    await e.shutdown()


def test_kill_leader_triggers_failover_to_next_lowest_id():
    asyncio.run(_failover_check())


async def _kill_invalid():
    e = EngineService(tick_period_s=0.001)
    await e.start("steady_state", "chillvalve")
    await asyncio.sleep(0.05)
    with pytest.raises(ValueError):
        await e.kill_leader("ZZ9")
    await e.shutdown()


def test_kill_leader_rejects_unknown_valve_id():
    asyncio.run(_kill_invalid())


async def _kill_in_belimo():
    e = EngineService(tick_period_s=0.001)
    await e.start("steady_state", "belimo")
    await asyncio.sleep(0.05)
    with pytest.raises(RuntimeError):
        await e.kill_leader("A1")
    await e.shutdown()


def test_kill_leader_rejected_in_belimo_mode():
    asyncio.run(_kill_in_belimo())
