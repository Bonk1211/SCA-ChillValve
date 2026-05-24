# SCA-ChillValve

Distributed cooperative-control prototype for HVAC valves in tropical data centers.
See `docs/ChillValve_Implementation_PRD_v1.md` for the full spec.

## Quickstart

```bash
uv sync
uv run pytest
uv run python scripts/plot_cv_curves.py   # writes docs/cv_curves.png
```

## Run a scenario from the CLI

```bash
uv run python -m sim.engine --mode belimo
uv run python -m sim.engine --mode chillvalve
uv run python -m sim.engine --mode compare
```

Per-tick JSONL timeseries lands in `data/runs/{scenario}_{mode}_{timestamp}.jsonl`.

## Run the backend (FastAPI + WebSocket)

```bash
uv run uvicorn backend.main:app --port 8000
```

Then in another terminal:

```bash
curl localhost:8000/health
curl -X POST 'localhost:8000/scenario/start?name=steady_state&mode=chillvalve'
curl localhost:8000/health
# Stream live state:
websocat ws://localhost:8000/ws    # or any WebSocket client
curl -X POST localhost:8000/scenario/pause
curl 'localhost:8000/history?since=0' | jq '.rows | length'
```

OpenAPI spec served at `http://localhost:8000/docs`.

State is streamed at 20 Hz wall-clock (1 simulated second per 50 ms),
operational data is batched into `data/chillvalve.db` every 5 seconds,
and the WebSocket fan-out drops snapshots for slow consumers rather than
blocking the engine.

### Validation scripts

```bash
uv run python scripts/validate_baseline_energy.py        # Belimo kWh / dT bands
uv run python scripts/validate_chillvalve_vs_belimo.py   # compare modes complete
uv run python scripts/validate_backend_e2e.py            # backend + WS smoke
```

## Status

Phase 5 (FastAPI Backend) — complete.

- `backend/db.py`: SQLite schema for operational data, anomaly events, coordination log, scenario metadata (PRD §7.3)
- `backend/models.py`: Pydantic v2 schemas for REST + WebSocket payloads
- `backend/orchestrator.py`: `EngineService` runs the sim as an asyncio task; `asyncio.to_thread` keeps the event loop unblocked; per-client `asyncio.Queue` fan-out drops on slow consumer
- `backend/main.py`: FastAPI app with lifespan, REST endpoints (`/health`, `/scenario/{start,pause,resume,reset}`, `/mode/{mode}`, `/history`) and WebSocket `/ws`
- CORS locked to `http://localhost:5173` for the upcoming Phase 6 dashboard

Next: Phase 4 (ML training, pending external Colab work by the user) and Phase 6 (React + Vite dashboard).

## Repository layout

See PRD §3 for the canonical tree.

## Troubleshooting

- **`scikit-learn` install fails on macOS** — install Xcode CLI tools: `xcode-select --install`, then `uv sync` again.
