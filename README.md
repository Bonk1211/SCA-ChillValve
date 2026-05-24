# SCA-ChillValve

Distributed cooperative-control prototype for HVAC valves in tropical data centers.
See `docs/ChillValve_Implementation_PRD_v1.md` for the full spec.

## Quickstart

```bash
uv sync
uv run pytest
uv run python scripts/plot_cv_curves.py   # writes docs/cv_curves.png
```

## Status

Phase 1 (Foundation) — repo scaffolded, hydraulic model implemented and tested.
Next: Phase 2 (6-valve system + pump + Belimo baseline).

## Repository layout

See PRD §3 for the canonical tree.

## Troubleshooting

- **`scikit-learn` install fails on macOS** — install Xcode CLI tools: `xcode-select --install`, then `uv sync` again.
