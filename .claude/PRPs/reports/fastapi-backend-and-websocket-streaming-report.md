# Implementation Report: FastAPI Backend + WebSocket Streaming + SQLite Persistence

## Summary
Wrapped the Phase 2/3 synchronous simulation engine in a FastAPI service driven by an asyncio task. State streams over `/ws` at 20 Hz wall-clock to all subscribed clients; REST endpoints control scenario lifecycle and mode swap; operational data is batched into SQLite per PRD §7.3.

## Assessment vs Reality

| Metric | Predicted (Plan) | Actual |
|---|---|---|
| Complexity | Large | Large |
| Confidence | 7/10 | 8/10 (smoother than expected — no asyncio surprises) |
| Files Changed | ~14 | 14 |
| Test count | ~20 new | 25 new tests; 103 total in suite |
| Coverage | ≥ 85% backend, ≥ 90% sim | 93–100% backend; 90+% sim — overall 96% |

## Tasks Completed

| # | Task | Status | Notes |
|---|---|---|---|
| 1 | backend/db.py | Complete | 4 tables, batched + immediate writes, history query |
| 2 | backend/models.py | Complete | Pydantic v2 with `Literal` enums |
| 3 | backend/orchestrator.py | Complete | `EngineService` 150 LOC; `asyncio.to_thread` for sim step; `asyncio.Queue` fan-out |
| 4 | backend/main.py + websocket.py | Complete | Lifespan, 7 REST endpoints + `/ws`, CORS for `localhost:5173` |
| 5 | 4 test files + conftest | Complete | 25 cases incl. async orchestrator tests via `pytest-asyncio` |
| 6 | validate_backend_e2e.py + httpx + README | Complete | Smoke received 100/100 WS messages in 2 seconds |

## Validation Results

| Level | Status | Notes |
|---|---|---|
| Ruff | Pass | All checks passed |
| Pytest | Pass | 103/103 (stable across 3 reruns) |
| Coverage | Pass | 96% overall; backend/db 100%; backend/models 100%; backend/main 93%; backend/orchestrator 94% |
| E2E smoke | Pass | uvicorn launched in subprocess; 100 state messages drained in 2s |

## Files Changed

| File | Action | Lines |
|---|---|---|
| `backend/__init__.py` | UPDATED | docstring |
| `backend/db.py` | CREATED | 105 |
| `backend/models.py` | CREATED | 71 |
| `backend/orchestrator.py` | CREATED | 196 |
| `backend/websocket.py` | CREATED | 11 |
| `backend/main.py` | CREATED | 114 |
| `tests/conftest.py` | CREATED | 22 |
| `tests/test_backend_db.py` | CREATED | 5 cases |
| `tests/test_backend_orchestrator.py` | CREATED | 11 cases |
| `tests/test_backend_rest.py` | CREATED | 7 cases |
| `tests/test_backend_websocket.py` | CREATED | 2 cases |
| `tests/test_scenarios.py` | UPDATED | bound tolerance fix for floating-point edge |
| `scripts/validate_backend_e2e.py` | CREATED | 71 |
| `pyproject.toml` | UPDATED | `asyncio_mode = "auto"`, +`pytest-asyncio`, +`httpx` (dev) |
| `README.md` | UPDATED | "Run the backend" section + Phase 5 status |

## Deviations from Plan

1. **Pytest `asyncio_mode = "auto"`**
   - **WHAT:** Plan implied explicit `@pytest.mark.asyncio` decorators.
   - **WHY:** Setting `asyncio_mode = "auto"` in `pyproject.toml` removes the need to decorate every async test. The orchestrator tests already use `await` extensively; auto mode keeps the code cleaner.

2. **Added `httpx` as dev dependency**
   - **WHAT:** Plan mentioned httpx for the smoke script. After adding pytest-asyncio, `fastapi.testclient.TestClient` errored because starlette's TestClient now requires httpx as a hard dep.
   - **WHY:** Required for `TestClient` instantiation in test fixtures. `uv add --dev httpx` resolved it.

3. **Tightened `test_load_fraction_stays_within_amplitude` bounds with ±1e-9 tolerance**
   - **WHAT:** Phase 2 test asserted strict `0.65 <= f <= 0.75`.
   - **WHY:** Python's hash randomization makes the per-valve phase offset non-deterministic, and at peaks `sin(...) == 1.0` can produce `f = base + amp + tiny_FP_error`. The strict bound rejected values one ULP over the limit. Added ±1e-9 tolerance. Test now stable across 3 reruns.

4. **`EngineService._fanout` uses `put_nowait` without back-pressure**
   - **WHAT:** Plan said queue maxsize=64 with drop-on-full.
   - **WHY:** Exactly that, but worth flagging: a permanently-slow consumer means missed snapshots. The Phase 6 dashboard is expected to consume at 20 Hz (well under maxsize), so this is fine. If we add metrics later, surface a per-subscriber drop counter.

5. **`EngineService` uses `asyncio.Event` lazily** (`field(default=None)`)
   - **WHAT:** Plan had Event objects in `field(default_factory=asyncio.Event)`.
   - **WHY:** Creating `asyncio.Event` outside a running loop is fine in Python ≥3.10, but the `factory` runs at dataclass construction time. To be safe across Python versions and avoid "no running event loop" warnings, the Events are created inside `start()` and cleared in `reset()`.

## Issues Encountered

1. **`fastapi.testclient` required `httpx`** (Task 5). Resolved with `uv add --dev httpx`. Caught immediately by first pytest run.
2. **Flaky scenarios bound assertion** (Task 6 sweep). Resolved with FP tolerance. Caught only after running coverage which had different ordering than basic pytest.
3. **Brief uvicorn boot delay** during the live-curl smoke check (1.5s wasn't enough). Validate script uses a retry loop (`for _ in range(40): try health()`) so it's robust.

## Tests Written

| Test File | Tests | Coverage |
|---|---|---|
| `tests/conftest.py` | (fixtures) | `tmp_db_path`, `client_with_tmp_db` shared by all backend tests |
| `tests/test_backend_db.py` | 5 | Schema, batch roundtrip, history filter, anomaly + coordination event persistence |
| `tests/test_backend_orchestrator.py` | 11 | Idle status, start advances, pause/resume, reset → idle, mode swap, invalid mode/scenario, subscriber receives snapshots |
| `tests/test_backend_rest.py` | 7 | All endpoints happy path + 4xx error paths (404 scenario, 400 mode, 409 unstarted mode swap) |
| `tests/test_backend_websocket.py` | 2 | Receives state messages, unsubscribes cleanly on disconnect |

## Acceptance Criteria

- [x] All tasks 1–6 completed
- [x] Ruff and pytest green (103/103)
- [x] WebSocket streams ≥ 20 msg/sec (smoke received 100 in ~2 s = 50/sec)
- [x] All 4 SQLite tables created on startup
- [x] Operational data persisted (batched flush every 5 s)
- [x] OpenAPI spec at `/docs` (verified via FastAPI app construction)
- [x] PRD §15 acceptance #1 met for backend: simulation drives end-to-end over HTTP

## Next Steps

- [ ] **Phase 4** — wire user's Colab-trained Isolation Forest into `sim/layers/layer2_ml.py` when the user delivers `data/models/isolation_forest.pkl` + scaler + metadata
- [ ] **Phase 6** — React + Vite dashboard consuming `/ws`; CORS is already configured for `localhost:5173`
- [ ] **Phase 7** — integration polish, fault-injection scenario C (needs Phase 4 ML), demo recording
