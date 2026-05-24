"""Calibrate Layer 2 anomaly threshold to the sim's own normal distribution.

The Isolation Forest is trained on LBNL air-side AHU data; the simulation
produces water-side valve data. Cross-domain drift means even normal sim
states score above the LBNL-tuned threshold. This script runs the engine
for N ticks in Belimo mode (no faults), collects anomaly scores, and writes
a sim-calibrated threshold back into `data/models/training_metadata.json`
as `deployment_threshold`.

This mirrors PRD §13 Q7: "Phase 2: after 30 days of operation, Layer 2
anomaly models train on the building's normal patterns."

Usage:
    uv run python scripts/calibrate_layer2.py [--ticks 600] [--percentile 99]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402

from sim.coil import Coil  # noqa: E402
from sim.controllers.belimo_baseline import BelimoController  # noqa: E402
from sim.layers.layer2_ml import Layer2ML  # noqa: E402
from sim.scenarios import Scenario  # noqa: E402
from sim.system import HydraulicSystem  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
METADATA_PATH = ROOT / "data" / "models" / "training_metadata.json"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--ticks", type=int, default=600, help="warmup duration in sim seconds")
    p.add_argument("--percentile", type=float, default=99.0)
    args = p.parse_args()

    if not METADATA_PATH.exists():
        print(f"FAIL: {METADATA_PATH} not found. Train the model first.", file=sys.stderr)
        return 1

    layer2 = Layer2ML()
    if not layer2._loaded:
        print("FAIL: model not loaded", file=sys.stderr)
        return 1

    scenario = Scenario.load(ROOT / "data" / "scenarios" / "steady_state.json")
    system = HydraulicSystem.build_default()
    controller = BelimoController()

    scores: list[float] = []
    states = system.tick(0)
    for t in range(args.ticks):
        for rec in system.valves.values():
            rec.coil = Coil(
                design_flow_gpm=rec.coil.design_flow_gpm,
                design_dT_C=rec.coil.design_dT_C,
                load_fraction=scenario.load_fraction(rec.valve_id, t),
            )
        commands = controller.step(states)
        system.set_positions(commands)
        states = system.tick(t)
        for s in states:
            r = layer2.evaluate(s, tick_seconds=t)
            scores.append(r.raw_score)

    threshold = float(np.percentile(scores, args.percentile))
    print(f"collected {len(scores)} anomaly scores from {args.ticks} ticks × 6 valves")
    print(f"  min={min(scores):.4f}  p50={float(np.percentile(scores, 50)):.4f}  "
          f"p95={float(np.percentile(scores, 95)):.4f}  "
          f"p{int(args.percentile)}={threshold:.4f}  max={max(scores):.4f}")
    print(f"setting deployment_threshold = {threshold:.4f}")

    meta = json.loads(METADATA_PATH.read_text())
    meta.setdefault("metrics", {})["deployment_threshold"] = threshold
    meta["metrics"]["deployment_threshold_basis"] = (
        f"{args.percentile}th percentile of {len(scores)} sim anomaly scores collected "
        f"during {args.ticks} ticks of Belimo steady-state operation; calibrates the "
        f"LBNL-trained model to sim-domain normality"
    )
    METADATA_PATH.write_text(json.dumps(meta, indent=2))
    print(f"updated {METADATA_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
