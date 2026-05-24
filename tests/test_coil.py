"""Tests for sim/coil.py — verifies PRD §4.2 thermal model."""
from __future__ import annotations

import math

from sim.coil import Coil


def test_dT_equals_design_at_design_flow_full_load():
    c = Coil(design_flow_gpm=50.0, design_dT_C=5.0, load_fraction=1.0)
    assert math.isclose(c.achieved_dT(50.0), 5.0, rel_tol=1e-9)


def test_dT_collapses_upward_when_underflowing():
    """Half the flow → double the ΔT under unified formula."""
    c = Coil(design_flow_gpm=50.0, design_dT_C=5.0, load_fraction=1.0)
    assert math.isclose(c.achieved_dT(25.0), 10.0, rel_tol=1e-9)


def test_dT_degrades_when_overflowing():
    """Double the flow → half the ΔT."""
    c = Coil(design_flow_gpm=50.0, design_dT_C=5.0, load_fraction=1.0)
    assert math.isclose(c.achieved_dT(100.0), 2.5, rel_tol=1e-9)


def test_dT_zero_at_zero_flow():
    c = Coil(design_flow_gpm=50.0)
    assert c.achieved_dT(0.0) == 0.0


def test_load_fraction_scales_capacity_demand():
    c1 = Coil(design_flow_gpm=50.0, load_fraction=1.0)
    c2 = Coil(design_flow_gpm=50.0, load_fraction=0.5)
    assert math.isclose(c2.capacity_demand_kw, 0.5 * c1.capacity_demand_kw, rel_tol=1e-9)


def test_delivered_capacity_equals_demand_under_unified_formula():
    """The unified ΔT formula means delivered always equals demand (for flow > 0)."""
    c = Coil(design_flow_gpm=50.0, load_fraction=0.7)
    assert math.isclose(c.delivered_capacity_kw(30.0), c.capacity_demand_kw, rel_tol=1e-9)
