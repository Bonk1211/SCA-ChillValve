"""Tests for backend/orchestrator.py EngineService."""
from __future__ import annotations

import asyncio

import pytest

from backend.orchestrator import EngineService


@pytest.fixture
def engine():
    return EngineService(tick_period_s=0.001)  # very fast for tests


def test_initial_status_is_idle(engine):
    s = engine.status()
    assert s["engine"] == "idle"
    assert s["tick"] == 0
    assert s["scenario"] is None


@pytest.mark.asyncio
async def test_start_advances_tick(engine):
    await engine.start("steady_state", "chillvalve")
    await asyncio.sleep(0.05)  # let it tick a few times
    s = engine.status()
    assert s["engine"] == "running"
    assert s["tick"] > 0
    await engine.shutdown()


@pytest.mark.asyncio
async def test_pause_halts_tick(engine):
    await engine.start("steady_state", "chillvalve")
    await asyncio.sleep(0.05)
    await engine.pause()
    tick_at_pause = engine._tick
    await asyncio.sleep(0.05)
    assert engine._tick == tick_at_pause
    s = engine.status()
    assert s["engine"] == "paused"
    await engine.shutdown()


@pytest.mark.asyncio
async def test_resume_continues_tick(engine):
    await engine.start("steady_state", "chillvalve")
    await asyncio.sleep(0.02)
    await engine.pause()
    tick_at_pause = engine._tick
    await asyncio.sleep(0.02)
    await engine.resume()
    await asyncio.sleep(0.05)
    assert engine._tick > tick_at_pause
    await engine.shutdown()


@pytest.mark.asyncio
async def test_reset_returns_to_idle(engine):
    await engine.start("steady_state", "chillvalve")
    await asyncio.sleep(0.02)
    await engine.reset()
    s = engine.status()
    assert s["engine"] == "idle"
    assert s["tick"] == 0


@pytest.mark.asyncio
async def test_set_mode_swaps_controller(engine):
    await engine.start("steady_state", "chillvalve")
    await asyncio.sleep(0.02)
    await engine.set_mode("belimo")
    from sim.controllers.belimo_baseline import BelimoController
    assert isinstance(engine._controller, BelimoController)
    await engine.shutdown()


@pytest.mark.asyncio
async def test_set_mode_rejects_invalid(engine):
    await engine.start("steady_state", "chillvalve")
    with pytest.raises(ValueError):
        await engine.set_mode("bogus")
    await engine.shutdown()


@pytest.mark.asyncio
async def test_set_mode_without_start_raises(engine):
    with pytest.raises(RuntimeError):
        await engine.set_mode("belimo")


@pytest.mark.asyncio
async def test_start_invalid_mode_raises(engine):
    with pytest.raises(ValueError):
        await engine.start("steady_state", "bogus")


@pytest.mark.asyncio
async def test_start_missing_scenario_raises(engine):
    with pytest.raises(FileNotFoundError):
        await engine.start("does_not_exist", "chillvalve")


@pytest.mark.asyncio
async def test_subscriber_receives_snapshots(engine):
    await engine.start("steady_state", "chillvalve")
    q = await engine.subscribe()
    msg = await asyncio.wait_for(q.get(), timeout=1.0)
    assert msg["type"] == "state"
    assert "valves" in msg
    assert len(msg["valves"]) == 6
    await engine.unsubscribe(q)
    await engine.shutdown()
