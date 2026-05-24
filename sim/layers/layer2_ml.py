"""Layer 2 — ML anomaly detection. PRD §5.2.

Phase 3 placeholder: always benign. Phase 4 will load the trained Isolation
Forest from data/models/ and compute real scores. The placeholder's surface
matches what Phase 4 will need so call sites remain stable.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sim.types import AnomalyResult, ValveState


@dataclass
class Layer2ML:
    """Anomaly detector. Placeholder in Phase 3."""

    def evaluate(self, state: ValveState) -> AnomalyResult:
        return AnomalyResult(
            anomaly_detected=False,
            confidence=0.0,
            raw_score=0.0,
            features=[],
            timestamp=state.timestamp or datetime.utcnow(),
        )
