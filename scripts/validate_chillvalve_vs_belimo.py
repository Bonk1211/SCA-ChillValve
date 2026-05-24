"""Validate ChillValve + Belimo both run end-to-end and report the delta.

Does NOT require ChillValve to save energy in Phase 3 — Layer 2 is a
placeholder, no fault scenarios are loaded, and the unified ΔT formula
keeps capacity_delivered == capacity_demand, leaving no deficit for the
leader to coordinate around. Phase 4 (real ML + fault scenarios) is when
meaningful savings can be measured.

Usage:
    uv run python scripts/validate_chillvalve_vs_belimo.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sim.engine import _run_single  # noqa: E402


def main() -> int:
    _, belimo = _run_single("steady_state", "belimo", log_every=10**9)
    _, cv = _run_single("steady_state", "chillvalve", log_every=10**9)
    delta = cv["pump_kwh"] - belimo["pump_kwh"]
    pct = (delta / belimo["pump_kwh"]) * 100.0
    print(f"belimo:     pump_kwh={belimo['pump_kwh']:.3f}  mean_dT={belimo['mean_dT']:.2f}")
    print(f"chillvalve: pump_kwh={cv['pump_kwh']:.3f}  mean_dT={cv['mean_dT']:.2f}")
    print(f"delta:      {delta:+.3f} kWh ({pct:+.1f} %)")
    for name, s in (("belimo", belimo), ("chillvalve", cv)):
        if not 1.0 <= s["pump_kwh"] <= 10.0:
            print(f"FAIL: {name} pump_kwh {s['pump_kwh']:.2f} outside [1, 10]", file=sys.stderr)
            return 1
        if not 3.0 <= s["mean_dT"] <= 7.0:
            print(f"FAIL: {name} mean_dT {s['mean_dT']:.2f} outside [3, 7] C", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
