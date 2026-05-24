# Implementation Report: Phase 4 — ML Training + Layer 2 Wiring

## Summary
Trained the Layer 2 Isolation Forest locally on the LBNL Single-Duct AHU dataset using a deliberately narrow 5-feature subset that maps cleanly to `ValveState`. Wired the trained model into `sim/layers/layer2_ml.py` with a placeholder fallback when artifacts are missing. Added a sim-domain calibration script so the LBNL-trained threshold is rescaled to the simulation's actual normal distribution at deployment time.

## Inputs delivered by user

- `SCA_Piping_ML_Corrected.ipynb` (reference Colab notebook, 24-feature pipeline)
- `LBNL_FDD_Data_Sets_SDAHU.zip` (607 MB, extracted to `data/lbnl_raw/`, 21 CSVs)

## What was built

| File | Action | Notes |
|---|---|---|
| `ml/preprocess.py` | CREATED | Load 21 CSVs, label rows, downsample every 30th row, engineer 5-feature subset, save train/test as joblib pkl. **Downsampling** was needed because the full 11M-row dataset overflows disk. |
| `ml/train.py` | CREATED | Fit StandardScaler + IsolationForest(n_estimators=200, contamination=0.05), save artifacts to `data/models/`. |
| `ml/validate.py` | CREATED | Compute AUC, tune threshold for FPR ≤ 10% (not F1 — that's degenerate on faulted-heavy test set), per-fault recall breakdown, 3 plots, **training-set p95/p99 thresholds** for cross-domain deployment. |
| `scripts/calibrate_layer2.py` | CREATED | Run engine 600 ticks in Belimo mode (no faults), collect anomaly scores, write 99th percentile back to metadata as `deployment_threshold`. Mirrors PRD §13 Q7 site-specific commissioning. |
| `sim/layers/layer2_ml.py` | REWROTE | Loads model + scaler + metadata on construction; falls back to benign placeholder when artifacts missing. `evaluate(state, tick_seconds=0)` builds 5-feature vector and scores. |
| `sim/controllers/chillvalve.py` | UPDATED | `layer2.evaluate(s, tick_seconds=int(t_seconds))` — passes simulated time so hour_sin/hour_cos feature values are accurate. |
| `tests/test_layer2_ml.py` | REWROTE | Tests both placeholder mode (forced via nonexistent paths) and real-model mode (when artifacts present). 4 cases. |
| `tests/test_chillvalve_controller.py` | UPDATED | `test_layer_2_anomaly_flag_propagated_to_state` now injects a forced-placeholder Layer 2 to keep the assertion deterministic regardless of model presence. |

## Feature subset

Only these LBNL columns have a meaningful sim equivalent:

| LBNL | ValveState | Note |
|---|---|---|
| `CHWC_VLV` (0–1) | `position_pct / 100` | Direct semantic match |
| `dT_coil` (= MA − SA, °F, air-side) | `dT_C` (water-side, °C) | Different physics; same "coil cooling magnitude" role; scaler normalizes |
| `SA_CFM` (air flow) | `flow_gpm` (water flow) | Different media; same flow-magnitude role |
| `hour_sin` / `hour_cos` | synthesized from sim tick | `(tick / 3600) % 24` |

Building-level signals from the notebook (zone temps, dampers, fan speeds, OA temp) are excluded — the sim has no equivalents and synthesizing them would pollute the anomaly score.

## Training results

```
Training samples:  14,014  (fault-free, 80% of downsampled LBNL baseline)
Test samples:      14,014  (3,504 normal + 10,510 faulted, stratified by fault type)
Features:          5  (CHWC_VLV, dT_coil, SA_CFM, hour_sin, hour_cos)

AUC: 0.6537
```

Per-fault recall at FPR ≤ 10%:
```
coil_valve_stuck      85.5%   ← severe operational fault, caught reliably
coil_sensor_bias      40.8%
coil_leakage          28.8%
damper_stuck          19.6%
oa_sensor_bias         5.5%   ← subtle, requires temporal modeling
```

**AUC 0.65 is below PRD §9.4's "defensible 0.75" target** because we use only 5 features (notebook uses 24) and the sim is water-side while LBNL is air-side. The 5-feature subset is the price of building a model that can actually run against `ValveState` at inference time.

## Cross-domain calibration

LBNL distribution: `SA_CFM` mean ≈ 372k, sim `flow_gpm` ≈ 22. After standardization, almost all sim states score above the LBNL-tuned threshold → "everything anomalous" if we use the test-set-tuned threshold.

Fix: `scripts/calibrate_layer2.py` runs the sim 600 ticks in Belimo mode (no faults), collects 3,600 anomaly scores, sets `deployment_threshold = 99th percentile`. Result: real-time `chillvalve` mode now flags ~0.6% of valve-ticks (close to the 1% calibration target).

This matches PRD §13 Q7: *"Phase 2: after 30 days of operation, Layer 2 anomaly models train on the building's normal patterns."*

## Live validation

```
chillvalve mode (3600 ticks, post-calibration):
  pump_kwh:        3.77    (matches Phase 3 baseline)
  mean_dT:         5.00    (matches Phase 3 baseline)
  anomaly flags:   126 / 21600 valve-ticks (0.58%)
  layer1 fires:    0
  leader changes:  0
```

No regressions in pump energy or mean ΔT — Layer 2 enrichment is purely additive.

## Validation artifacts in `docs/ml_validation/`
- `roc_curve.png`
- `score_distribution.png`
- `per_fault_detection.png`

## How to reproduce

```bash
# Extract LBNL_FDD_Data_Sets_SDAHU.zip into data/lbnl_raw/ (one-time, 2.7 GB)
uv run python -m ml.preprocess
uv run python -m ml.train
uv run python -m ml.validate
uv run python scripts/calibrate_layer2.py --ticks 600 --percentile 99
```

Trained artifacts (`isolation_forest.pkl`, `feature_scaler.pkl`, `training_metadata.json`) land in `data/models/` (gitignored). Plots land in `docs/ml_validation/`.

## Deviations from earlier guidance

1. **Phase 4 went local, not Colab.** Earlier session memory said the user would train on Colab and deliver `.pkl` files; the user reversed course mid-session and delivered the notebook + raw zip instead. Memory note updated to reflect this.
2. **Downsampled the dataset.** The full 11M-row corpus runs out of disk for intermediate parquet/pkl files. Every 30th row (~360k total) gives the IF plenty of variance and runs in seconds.
3. **F1-max threshold replaced with FPR-bounded.** F1-max picks "flag everything" on a faulted-heavy test set. Bounded FPR ≤ 10% gives a deployable threshold (precision 0.92, recall 0.36, F1 0.52).
4. **Two thresholds in metadata.** `tuned_threshold` (LBNL test set) + `deployment_threshold` (sim-domain p99 from calibration). Layer 2 uses `deployment_threshold`, falling back to `tuned_threshold` if calibration hasn't run.
5. **Layer 2 falls back to placeholder when artifacts missing.** Lets tests run on a fresh clone without `ml/train` having been executed yet. The tests force this by passing nonexistent paths.

## Q&A defense (for PRD §13 / report)

> **Why is AUC only 0.65 instead of 0.85?**
> We deliberately trained on only 5 sim-mappable features, not the notebook's 24. The notebook includes zone temps, damper positions, fan speeds, and outdoor air temperature — building-level AHU signals that don't exist in our per-valve simulation. With only the features the sim can actually deliver at inference time, AUC is bounded around 0.65. The alternative — training on 24 features and synthesizing missing ones from defaults — would inflate AUC on paper while degrading the actual anomaly signal in deployment. We chose the honest path.

> **What about the cross-domain (air → water) mismatch?**
> LBNL is air-side AHU data; our sim is water-side chilled-water valves. The Isolation Forest learns normal patterns in the LBNL distribution; sim values are systematically out-of-distribution. We compensate at deployment via a calibration step that re-tunes the threshold to the sim's own normal range — mirroring real building commissioning where the model is calibrated on the first 30 days of site-specific data (PRD §13 Q7).

> **Which faults does the model actually catch?**
> At a 10% false-positive budget: 85% of stuck cooling-coil valves, 41% of cooling-coil sensor biases, 29% of coil leakage. The severe operational faults — stuck valves, the headline failure mode for a smart valve product — are caught reliably. Subtler faults (sensor drift) require temporal modeling beyond the row-level features we use.

## Next steps

- [ ] Optional: extend `ValveState` with synthetic AHU context (zone temps, OA temp) and retrain on the notebook's full 24-feature set if higher AUC is needed for the demo. ~5–10 file edits across `sim/`.
- [ ] Phase 7: integration polish, fault injection scenario C, demo recording.
