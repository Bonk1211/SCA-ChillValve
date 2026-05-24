"""Coil thermal model. PRD §4.2 lines 176–188.

Both regimes (underflow and overflow) reduce to a single formula:
    ΔT_achieved = capacity_demand / (m_dot_actual * Cp)
                = load_fraction * dT_design * (m_dot_design / m_dot_actual)

  m_dot = m_dot_design → ΔT = dT_design
  m_dot < m_dot_design → ΔT > dT_design (collapse — water spends longer in coil)
  m_dot > m_dot_design → ΔT < dT_design (degrade — water passes too fast)
"""
from __future__ import annotations

from dataclasses import dataclass

from sim.units import CP_WATER_KJ_PER_KG_K, gpm_to_kg_per_s


@dataclass(frozen=True)
class Coil:
    """Air-side load coupled to chilled-water flow via design ΔT."""

    design_flow_gpm: float
    design_dT_C: float = 5.0     # PRD §4.1
    load_fraction: float = 1.0   # scenario-driven; 1.0 = full design load

    @property
    def capacity_demand_kw(self) -> float:
        m_dot_design = gpm_to_kg_per_s(self.design_flow_gpm)
        return self.load_fraction * m_dot_design * CP_WATER_KJ_PER_KG_K * self.design_dT_C

    def achieved_dT(self, flow_gpm: float) -> float:
        if flow_gpm <= 0.0:
            return 0.0
        m_dot = gpm_to_kg_per_s(flow_gpm)
        return self.capacity_demand_kw / (m_dot * CP_WATER_KJ_PER_KG_K)

    def delivered_capacity_kw(self, flow_gpm: float) -> float:
        if flow_gpm <= 0.0:
            return 0.0
        # Always equals capacity_demand_kw under the unified formula above,
        # but expressed explicitly via achieved_dT for clarity.
        return self.achieved_dT(flow_gpm) * gpm_to_kg_per_s(flow_gpm) * CP_WATER_KJ_PER_KG_K
