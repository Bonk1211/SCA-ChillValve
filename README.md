# SCA-ChillValve

Distributed cooperative-control prototype for HVAC valves in tropical data centers.
See `docs/ChillValve_Implementation_PRD_v1.md` for the full spec.

## Quickstart (backend + sim)

```bash
uv sync
uv run pytest
uv run python scripts/plot_cv_curves.py   # writes docs/cv_curves.png
```

## Run a scenario from the CLI

```bash
# Scenarios: `steady_state` (60 min benign) or `fault_injection` (30 min, B2 fouling)
uv run python -m sim.engine --scenario steady_state --mode belimo
uv run python -m sim.engine --scenario fault_injection --mode chillvalve
uv run python -m sim.engine --mode belimo
uv run python -m sim.engine --mode chillvalve
uv run python -m sim.engine --mode compare
```

Per-tick JSONL timeseries lands in `data/runs/{scenario}_{mode}_{timestamp}.jsonl`.

## Run the backend (FastAPI + WebSocket)

```bash
uv run uvicorn backend.main:app --port 8000
```

REST: `GET /health`, `POST /scenario/{start,pause,resume,reset}`, `POST /mode/{mode}`, `GET /history?since=N`.
WebSocket: `/ws` streams state at 20 Hz wall-clock.
OpenAPI: `http://localhost:8000/docs`.

## Run the dashboard

```bash
cd frontend
npm install   # first time only
npm run dev   # http://localhost:5173
```

Backend must be running on `localhost:8000`. CORS is pre-configured for `localhost:5173`.

The dashboard shows 6 valve tiles (2 branches × 3 valves) with live flow / ΔT /
position, three-layer activity indicators (L1 rules / L2 ML / L3 coordination +
LEADER badge), a 60-tick mini chart per valve, and a scrolling event log of
rule fires and leader changes.

### Validation scripts

```bash
uv run python scripts/validate_baseline_energy.py        # Belimo kWh / dT bands
uv run python scripts/validate_chillvalve_vs_belimo.py   # compare modes complete
uv run python scripts/validate_backend_e2e.py            # backend + WS smoke

cd frontend && npm run test                              # vitest unit tests
cd frontend && npm run build                             # production build
```

## Status

Phase 7 (Integration & Polish) — complete.

- Vite + React 19 + Tailwind v3 + Zustand + Recharts + framer-motion
- `useWebSocket` hook auto-reconnects with exponential backoff
- `useDashboardStore` buffers 60 ticks per valve; detects rule-fire and
  leader-change events for the log
- ValveTile renders metrics + LEADER badge (framer-motion `layoutId` so the
  badge animates between branch siblings on election) + L1/L2/L3 indicators
- 12 frontend tests pass; production bundle is 627 KB / 195 KB gzipped

Next: Phase 4 (ML training, pending external Colab work by the user) and
Phase 7 (integration polish + demo recording).

## Repository layout

See PRD §3 for the canonical tree.


## Environment

```bash
cp .env.example .env
# Edit .env to set GEMINI_API_KEY, CHILLVALVE_TICK_PERIOD_S, etc.
```

`.env` is auto-loaded by `sim/_env.py` on import of `sim.engine`,
`backend.main`, or `backend.explainer`. `.env` is gitignored; never
committed. The `.env.example` template lists every variable the codebase
reads.

Supported variables:

| Variable | Default | Purpose |
|---|---|---|
| `GEMINI_API_KEY` or `GOOGLE_API_KEY` | (unset) | Enable LLM leader-event narration. Without it the explainer falls back to deterministic templates. |
| `CHILLVALVE_TICK_PERIOD_S` | `0.05` | Wall-clock seconds per simulated second. Lower = faster demo playback. |
| `CHILLVALVE_DB_PATH` | `data/chillvalve.db` | SQLite path. |

### Optional: LLM event narration + multi-agent debate

Two LLM features, both Gemini 2.5 Flash, both off without an API key:

1. **Event narration** — leader-election events get a one-sentence
   explanation in the dashboard event log.
2. **Multi-agent debate** (Layer 3 replacement) — when Layer 2's
   anomaly confidence sits in the uncertain band `[0.30, 0.85]` for a
   branch, the valves debate. Each peer speaks once in parallel, the
   elected leader synthesizes per-valve position allocations.
   Cooldown: 30 sim-seconds per branch. State-hash cached so similar
   conditions don't re-bill. Transcripts render in the dashboard's
   Debate Panel.

Layer 1 still validates the final command — the debate recommends, it
never bypasses safety.

```bash
echo "GEMINI_API_KEY=your_key" >> .env
uv run uvicorn backend.main:app --port 8000
```

Without a key, the explainer uses deterministic text and the debate
silently falls back to deterministic Layer 3 (priority-based allocation
by the elected leader).

The LLM is operator-facing only. It does **not** participate in the
control loop — Layer 1 rules, Layer 2 ML, and Layer 3 election all run
identically regardless of whether explanations are enabled.

## Troubleshooting

- **`scikit-learn` install fails on macOS** — install Xcode CLI tools:
  `xcode-select --install`, then `uv sync` again.
- **Dashboard shows "disconnected"** — check that the backend is running on
  `localhost:8000`. The dashboard auto-reconnects every 1–10 s.
