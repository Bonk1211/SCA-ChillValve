"""Unit conversions used across the simulation."""
from __future__ import annotations

KPA_PER_PSI = 6.894757
PSI_PER_KPA = 1.0 / KPA_PER_PSI  # ≈ 0.145038
WATER_DENSITY_KG_PER_M3 = 1000.0
# 1 US gallon = 3.785411784 L, divided by 60 s. PRD §4.2 uses an L/min shortcut
# (flow * density / 60) which is ~5% off; this constant is the exact GPM → m³/s.
GPM_TO_M3_PER_S = 6.30902e-5
CP_WATER_KJ_PER_KG_K = 4.186


def kpa_to_psi(kpa: float) -> float:
    return kpa * PSI_PER_KPA


def psi_to_kpa(psi: float) -> float:
    return psi * KPA_PER_PSI


def gpm_to_kg_per_s(gpm: float, density_kg_m3: float = WATER_DENSITY_KG_PER_M3) -> float:
    return gpm * GPM_TO_M3_PER_S * density_kg_m3
