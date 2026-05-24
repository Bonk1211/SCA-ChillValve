"""Tests for sim/valve.py — verifies hydraulic model against datasheet."""
from __future__ import annotations

import math

import pytest

from sim.types import RANGEABILITY, ValveSpec
from sim.valve import Valve


@pytest.mark.parametrize(
    "spec, expected_cv_max",
    [
        (ValveSpec.DN65, 47.0),
        (ValveSpec.DN100, 150.0),
    ],
)
def test_cv_at_full_open_matches_datasheet(spec, expected_cv_max):
    v = Valve(spec=spec)
    assert math.isclose(v.cv(1.0), expected_cv_max, rel_tol=1e-9)


@pytest.mark.parametrize("spec", [ValveSpec.DN65, ValveSpec.DN100])
def test_cv_at_zero_position_equals_cv_max_over_rangeability(spec):
    v = Valve(spec=spec)
    assert math.isclose(v.cv(0.0), spec.cv_max / RANGEABILITY, rel_tol=1e-9)


def test_cv_is_monotonically_increasing():
    v = Valve(spec=ValveSpec.DN65)
    positions = [i / 100 for i in range(101)]
    cvs = [v.cv(p) for p in positions]
    assert all(b > a for a, b in zip(cvs, cvs[1:], strict=False))


@pytest.mark.parametrize("bad_position", [-0.01, 1.01, -1.0, 2.0])
def test_cv_raises_on_out_of_range_position(bad_position):
    v = Valve(spec=ValveSpec.DN65)
    with pytest.raises(ValueError):
        v.cv(bad_position)


def test_flow_is_zero_when_dp_is_zero():
    v = Valve(spec=ValveSpec.DN65)
    assert v.flow_gpm(position=0.5, dP_kPa=0.0) == 0.0


def test_flow_scales_as_sqrt_of_dp():
    v = Valve(spec=ValveSpec.DN65)
    f1 = v.flow_gpm(position=0.5, dP_kPa=50.0)
    f4 = v.flow_gpm(position=0.5, dP_kPa=200.0)  # 4x dP → 2x flow
    assert math.isclose(f4 / f1, 2.0, rel_tol=1e-9)


def test_flow_raises_on_negative_dp():
    v = Valve(spec=ValveSpec.DN65)
    with pytest.raises(ValueError):
        v.flow_gpm(position=0.5, dP_kPa=-1.0)


def test_dn100_flows_more_than_dn65_at_same_position_and_dp():
    a = Valve(spec=ValveSpec.DN65)
    b = Valve(spec=ValveSpec.DN100)
    assert b.flow_gpm(0.7, 100.0) > a.flow_gpm(0.7, 100.0)
