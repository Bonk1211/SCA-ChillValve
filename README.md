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
# Belimo Energy Valve baseline
uv run python -m sim.engine --scenario steady_state --mode belimo

# ChillValve three-layer controller (Layer 1 rules + Layer 2 ML placeholder + Layer 3 multi-agent)
uv run python -m sim.engine --scenario steady_state --mode chillvalve

# Side-by-side comparison
uv run python -m sim.engine --scenario steady_state --mode compare
```

Per-tick JSONL timeseries lands in `data/runs/{scenario}_{mode}_{timestamp}.jsonl`,
including pump kW, per-valve flow/ΔT/position, Layer 1 rule fires, Layer 2 anomaly flags,
and Layer 3 leader assignments.

### Validation scripts

```bash
uv run python scripts/validate_baseline_energy.py        # asserts Belimo kWh + dT bands
uv run python scripts/validate_chillvalve_vs_belimo.py   # asserts both modes complete + report delta
```

## Status

Phase 3 (Three-Layer Intelligence) — complete.

- **Layer 1**: 5 deterministic rules per PRD §5.1 (position clamp, flow ceiling, dP failsafe, sensor validity, actuator timeout) + `validate_command` helper
- **Layer 2**: placeholder returning benign `AnomalyResult` (Phase 4 swaps in the trained Isolation Forest)
- **Layer 3**: in-process pub/sub broker + per-valve `ValveAgent` with two-phase tick (broadcast → process), bully leader election, leader-driven priority-based setpoint allocation
- **ChillValveController**: orchestrates all three layers per PRD §6 (Layer 1 override → Layer 2 enrich → Layer 3 setpoint → Layer 1 validate)
- **engine.py**: extended with `--mode chillvalve` and `--mode compare`; compare prints the delta line

Next: Phase 4 (ML training pipeline: download LBNL dataset, train Isolation Forest, swap into Layer 2).

## Repository layout

See PRD §3 for the canonical tree.

## Troubleshooting

- **`scikit-learn` install fails on macOS** — install Xcode CLI tools: `xcode-select --install`, then `uv sync` again.
