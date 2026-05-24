"""Single-valve hydraulic model. PRD §4.2.

Flow is computed from valve position and pressure drop using the standard
equal-percentage characteristic and ISA liquid flow equation.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from sim.types import RANGEABILITY, SG_WATER, ValveSpec
from sim.units import kpa_to_psi


@dataclass(frozen=True)
class Valve:
    """Equal-percentage characterized ball valve per PRD §4.2."""

    spec: ValveSpec
    rangeability: float = RANGEABILITY

    def cv(self, position: float) -> float:
        """Effective Cv at the given position.

        position is on the unit interval [0, 1] (NOT percent).
        Cv(position) = Cv_max * R^(position - 1)
          position=1.0 → Cv_max
          position=0.0 → Cv_max / R   (minimum Cv)
        """
        if not 0.0 <= position <= 1.0:
            raise ValueError(f"position must be in [0, 1], got {position!r}")
        return self.spec.cv_max * (self.rangeability ** (position - 1.0))

    def flow_gpm(self, position: float, dP_kPa: float) -> float:
        """Volumetric flow [GPM] given position and pressure drop across the valve."""
        if dP_kPa < 0.0:
            raise ValueError(f"dP_kPa must be >= 0, got {dP_kPa!r}")
        if dP_kPa == 0.0:
            return 0.0
        dP_psi = kpa_to_psi(dP_kPa)
        return self.cv(position) * math.sqrt(dP_psi / SG_WATER)
