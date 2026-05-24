"""Layer 2 — ML anomaly detection. PRD §5.2.

Loads the Isolation Forest trained by `ml.train` on the LBNL SDAHU dataset
and scores incoming `ValveState` snapshots. The 5-feature inference vector
mirrors what `ml.preprocess.FEATURE_COLS` was trained on:

    [CHWC_VLV, dT_coil, SA_CFM, hour_sin, hour_cos]
     ^position_pct/100, dT_C, flow_gpm, sin(2π·h/24), cos(2π·h/24)

`hour` is derived from a tick counter (one tick = one simulated second).
For a 60-min scenario, the hour features are effectively constant — that's
fine; they're included only because the model was trained with them.

If the model artifacts are missing, the layer falls back to the benign
placeholder so the rest of the pipeline still works (useful for tests).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import numpy as np

from sim.types import AnomalyResult, ValveState

# Default artifact locations (writable by `ml.train`).
DEFAULT_ROOT = Path(__file__).resolve().parent.parent.parent / "data" / "models"
DEFAULT_MODEL_PATH = DEFAULT_ROOT / "isolation_forest.pkl"
DEFAULT_SCALER_PATH = DEFAULT_ROOT / "feature_scaler.pkl"
DEFAULT_METADATA_PATH = DEFAULT_ROOT / "training_metadata.json"

# Match ml.preprocess.FEATURE_COLS exactly. Order matters.
FEATURE_NAMES: List[str] = ["CHWC_VLV", "dT_coil", "SA_CFM", "hour_sin", "hour_cos"]

# Confidence mapping: linear ramp around the tuned threshold.
# anomaly_score (=-decision_function) above threshold → 1.0; far below → 0.0.
CONFIDENCE_WINDOW = 0.20


@dataclass
class Layer2ML:
    """Anomaly detector. Loads trained artifacts on construction (or falls back to placeholder)."""

    model_path: Path = DEFAULT_MODEL_PATH
    scaler_path: Path = DEFAULT_SCALER_PATH
    metadata_path: Path = DEFAULT_METADATA_PATH
    _model: Optional[object] = field(default=None, repr=False)
    _scaler: Optional[object] = field(default=None, repr=False)
    _threshold: float = 0.0
    _loaded: bool = False

    def __post_init__(self) -> None:
        if self.model_path.exists() and self.scaler_path.exists():
            import joblib
            self._model = joblib.load(self.model_path)
            self._scaler = joblib.load(self.scaler_path)
            if self.metadata_path.exists():
                import json
                meta = json.loads(self.metadata_path.read_text())
                self._threshold = float(meta.get("metrics", {}).get("deployment_threshold")
                                            or meta.get("metrics", {}).get("tuned_threshold", 0.0))
            self._loaded = True

    def evaluate(self, state: ValveState, tick_seconds: int = 0) -> AnomalyResult:
        if not self._loaded:
            return AnomalyResult(
                anomaly_detected=False,
                confidence=0.0,
                raw_score=0.0,
                features=[],
                timestamp=state.timestamp or datetime.utcnow(),
            )

        features = _build_feature_vector(state, tick_seconds)
        x = self._scaler.transform([features])
        # decision_function: higher = more normal; lower = more anomalous.
        raw = float(self._model.decision_function(x)[0])
        anomaly_score = -raw  # higher = more anomalous
        anomaly_detected = anomaly_score >= self._threshold
        # Map to [0, 1] confidence with linear ramp around the threshold.
        confidence = max(
            0.0,
            min(1.0, (anomaly_score - self._threshold) / CONFIDENCE_WINDOW + 0.5),
        )
        return AnomalyResult(
            anomaly_detected=anomaly_detected,
            confidence=confidence,
            raw_score=anomaly_score,
            features=features,
            timestamp=state.timestamp or datetime.utcnow(),
        )


def _build_feature_vector(state: ValveState, tick_seconds: int) -> List[float]:
    """Build the 5-element feature vector matching ml.preprocess.FEATURE_COLS order."""
    hour_of_day = (tick_seconds / 3600.0) % 24.0
    hour_sin = float(np.sin(2 * np.pi * hour_of_day / 24.0))
    hour_cos = float(np.cos(2 * np.pi * hour_of_day / 24.0))
    return [
        state.position_pct / 100.0,   # CHWC_VLV
        state.dT_C,                   # dT_coil (C vs F is normalized away by scaler)
        state.flow_gpm,               # SA_CFM (different media, same flow-magnitude role)
        hour_sin,
        hour_cos,
    ]
