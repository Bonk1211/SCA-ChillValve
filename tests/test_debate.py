"""Tests for backend/debate.py — multi-agent LLM debate."""
from __future__ import annotations

import asyncio

from backend.debate import (
    DEBATE_COOLDOWN_S,
    DebateRunner,
    is_uncertain_branch,
    state_fingerprint,
)


def _valve(vid, conf=0.0, pos=50.0, dT=5.0, flow=22.0):
    return {
        "valve_id": vid,
        "branch_id": vid[0],
        "flow_gpm": flow,
        "dT_C": dT,
        "position_pct": pos,
        "anomaly_confidence": conf,
        "is_leader": False,
        "anomaly_detected": False,
        "rule_fired": None,
        "safety_override_active": False,
    }


def test_uncertainty_band_detects_mid_confidence():
    valves = [_valve("A1", conf=0.10), _valve("A2", conf=0.50), _valve("A3", conf=0.05)]
    assert is_uncertain_branch(valves) is True


def test_uncertainty_band_skips_all_low_confidence():
    valves = [_valve("A1", conf=0.05), _valve("A2", conf=0.10), _valve("A3", conf=0.05)]
    assert is_uncertain_branch(valves) is False


def test_uncertainty_band_skips_all_high_confidence():
    valves = [_valve("A1", conf=0.95), _valve("A2", conf=0.90), _valve("A3", conf=0.99)]
    assert is_uncertain_branch(valves) is False


def test_state_fingerprint_groups_similar_states():
    v1 = [_valve("A1", conf=0.50, pos=50.2, flow=22.1), _valve("A2", conf=0.20)]
    v2 = [_valve("A1", conf=0.51, pos=51.0, flow=23.0), _valve("A2", conf=0.18)]
    # Rounded by store: both should hash to the same fingerprint.
    assert state_fingerprint(v1) == state_fingerprint(v2)


def test_state_fingerprint_distinguishes_different_states():
    v1 = [_valve("A1", conf=0.50, pos=50.0)]
    v2 = [_valve("A1", conf=0.50, pos=80.0)]
    assert state_fingerprint(v1) != state_fingerprint(v2)


def test_cooldown_blocks_back_to_back_debates(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "fake_key_for_init")
    r = DebateRunner()
    # First debate at t=0 → recorded.
    r.last_debate_at["A"] = 0.0
    assert r.can_debate("A", 0.0 + DEBATE_COOLDOWN_S - 1) is False
    assert r.can_debate("A", 0.0 + DEBATE_COOLDOWN_S + 1) is True


def test_no_api_key_disables_debate(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    r = DebateRunner()
    assert r._enabled is False
    # Without an API key, can_debate is always False — debate never fires.
    assert r.can_debate("A", 0.0) is False
    # run() returns None → controller falls back to deterministic L3.
    result = asyncio.run(r.run("A", "A1", [_valve("A1")], 100.0))
    assert result is None
