"""Tests for sim/units.py — round-trip and conversion sanity."""
from __future__ import annotations

import math

from sim.units import (
    GPM_TO_M3_PER_S,
    WATER_DENSITY_KG_PER_M3,
    gpm_to_kg_per_s,
    kpa_to_psi,
    psi_to_kpa,
)


def test_kpa_psi_round_trip():
    assert math.isclose(psi_to_kpa(kpa_to_psi(250.0)), 250.0, rel_tol=1e-9)


def test_kpa_to_psi_anchor():
    # 100 kPa ≈ 14.5038 psi
    assert math.isclose(kpa_to_psi(100.0), 14.5038, rel_tol=1e-4)


def test_gpm_to_kg_per_s_for_one_gpm_water():
    # 1 GPM water ≈ 0.0631 kg/s
    actual = gpm_to_kg_per_s(1.0)
    expected = 1.0 * GPM_TO_M3_PER_S * WATER_DENSITY_KG_PER_M3
    assert math.isclose(actual, expected, rel_tol=1e-9)
