"""Tests that the EngineService emits explanation messages on leader changes."""
from __future__ import annotations

import asyncio

from backend.orchestrator import EngineService


async def _drain(q, timeout_per_msg=0.1, max_seconds=2.0):
    out = []
    loop = asyncio.get_event_loop()
    end = loop.time() + max_seconds
    while loop.time() < end:
        try:
            msg = await asyncio.wait_for(q.get(), timeout=timeout_per_msg)
        except asyncio.TimeoutError:
            continue
        out.append(msg)
    return out


async def _boot_emits_explanations():
    e = EngineService(tick_period_s=0.05)
    q = await e.subscribe()
    await e.start("steady_state", "chillvalve")
    await asyncio.sleep(0.3)
    msgs = await _drain(q, max_seconds=0.6)
    explanations = [m for m in msgs if m.get("type") == "explanation"]
    branches = sorted(m["branch_id"] for m in explanations)
    assert "A" in branches and "B" in branches, f"missing boot explanations: {explanations}"
    for m in explanations:
        assert m["cause"] == "boot"
        assert m["previous_leader"] is None
        assert isinstance(m["text"], str) and len(m["text"]) > 0
    await e.shutdown()


def test_boot_emits_one_explanation_per_branch():
    asyncio.run(_boot_emits_explanations())


async def _failover_emits_explanation():
    e = EngineService(tick_period_s=0.05)
    q = await e.subscribe()
    await e.start("steady_state", "chillvalve")
    await asyncio.sleep(0.3)
    await _drain(q, max_seconds=0.3)  # drain boot
    await e.kill_leader("A1")
    msgs = await _drain(q, max_seconds=3.0)
    explanations = [m for m in msgs if m.get("type") == "explanation"]
    a_failover = [m for m in explanations if m["branch_id"] == "A" and m["cause"] == "killed"]
    assert len(a_failover) >= 1
    e0 = a_failover[0]
    assert e0["previous_leader"] == "A1"
    assert e0["new_leader"] == "A2"
    assert "A1" in e0["text"] and "A2" in e0["text"]
    await e.shutdown()


def test_failover_emits_killed_explanation_with_correct_prev_and_new():
    asyncio.run(_failover_emits_explanation())
