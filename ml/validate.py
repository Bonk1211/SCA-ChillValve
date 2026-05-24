"""Validate the trained Isolation Forest against held-out faulted/normal test set.

Computes AUC, tunes a threshold for F1, reports per-fault-type recall, and
writes ROC + score-distribution + per-fault plots into docs/ml_validation/.
Updates data/models/training_metadata.json with the metrics block.

Usage:
    uv run python -m ml.validate
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import joblib
import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from sklearn.metrics import (  # noqa: E402
    classification_report,
    confusion_matrix,
    precision_recall_curve,
    roc_auc_score,
    roc_curve,
)

from ml.preprocess import FEATURE_COLS  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = ROOT / "data" / "lbnl_processed"
MODELS_DIR = ROOT / "data" / "models"
PLOTS_DIR = ROOT / "docs" / "ml_validation"


def main() -> int:
    test_df = joblib.load(PROCESSED_DIR / "test.pkl")
    train_df = joblib.load(PROCESSED_DIR / "train.pkl")
    model = joblib.load(MODELS_DIR / "isolation_forest.pkl")
    scaler = joblib.load(MODELS_DIR / "feature_scaler.pkl")

    # Compute a training-set percentile threshold for cross-domain deployment.
    # Sim values shifted out of LBNL distribution → test-set tuned threshold
    # over-flags. Training-percentile is calibrated to the model's own normal.
    X_train_scaled = scaler.transform(train_df[FEATURE_COLS].values)
    train_anomaly_scores = -model.decision_function(X_train_scaled)
    train_p95 = float(np.percentile(train_anomaly_scores, 95))
    train_p99 = float(np.percentile(train_anomaly_scores, 99))
    print(f"training-set anomaly score percentiles: 95th={train_p95:.4f}  99th={train_p99:.4f}")

    X = scaler.transform(test_df[FEATURE_COLS].values)
    y = test_df["is_faulted"].values

    raw = model.decision_function(X)
    anomaly_scores = -raw  # higher = more anomalous
    y_pred_default = (model.predict(X) == -1).astype(int)
    auc = roc_auc_score(y, anomaly_scores)

    print(f"AUC: {auc:.4f}")
    print()
    print("default-threshold classification:")
    print(classification_report(y, y_pred_default, target_names=["Normal", "Anomaly"], digits=4))

    # Tune threshold: maximize recall subject to FPR <= 0.10.
    # (F1-max is degenerate when the test set is faulted-heavy — flagging
    #  everything wins F1 trivially. Bounding FPR gives a deployable threshold.)
    fpr_curve, tpr_curve, thresh_curve = roc_curve(y, anomaly_scores)
    max_fpr = 0.10
    valid = np.where(fpr_curve <= max_fpr)[0]
    if len(valid) == 0:
        best_roc_idx = 0
    else:
        best_roc_idx = int(valid[np.argmax(tpr_curve[valid])])
    tuned_threshold = float(thresh_curve[best_roc_idx])
    # Also compute the standard precision/recall at this threshold for the report.
    precisions, recalls, thresholds = precision_recall_curve(y, anomaly_scores)
    # Find precision/recall pair closest to our threshold
    closest = int(np.argmin(np.abs(thresholds - tuned_threshold)))
    best = closest
    f1 = 2 * precisions[:-1] * recalls[:-1] / (precisions[:-1] + recalls[:-1] + 1e-9)
    print(f"tuned threshold (FPR<={max_fpr}): {tuned_threshold:.4f}  precision={precisions[best]:.3f}  recall={recalls[best]:.3f}  f1={f1[best]:.3f}")

    y_pred_tuned = (anomaly_scores >= tuned_threshold).astype(int)
    cm = confusion_matrix(y, y_pred_tuned)
    print(f"tuned confusion matrix (rows=actual, cols=predicted):\n{cm}")

    # Per-fault recall.
    faulted = test_df.assign(score=anomaly_scores, pred=y_pred_tuned)
    faulted = faulted[faulted["is_faulted"] == 1]
    per_fault = {
        ft: float(grp["pred"].mean())
        for ft, grp in faulted.groupby("fault_type")
    }
    print("per-fault recall (tuned):")
    for ft, rec in sorted(per_fault.items()):
        print(f"  {ft:<25} {rec:.1%}")

    # False positive rate at tuned threshold.
    normal = test_df.assign(pred=y_pred_tuned)
    normal = normal[normal["is_faulted"] == 0]
    fp_rate = float(normal["pred"].mean())
    print(f"false positive rate (tuned): {fp_rate:.1%}")

    # Plots.
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)

    fpr, tpr, _ = roc_curve(y, anomaly_scores)
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.plot(fpr, tpr, color="#0ea5e9", linewidth=2.5, label=f"Isolation Forest (AUC={auc:.3f})")
    ax.plot([0, 1], [0, 1], color="gray", linestyle="--", linewidth=1)
    ax.set_xlabel("False positive rate")
    ax.set_ylabel("True positive rate")
    ax.set_title("ChillValve Layer 2 — Anomaly Detection ROC")
    ax.legend(loc="lower right")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "roc_curve.png", dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.hist(anomaly_scores[y == 0], bins=50, alpha=0.6, color="#10b981", label="Normal", density=True)
    ax.hist(anomaly_scores[y == 1], bins=50, alpha=0.6, color="#f43f5e", label="Faulted", density=True)
    ax.axvline(tuned_threshold, color="black", linestyle="--", linewidth=1.5, label=f"Tuned threshold ({tuned_threshold:.3f})")
    ax.set_xlabel("Anomaly score (higher = more anomalous)")
    ax.set_ylabel("Density")
    ax.set_title("Score distribution — normal vs faulted")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "score_distribution.png", dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 5))
    sorted_pf = sorted(per_fault.items(), key=lambda x: x[1])
    names = [n for n, _ in sorted_pf]
    vals = [v for _, v in sorted_pf]
    colors = ["#ef4444" if v < 0.3 else "#f59e0b" if v < 0.6 else "#10b981" for v in vals]
    bars = ax.barh(names, vals, color=colors, edgecolor="black", linewidth=0.5)
    for bar, v in zip(bars, vals, strict=False):
        ax.text(bar.get_width() + 0.01, bar.get_y() + bar.get_height() / 2, f"{v:.1%}", ha="left", va="center")
    ax.set_xlabel("Detection rate (recall) at tuned threshold")
    ax.set_title(f"Detection rate by fault type — overall AUC {auc:.3f}")
    ax.set_xlim(0, 1.15)
    ax.axvline(0.5, color="gray", linestyle=":", alpha=0.5)
    ax.grid(axis="x", alpha=0.3)
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "per_fault_detection.png", dpi=150)
    plt.close(fig)

    # Update metadata with metrics.
    metadata_path = MODELS_DIR / "training_metadata.json"
    metadata = json.loads(metadata_path.read_text())
    metadata["test_samples"] = int(len(test_df))
    metadata["metrics"] = {
        "auc": float(auc),
        "tuned_threshold": tuned_threshold,
        "tuned_precision": float(precisions[best]),
        "tuned_recall": float(recalls[best]),
        "tuned_f1": float(f1[best]),
        "false_positive_rate_at_tuned": fp_rate,
        "training_p95_threshold": train_p95,
        "training_p99_threshold": train_p99,
        "deployment_threshold": train_p95,
        "deployment_threshold_basis": "95th percentile of training-set anomaly scores; calibrated for cross-domain inference where the LBNL-test-tuned threshold over-flags sim inputs",
    }
    metadata["per_fault_recall_at_tuned"] = per_fault
    metadata_path.write_text(json.dumps(metadata, indent=2))
    print(f"updated {metadata_path}")
    print(f"plots in {PLOTS_DIR}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
