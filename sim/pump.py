"""Pump model. PRD §4.3."""
from __future__ import annotations

from dataclasses import dataclass

from sim.units import kpa_to_psi


@dataclass(frozen=True)
class Pump:
    """Single variable-speed pump serving both branches.

    Head curve (quadratic system curve): ΔP_pump = static_head + k * Q^2.
    Power: imperial HP = (Q[GPM] * ΔP[psi]) / 3960, then × 0.7457 → kW,
    then / η = mechanical kW input.
    """

    max_head_kpa: float = 250.0     # PRD §4.1
    max_flow_gpm: float = 800.0     # PRD §4.1
    efficiency: float = 0.65        # PRD §4.1
    static_head_kpa: float = 200.0   # head at zero flow

    @property
    def k(self) -> float:
        return (self.max_head_kpa - self.static_head_kpa) / (self.max_flow_gpm ** 2)

    def head_kpa(self, flow_gpm: float) -> float:
        if flow_gpm < 0.0:
            raise ValueError(f"flow_gpm must be >= 0, got {flow_gpm!r}")
        return self.static_head_kpa + self.k * flow_gpm * flow_gpm

    def power_kw(self, flow_gpm: float, head_kpa: float) -> float:
        if flow_gpm < 0.0 or head_kpa < 0.0:
            raise ValueError("flow_gpm and head_kpa must be >= 0")
        head_psi = kpa_to_psi(head_kpa)
        hydraulic_hp = (flow_gpm * head_psi) / 3960.0
        return (hydraulic_hp * 0.7457) / self.efficiency
