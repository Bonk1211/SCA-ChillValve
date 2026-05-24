"""Train Isolation Forest on preprocessed LBNL data.

Inputs:  data/lbnl_processed/train.pkl
Outputs: data/models/isolation_forest.pkl
         data/models/feature_scaler.pkl
         data/models/training_metadata.json (partial; validate.py fills in metrics)

Usage:
    uv run python -m ml.train
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import joblib
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from ml.preprocess import FEATURE_COLS

ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = ROOT / "data" / "lbnl_processed"
MODELS_DIR = ROOT / "data" / "models"


def main() -> int:
    train_path = PROCESSED_DIR / "train.pkl"
    if not train_path.exists():
        print(f"FAIL: {train_path} not found. Run `uv run python -m ml.preprocess` first.", file=sys.stderr)
        return 1
    train_df = joblib.load(train_path)
    X = train_df[FEATURE_COLS].values
    print(f"training on {len(X):,} samples × {len(FEATURE_COLS)} features")

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = IsolationForest(
        n_estimators=200,
        contamination=0.05,
        max_samples=256,
        max_features=1.0,
        bootstrap=False,
        random_state=42,
        n_jobs=-1,
    )
    print("fitting Isolation Forest...")
    model.fit(X_scaled)
    print("fit complete")

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODELS_DIR / "isolation_forest.pkl")
    joblib.dump(scaler, MODELS_DIR / "feature_scaler.pkl")

    metadata = {
        "training_date": datetime.utcnow().isoformat(),
        "model_type": "IsolationForest",
        "training_samples": int(len(X)),
        "feature_names": FEATURE_COLS,
        "feature_count": len(FEATURE_COLS),
        "hyperparameters": {
            "n_estimators": 200,
            "contamination": 0.05,
            "max_samples": 256,
            "random_state": 42,
        },
        "data_source": "LBNL Fault Detection and Diagnostics - Single-Duct AHU subset",
        "data_url": "https://faultdetection.lbl.gov/",
        "feature_mapping": {
            "CHWC_VLV": "position_pct / 100",
            "dT_coil": "dT_C (with implicit unit conversion via scaler)",
            "SA_CFM": "flow_gpm (different media, same flow-magnitude role)",
            "hour_sin": "sin(2π · hour_of_day / 24); synthesize from sim tick",
            "hour_cos": "cos(2π · hour_of_day / 24); synthesize from sim tick",
        },
        "notes": "Cross-domain training: LBNL is air-side AHU data; sim is water-side. Scaler bridges magnitudes but not physics. Validation AUC reflects defensible-but-not-strong unsupervised detection.",
    }
    with open(MODELS_DIR / "training_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"saved: {MODELS_DIR}/isolation_forest.pkl")
    print(f"saved: {MODELS_DIR}/feature_scaler.pkl")
    print(f"saved: {MODELS_DIR}/training_metadata.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
