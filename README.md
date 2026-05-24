# SCA-ChillValve

Distributed cooperative-control prototype for HVAC valves in tropical data centers.
See `docs/ChillValve_Implementation_PRD_v1.md` for the full spec.

## Quickstart

```bash
uv sync
uv run pytest
uv run python scripts/plot_cv_curves.py   # writes docs/cv_curves.png
```

## Run a scenario

```bash
uv run python -m sim.engine --scenario steady_state --mode belimo
uv run python scripts/validate_baseline_energy.py
```

Output JSON timeseries lands in `data/runs/{scenario}_{mode}_{timestamp}.jsonl`.

## Status

Phase 2 (Simulation Core) — complete. 6-valve / 2-branch hydraulic system, Belimo
baseline controller, scenario engine, JSONL output. Energy ~3-5 kWh / 60 min,
mean ΔT ~5°C tracked by Belimo.

Next: Phase 3 (three-layer intelligence: rules + ML anomaly + multi-agent coordination).

## Repository layout

See PRD §3 for the canonical tree.

## Troubleshooting

- **`scikit-learn` install fails on macOS** — install Xcode CLI tools: `xcode-select --install`, then `uv sync` again.
