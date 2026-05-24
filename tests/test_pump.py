"""Tests for sim/pump.py."""
from __future__ import annotations

import math

import pytest

from sim.pump import Pump


def test_head_at_zero_flow_equals_static():
    p = Pump()
    assert math.isclose(p.head_kpa(0.0), p.static_head_kpa, rel_tol=1e-9)


def test_head_at_max_flow_equals_max():
    p = Pump()
    assert math.isclose(p.head_kpa(p.max_flow_gpm), p.max_head_kpa, rel_tol=1e-9)


def test_head_monotonically_increasing_with_flow():
    p = Pump()
    flows = [0, 100, 200, 400, 600, 800]
    heads = [p.head_kpa(q) for q in flows]
    assert all(b > a for a, b in zip(heads, heads[1:], strict=False))


def test_power_zero_at_zero_flow():
    p = Pump()
    assert p.power_kw(0.0, p.head_kpa(0.0)) == 0.0


def test_power_positive_at_operating_point():
    p = Pump()
    # 500 GPM through 200 kPa with η=0.65 → expect ~4 kW
    assert 2.0 < p.power_kw(500.0, 200.0) < 6.0


@pytest.mark.parametrize("bad_q", [-0.1, -100.0])
def test_head_raises_on_negative_flow(bad_q):
    with pytest.raises(ValueError):
        Pump().head_kpa(bad_q)


def test_power_raises_on_negative_inputs():
    p = Pump()
    with pytest.raises(ValueError):
        p.power_kw(-1.0, 100.0)
    with pytest.raises(ValueError):
        p.power_kw(100.0, -1.0)
