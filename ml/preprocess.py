"""Preprocess LBNL Single-Duct AHU dataset.

Loads all 21 CSVs, labels rows (1 fault-free + 20 faulted), engineers a
sim-mappable feature subset, downsamples for tractability, saves train/test
as joblib pickles.

Feature subset is deliberately narrow to match `sim.types.ValveState`:

    LBNL column   <-> ValveState field
    -----------       -----------------------------
    CHWC_VLV      <-> position_pct / 100
    dT_coil       <-> dT_C  (different units; scaler normalizes)
    SA_CFM        <-> flow_gpm (different media; same "flow magnitude" role)
    hour_sin/cos  <-> synthesized from sim tick

Building-level signals (zone temps, dampers, fan speeds, OA temp) are
intentionally excluded — the sim has no equivalents and synthesizing them
would pollute the anomaly score.

Usage:
    uv run python -m ml.preprocess
"""
from __future__ import annotations

import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "lbnl_raw" / "LBNL_FDD_Dataset_SDAHU"
PROCESSED_DIR = ROOT / "data" / "lbnl_processed"

USECOLS = ["Datetime", "CHWC_VLV", "SA_TEMP", "MA_TEMP", "SA_CFM"]
FEATURE_COLS = ["CHWC_VLV", "dT_coil", "SA_CFM", "hour_sin", "hour_cos"]

# Downsample: keep every Nth row. 525k rows × 21 files = 11M rows; way more
# than Isolation Forest needs and runs out of disk for intermediate files.
# Sampling every 30 minutes (rows are 1-minute) gives ~17k rows per file → 350k total.
ROW_STRIDE = 30

FAULT_TYPE_PREFIXES = {
    "coi_bias": "coil_sensor_bias",
    "coi_leakage": "coil_leakage",
    "coi_stuck": "coil_valve_stuck",
    "damper_stuck": "damper_stuck",
    "oa_bias": "oa_sensor_bias",
}


def categorize(filename: str) -> tuple[int, str, float]:
    if filename == "AHU_annual.csv":
        return 0, "fault_free", 0.0
    cleaned = filename.replace("_annual_short.csv", "").replace("_annual.csv", "")
    parts = cleaned.split("_")
    for prefix, name in FAULT_TYPE_PREFIXES.items():
        if filename.startswith(prefix):
            sev_str = parts[-1]
            try:
                sev = (
                    float(sev_str) / 100.0
                    if sev_str.lstrip("-").isdigit() and len(sev_str) > 1
                    else float(sev_str)
                )
            except ValueError:
                sev = 0.0
            return 1, name, sev
    raise ValueError(f"unrecognized filename: {filename}")


def load_all(stride: int = ROW_STRIDE) -> pd.DataFrame:
    files = sorted(RAW_DIR.glob("*.csv"))
    if len(files) != 21:
        raise RuntimeError(f"expected 21 CSVs in {RAW_DIR}, found {len(files)}")
    frames = []
    for f in files:
        is_faulted, fault_type, severity = categorize(f.name)
        df = pd.read_csv(f, usecols=lambda c: c in USECOLS)
        if stride > 1:
            df = df.iloc[::stride].reset_index(drop=True)
        df["is_faulted"] = is_faulted
        df["fault_type"] = fault_type
        df["fault_severity"] = severity
        df["source_file"] = f.name
        frames.append(df)
        print(f"  loaded {f.name:<40} {len(df):>7,} rows ({fault_type}, sev={severity})")
    return pd.concat(frames, ignore_index=True)


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.dropna(subset=["CHWC_VLV", "SA_TEMP", "MA_TEMP", "SA_CFM"]).copy()
    df["datetime"] = pd.to_datetime(df["Datetime"])
    df["dT_coil"] = df["MA_TEMP"] - df["SA_TEMP"]
    df["hour"] = df["datetime"].dt.hour
    df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24)
    df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24)
    return df.dropna(subset=FEATURE_COLS).reset_index(drop=True)


def split(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    fault_free = df[df["is_faulted"] == 0].sort_values("datetime").reset_index(drop=True)
    faulted = df[df["is_faulted"] == 1]
    n_train = int(len(fault_free) * 0.8)
    train_df = fault_free.iloc[:n_train].copy()
    test_normal = fault_free.iloc[n_train:].copy()

    target_faulted = len(test_normal) * 3
    fault_types = faulted["fault_type"].unique()
    per_type_cap = max(1, target_faulted // max(1, len(fault_types)))

    parts = []
    for ft in fault_types:
        subset = faulted[faulted["fault_type"] == ft]
        n = min(len(subset), per_type_cap)
        parts.append(subset.sample(n=n, random_state=42))
    test_faulted = pd.concat(parts, ignore_index=True)
    test_df = (
        pd.concat([test_normal, test_faulted])
        .sample(frac=1, random_state=42)
        .reset_index(drop=True)
    )
    assert train_df["is_faulted"].sum() == 0, "training set contaminated"
    return train_df, test_df


def main() -> int:
    if not RAW_DIR.exists():
        print(f"FAIL: {RAW_DIR} not found", file=sys.stderr)
        return 1
    print(f"loading 21 CSVs (every {ROW_STRIDE}th row)...")
    df = load_all()
    print(f"total rows loaded: {len(df):,}")
    print("engineering features...")
    df = engineer_features(df)
    print(f"after engineering: {len(df):,}")
    print("splitting train/test...")
    train_df, test_df = split(df)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(train_df, PROCESSED_DIR / "train.pkl", compress=3)
    joblib.dump(test_df, PROCESSED_DIR / "test.pkl", compress=3)
    print(f"train: {len(train_df):,} rows  -> {PROCESSED_DIR / 'train.pkl'}")
    print(f"test:  {len(test_df):,} rows  -> {PROCESSED_DIR / 'test.pkl'}")
    print(f"  normal: {(test_df['is_faulted']==0).sum():,}, faulted: {(test_df['is_faulted']==1).sum():,}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
