"""Plot Cv vs position curves for DN65 and DN100 valves.

Usage:
    uv run python scripts/plot_cv_curves.py

Output:
    docs/cv_curves.png
"""
from __future__ import annotations

import sys
from pathlib import Path

# Make the repo root importable when invoked as a script (not a module).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib  # noqa: E402

matplotlib.use("Agg")  # headless

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from sim.types import ValveSpec  # noqa: E402
from sim.valve import Valve  # noqa: E402

OUTPUT = Path(__file__).resolve().parents[1] / "docs" / "cv_curves.png"


def main() -> None:
    positions = np.linspace(0.0, 1.0, 101)
    fig, ax = plt.subplots(figsize=(8, 5))

    for spec in (ValveSpec.DN65, ValveSpec.DN100):
        v = Valve(spec=spec)
        cv_values = [v.cv(p) for p in positions]
        ax.plot(positions * 100, cv_values, label=f"{spec.label} (Cv_max={spec.cv_max})")

    ax.set_xlabel("Position (%)")
    ax.set_ylabel("Cv")
    ax.set_yscale("log")
    ax.set_title("Equal-percentage Cv curves (R=50)")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(OUTPUT, dpi=150)
    print(f"wrote {OUTPUT}")


if __name__ == "__main__":
    main()
