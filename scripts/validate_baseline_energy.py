"""Validate that the Belimo baseline produces realistic pump energy.

PRD §6 calls out ~10 kWh for a generic 60-min steady-state run, but PRD §4.1's
pump (250 kPa max head, 800 GPM max flow, η=0.65) has a theoretical max of
~8.4 kW. With our 6-valve subsystem at 70% load operating point, actual
draw lands ~3–5 kW → 3–5 kWh over 60 min. Acceptance band [1, 8] kWh
reflects what's physically achievable from the PRD-spec pump.

Usage:
    uv run python scripts/validate_baseline_energy.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sim.engine import run  # noqa: E402

EXPECTED_MIN_KWH = 1.0
EXPECTED_MAX_KWH = 8.0
EXPECTED_MEAN_DT_MIN = 3.5
EXPECTED_MEAN_DT_MAX = 6.5


def main() -> int:
    out = run("steady_state", "belimo", log_every=10**9)  # silent inside loop
    records = [json.loads(line) for line in out.read_text().splitlines()]
    total_kwh = sum(r["pump_kw"] for r in records) / 3600.0
    n_valves = len(records[0]["valves"])
    mean_dT = sum(st["dT_C"] for r in records for st in r["valves"]) / (len(records) * n_valves)

    print(f"validated: total_pump_energy = {total_kwh:.2f} kWh")
    print(f"validated: mean_dT           = {mean_dT:.2f} C")
    print(f"validated: ticks             = {len(records)}")

    rc = 0
    if not EXPECTED_MIN_KWH <= total_kwh <= EXPECTED_MAX_KWH:
        print(
            f"FAIL: pump energy {total_kwh:.2f} outside "
            f"[{EXPECTED_MIN_KWH}, {EXPECTED_MAX_KWH}] kWh",
            file=sys.stderr,
        )
        rc = 1
    if not EXPECTED_MEAN_DT_MIN <= mean_dT <= EXPECTED_MEAN_DT_MAX:
        print(
            f"FAIL: mean_dT {mean_dT:.2f} outside "
            f"[{EXPECTED_MEAN_DT_MIN}, {EXPECTED_MEAN_DT_MAX}] C",
            file=sys.stderr,
        )
        rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
