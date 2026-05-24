# Plan: FastAPI Backend + WebSocket Streaming + SQLite Persistence

## Summary
Wrap the Phase 2/3 simulation engine in a FastAPI service. The service runs the engine as a background asyncio task, streams per-tick `ValveState` updates over `/ws` to all subscribed dashboard clients, persists operational data + Layer events to SQLite per PRD §7.3, and exposes REST endpoints for scenario control (start, pause, reset, mode toggle, history query, health). After Phase 5, a developer can `uv run uvicorn backend.main:app` and a WebSocket client receives live state without the engine needing CLI invocation.

## User Story
As the software lead, I want the simulation engine wrapped in a network-accessible service streaming live state, so that Phase 6 (React dashboard) connects to one well-defined URL and the demo recording is driven by HTTP calls rather than CLI invocations.

## Problem → Solution
**Current state (after Phase 3):** `python -m sim.engine --mode chillvalve` runs the loop and writes a JSONL file. No live streaming, no HTTP surface, no DB persistence, no pause/resume.
**Desired state:**
- `uv run uvicorn backend.main:app --port 8000` starts the service
- `GET /health` → `{"status": "ok", "engine": "idle"|"running"|"paused"}`
- `POST /scenario/start?name=steady_state&mode=chillvalve` → engine begins ticking in the background; previous run (if any) is reset
- `POST /scenario/pause` → engine stops ticking but holds state; resumable
- `POST /scenario/reset` → engine returns to tick=0, idle
- `POST /mode/{mode}` → swap controller mid-run (belimo / chillvalve)
- `GET /history?since={timestamp}` → returns operational rows from SQLite
- `WebSocket /ws` → server pushes `{type, tick, valves, pump_kw, ...}` messages every 50 ms (real wall-clock, configurable)
- SQLite at `data/chillvalve.db` with the 4 tables from PRD §7.3; operational_data batched every 5 s; anomaly + coordination events written immediately

## Metadata
- **Complexity**: Large
- **Source PRD**: `docs/ChillValve_Implementation_PRD_v1.md`
- **PRD Phase**: Phase 5 — Backend (PRD §10 steps 20–24)
- **Estimated Files**: ~14 (5 source files in `backend/`, 5 test files, README + status, scenario JSON polish, REST schema models)

---

## UX Design

### Before
```
$ uv run python -m sim.engine --mode chillvalve
[engine] ticks=3600 ...
[summary] pump_kwh=3.77
$ cat data/runs/steady_state_chillvalve_*.jsonl | wc -l
3600
```
File-based output only.

### After
```
$ uv run uvicorn backend.main:app --port 8000 &
[uvicorn] running on 0.0.0.0:8000

$ curl -s localhost:8000/health
{"status":"ok","engine":"idle"}

$ curl -X POST 'localhost:8000/scenario/start?name=steady_state&mode=chillvalve'
{"status":"started","scenario":"steady_state","mode":"chillvalve","tick":0}

$ curl -s localhost:8000/health
{"status":"ok","engine":"running","scenario":"steady_state","mode":"chillvalve","tick":42}

$ websocat ws://localhost:8000/ws    # in another terminal
{"type":"state","tick":42,"pump_kw":3.86,"valves":[{"valve_id":"A1",...}]}
{"type":"state","tick":43,"pump_kw":3.86,...}
...

$ curl -X POST localhost:8000/scenario/pause
{"status":"paused","tick":42}

$ curl -s 'localhost:8000/history?since=0' | jq '.rows | length'
84   # 14 ticks × 6 valves = 84 rows
```

### Interaction Changes
| Touchpoint | Before | After | Notes |
|---|---|---|---|
| Engine start | CLI only | HTTP POST | Engine runs as background asyncio task |
| Live state | JSONL after run | WebSocket during run | 50 ms wall-clock cadence (configurable) |
| Persistence | JSONL files | SQLite tables | Per PRD §7.3 schema; co-exists with JSONL for now |
| Pause/resume | Not possible | Supported | Engine maintains its state |
| Multi-client | N/A | All connected /ws clients see same stream | Fan-out via asyncio.Queue per client |

---

## Mandatory Reading

| Priority | File | Lines | Why |
|---|---|---|---|
| P0 | `docs/ChillValve_Implementation_PRD_v1.md` | 696–793 | §7 — REST + WebSocket spec + orchestrator + SQLite schema |
| P0 | `sim/engine.py` | all | The synchronous tick loop we now wrap |
| P0 | `sim/controllers/chillvalve.py` | all | Mode swap target |
| P0 | `sim/controllers/belimo_baseline.py` | all | Mode swap target |
| P0 | `sim/system.py` | all | `HydraulicSystem` per-tick contract |
| P0 | `sim/scenarios.py` | all | `Scenario.load`; we mount on `data/scenarios/` |
| P1 | `docs/ChillValve_Implementation_PRD_v1.md` | 750–793 | §7.3 SQLite schema reference (literal column names) |
| P1 | `.claude/PRPs/reports/three-layer-intelligence-and-chillvalve-controller-report.md` | all | Deviations & loop-ordering wisdom from Phase 3 |

## External Documentation

| Topic | Source | Key Takeaway |
|---|---|---|
| FastAPI WebSocket | https://fastapi.tiangolo.com/advanced/websockets/ | `@app.websocket("/ws")` accepts then loops on `await websocket.send_json(...)` |
| asyncio background tasks | Python stdlib | `asyncio.create_task(coro())` schedules; cancel with `.cancel()` then `await task` (handles `CancelledError`) |
| Fan-out pub/sub in asyncio | stdlib | Per-client `asyncio.Queue(maxsize=64)`; producer puts to all; slow consumer drops on `QueueFull` |
| SQLite from async code | stdlib `sqlite3` + `aiosqlite` (or just sync inside `asyncio.to_thread`) | Phase 5 uses sync sqlite3 wrapped in `asyncio.to_thread` — keeps dependency surface minimal |
| FastAPI lifespan / startup | https://fastapi.tiangolo.com/advanced/events/ | `@asynccontextmanager` lifespan replaces deprecated `on_event` |
| TestClient / WebSocket testing | https://fastapi.tiangolo.com/advanced/testing-websockets/ | `with client.websocket_connect("/ws") as ws: ws.receive_json()` |

---

## Patterns to Mirror

### NAMING_CONVENTION
// SOURCE: Phase 1–3 codebase
- Modules: snake_case (`backend/main.py`, `backend/orchestrator.py`)
- Classes: PascalCase (`EngineService`, `ConnectionManager`)
- Functions: snake_case; private with `_`
- Constants UPPER_SNAKE; type hints `Optional[...]` / `List[...]` (no UP rules)

### ERROR_HANDLING
// SOURCE: `sim/valve.py`, `sim/pump.py`
- ValueError on invalid input at API boundary surfaces as HTTP 422 via FastAPI's pydantic; for our own validation, raise `HTTPException(400, "...")` explicitly
- No silent fallbacks; control-plane endpoints return clear error JSON

### TEST_STRUCTURE
// SOURCE: `tests/test_engine.py` (Phase 2/3)
```python
import pytest
from fastapi.testclient import TestClient
from backend.main import app

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c
```

### ENGINE_WRAPPING_PATTERN (new for Phase 5)
```python
# Background asyncio task drives the synchronous tick loop one step per cadence.
# Each tick: lock, advance simulation, snapshot, release, fan-out to WS clients, persist.
async def _engine_loop(self):
    while not self._stop.is_set():
        if self._paused.is_set():
            await asyncio.sleep(0.05)
            continue
        await asyncio.to_thread(self._tick_once)   # sync sim work off the event loop
        await self._fanout_state()
        await asyncio.sleep(self.tick_period_s)
```

### LIFESPAN_PATTERN
```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app):
    app.state.engine = EngineService()
    app.state.db = open_db(DB_PATH)
    yield
    await app.state.engine.shutdown()
    app.state.db.close()
```

---

## Files to Change

| File | Action | Justification |
|---|---|---|
| `backend/__init__.py` | UPDATE | Empty marker exists; add module docstring |
| `backend/db.py` | CREATE | SQLite schema per PRD §7.3; `open_db`, `write_operational_batch`, `write_anomaly_event`, `write_coordination_log`, `query_history` |
| `backend/models.py` | CREATE | Pydantic schemas for API responses (HealthResponse, ScenarioStartRequest, ScenarioStatus, HistoryResponse, WSStateMessage) |
| `backend/orchestrator.py` | CREATE | `EngineService` — wraps `HydraulicSystem` + controllers; owns the asyncio task; provides `start/pause/reset/set_mode`; emits state snapshots via async iterator |
| `backend/websocket.py` | CREATE | `ConnectionManager` — set of asyncio.Queue per client; broadcast helper that drops on `QueueFull` |
| `backend/main.py` | CREATE | FastAPI app with lifespan, REST endpoints, `/ws` handler |
| `tests/test_backend_db.py` | CREATE | Schema creation, batched write round-trip, history query |
| `tests/test_backend_orchestrator.py` | CREATE | start/pause/reset state machine; mode swap; tick advances during run |
| `tests/test_backend_websocket.py` | CREATE | TestClient WebSocket: connect, receive ≥3 state messages, disconnect cleanly |
| `tests/test_backend_rest.py` | CREATE | All REST endpoints happy + error paths |
| `tests/conftest.py` | CREATE | Shared fixtures: `app_with_tmp_db`, `running_engine` |
| `scripts/validate_backend_e2e.py` | CREATE | Smoke: start uvicorn in background, POST /scenario/start, drain /ws for 5 s, assert ≥ 50 state messages, POST /scenario/pause, exit 0 |
| `README.md` | UPDATE | "Run the backend" section + status |
| `pyproject.toml` | UPDATE | Add `httpx` to dev deps (FastAPI TestClient transitively, but explicit is clearer) |

## NOT Building

- **Auth / authz** — PRD §16 explicitly out of scope
- **Production WSGI/ASGI deployment config** (gunicorn, nginx) — local dev only
- **Cross-Origin** — adds CORS for the Phase 6 frontend (localhost:5173 only); no broader policy
- **Database migrations / schema versioning** — single hand-rolled schema, dropped/recreated on `--reset-db` flag
- **Real BACnet/IP integration** — PRD §7.2 explicitly accepts in-process broker
- **Live model retraining** — Phase 4 still external (handled by user on Colab)
- **JSONL output coexistence with SQLite** — switch to SQLite-only; JSONL was a Phase 2/3 convenience
- **WebSocket reconnection / heartbeats** — basic disconnect on TCP close; client (Phase 6) handles reconnect

---

## Step-by-Step Tasks

### Task 1: `backend/db.py` — SQLite schema + helpers
- **ACTION**: Implement schema, batched writes, history query.
- **IMPLEMENT** (key surface):
  ```python
  """SQLite persistence for ChillValve. PRD §7.3."""
  from __future__ import annotations
  import sqlite3
  from contextlib import contextmanager
  from pathlib import Path
  from typing import Iterable, List

  SCHEMA = """
  CREATE TABLE IF NOT EXISTS operational_data (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      timestamp_s REAL NOT NULL,
      valve_id TEXT NOT NULL,
      branch_id TEXT NOT NULL,
      flow_gpm REAL,
      dT_C REAL,
      position_pct REAL,
      dP_kPa REAL,
      mode TEXT
  );
  CREATE INDEX IF NOT EXISTS idx_op_timestamp ON operational_data(timestamp_s);
  CREATE INDEX IF NOT EXISTS idx_op_valve ON operational_data(valve_id);

  CREATE TABLE IF NOT EXISTS anomaly_events (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      timestamp_s REAL NOT NULL,
      valve_id TEXT NOT NULL,
      confidence REAL,
      features_json TEXT,
      resolution TEXT
  );

  CREATE TABLE IF NOT EXISTS coordination_log (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      timestamp_s REAL NOT NULL,
      branch_id TEXT NOT NULL,
      leader_id TEXT,
      event_type TEXT,
      payload_json TEXT
  );

  CREATE TABLE IF NOT EXISTS scenario_metadata (
      scenario_id TEXT PRIMARY KEY,
      started_at REAL,
      completed_at REAL,
      mode TEXT,
      final_pump_energy_kWh REAL,
      final_avg_dT_C REAL,
      anomaly_count INTEGER,
      election_count INTEGER
  );
  """


  def open_db(path: Path) -> sqlite3.Connection:
      path.parent.mkdir(parents=True, exist_ok=True)
      conn = sqlite3.connect(str(path), check_same_thread=False)
      conn.executescript(SCHEMA)
      conn.commit()
      return conn


  def write_operational_batch(conn: sqlite3.Connection, rows: Iterable[tuple]) -> None:
      """rows is iterable of (timestamp_s, valve_id, branch_id, flow_gpm, dT_C, position_pct, dP_kPa, mode)."""
      conn.executemany(
          "INSERT INTO operational_data "
          "(timestamp_s, valve_id, branch_id, flow_gpm, dT_C, position_pct, dP_kPa, mode) "
          "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
          rows,
      )
      conn.commit()


  def write_anomaly_event(conn, ts_s, valve_id, confidence, features_json, resolution="pending"):
      conn.execute(
          "INSERT INTO anomaly_events (timestamp_s, valve_id, confidence, features_json, resolution) "
          "VALUES (?, ?, ?, ?, ?)",
          (ts_s, valve_id, confidence, features_json, resolution),
      )
      conn.commit()


  def write_coordination_log(conn, ts_s, branch_id, leader_id, event_type, payload_json):
      conn.execute(
          "INSERT INTO coordination_log (timestamp_s, branch_id, leader_id, event_type, payload_json) "
          "VALUES (?, ?, ?, ?, ?)",
          (ts_s, branch_id, leader_id, event_type, payload_json),
      )
      conn.commit()


  def query_history(conn, since_s: float) -> List[dict]:
      cur = conn.execute(
          "SELECT timestamp_s, valve_id, branch_id, flow_gpm, dT_C, position_pct, dP_kPa, mode "
          "FROM operational_data WHERE timestamp_s >= ? ORDER BY timestamp_s, valve_id",
          (since_s,),
      )
      cols = ["timestamp_s", "valve_id", "branch_id", "flow_gpm", "dT_C", "position_pct", "dP_kPa", "mode"]
      return [dict(zip(cols, row, strict=False)) for row in cur.fetchall()]
  ```
- **MIRROR**: NAMING_CONVENTION; small focused functions; tested in isolation.
- **GOTCHA**:
  - `check_same_thread=False` because the connection is used from both the event loop and `asyncio.to_thread` workers.
  - PRD §7.3 schema names `timestamp TIMESTAMP`; we use `timestamp_s REAL` (Unix seconds) for simplicity. Document in code.
  - PRD's `INDEX idx_timestamp` syntax-in-CREATE-TABLE is non-portable; we use separate `CREATE INDEX` statements.
  - `executemany` is much faster than per-row `execute`; we batch operational data every 5 s × 6 valves = 30 rows per flush.
- **VALIDATE**: `tests/test_backend_db.py`.

### Task 2: `backend/models.py` — Pydantic schemas
- **ACTION**: Response/request models so endpoints have typed surfaces.
- **IMPLEMENT**:
  ```python
  """API schemas."""
  from __future__ import annotations
  from typing import List, Literal, Optional
  from pydantic import BaseModel


  Mode = Literal["belimo", "chillvalve"]
  EngineStatus = Literal["idle", "running", "paused"]


  class HealthResponse(BaseModel):
      status: str = "ok"
      engine: EngineStatus
      scenario: Optional[str] = None
      mode: Optional[Mode] = None
      tick: int = 0


  class StartResponse(BaseModel):
      status: Literal["started"]
      scenario: str
      mode: Mode
      tick: int


  class StatusResponse(BaseModel):
      status: EngineStatus
      tick: int
      scenario: Optional[str] = None
      mode: Optional[Mode] = None


  class HistoryRow(BaseModel):
      timestamp_s: float
      valve_id: str
      branch_id: str
      flow_gpm: float
      dT_C: float
      position_pct: float
      dP_kPa: float
      mode: Optional[str]


  class HistoryResponse(BaseModel):
      since_s: float
      rows: List[HistoryRow]


  class ValveSnapshot(BaseModel):
      valve_id: str
      branch_id: str
      flow_gpm: float
      dT_C: float
      position_pct: float
      is_leader: bool
      anomaly_detected: bool
      anomaly_confidence: float
      rule_fired: Optional[str]
      safety_override_active: bool


  class WSStateMessage(BaseModel):
      type: Literal["state"] = "state"
      tick: int
      pump_kw: float
      pump_head_kpa: float
      total_flow_gpm: float
      valves: List[ValveSnapshot]
  ```
- **MIRROR**: Pydantic v2 syntax (we already have pydantic≥2.13 in deps).
- **GOTCHA**: Use `Literal` for closed enums (mode, status) so OpenAPI is precise.
- **VALIDATE**: imports cleanly; `tests/test_backend_rest.py` round-trips models.

### Task 3: `backend/orchestrator.py` — `EngineService`
- **ACTION**: Class that owns the simulation; runs it as an asyncio task; exposes start/pause/reset/set_mode; broadcasts snapshots.
- **IMPLEMENT** (key surface):
  ```python
  """EngineService — async wrapper around the synchronous simulation engine."""
  from __future__ import annotations
  import asyncio
  import json
  import time
  from dataclasses import dataclass, field
  from pathlib import Path
  from typing import Any, Dict, List, Optional

  from sim.coil import Coil
  from sim.controllers.belimo_baseline import BelimoController
  from sim.controllers.chillvalve import ChillValveController
  from sim.scenarios import Scenario
  from sim.system import HydraulicSystem
  from sim.types import ValveState

  TICK_PERIOD_S = 0.05    # 20 Hz wall-clock; configurable via env or constructor
  OP_FLUSH_INTERVAL_S = 5.0


  @dataclass
  class EngineService:
      tick_period_s: float = TICK_PERIOD_S
      scenarios_dir: Path = Path(__file__).resolve().parent.parent / "data" / "scenarios"
      _system: Optional[HydraulicSystem] = None
      _controller: Optional[object] = None
      _scenario: Optional[Scenario] = None
      _mode: Optional[str] = None
      _tick: int = 0
      _task: Optional[asyncio.Task] = field(default=None, repr=False)
      _stop: asyncio.Event = field(default_factory=asyncio.Event, repr=False)
      _paused: asyncio.Event = field(default_factory=asyncio.Event, repr=False)
      _subscribers: List[asyncio.Queue] = field(default_factory=list, repr=False)
      _op_buffer: List[tuple] = field(default_factory=list, repr=False)
      _last_flush_at: float = 0.0
      _db_writer: Optional[Any] = None    # injected: a callable(rows) → None

      def attach_db_writer(self, writer) -> None:
          self._db_writer = writer

      def status(self) -> Dict[str, Any]:
          if self._task is None:
              return {"engine": "idle", "tick": 0, "scenario": None, "mode": None}
          if self._paused.is_set():
              state = "paused"
          else:
              state = "running"
          return {
              "engine": state, "tick": self._tick,
              "scenario": self._scenario.name if self._scenario else None,
              "mode": self._mode,
          }

      async def subscribe(self) -> asyncio.Queue:
          q: asyncio.Queue = asyncio.Queue(maxsize=64)
          self._subscribers.append(q)
          return q

      async def unsubscribe(self, q: asyncio.Queue) -> None:
          if q in self._subscribers:
              self._subscribers.remove(q)

      async def start(self, scenario_name: str, mode: str) -> Dict[str, Any]:
          if mode not in ("belimo", "chillvalve"):
              raise ValueError(f"unsupported mode: {mode!r}")
          await self.reset()
          self._scenario = Scenario.load(self.scenarios_dir / f"{scenario_name}.json")
          self._system = HydraulicSystem.build_default()
          if not self._scenario.valve_ids:
              self._scenario.valve_ids = list(self._system.valves.keys())
          self._mode = mode
          self._build_controller()
          self._stop.clear()
          self._paused.clear()
          self._task = asyncio.create_task(self._loop())
          return {"status": "started", "scenario": scenario_name, "mode": mode, "tick": 0}

      async def pause(self) -> None:
          self._paused.set()

      async def resume(self) -> None:
          self._paused.clear()

      async def reset(self) -> None:
          if self._task is not None:
              self._stop.set()
              try:
                  await self._task
              except asyncio.CancelledError:
                  pass
              self._task = None
          self._scenario = None
          self._system = None
          self._controller = None
          self._mode = None
          self._tick = 0
          self._op_buffer.clear()

      async def set_mode(self, mode: str) -> None:
          if mode not in ("belimo", "chillvalve"):
              raise ValueError(f"unsupported mode: {mode!r}")
          if self._task is None:
              raise RuntimeError("engine not started")
          self._mode = mode
          self._build_controller()

      async def shutdown(self) -> None:
          await self.reset()
          for q in list(self._subscribers):
              await self.unsubscribe(q)

      def _build_controller(self) -> None:
          if self._mode == "belimo":
              self._controller = BelimoController()
          else:
              c = ChillValveController()
              flow_max = {
                  vid: rec.coil.design_flow_gpm * 1.5
                  for vid, rec in self._system.valves.items()
              }
              c.initialize(list(self._system.valves.keys()), flow_max, t_seconds=float(self._tick))
              self._controller = c

      async def _loop(self) -> None:
          self._last_flush_at = time.monotonic()
          while not self._stop.is_set() and self._tick < self._scenario.duration_seconds:
              if self._paused.is_set():
                  await asyncio.sleep(0.05)
                  continue
              snapshot = await asyncio.to_thread(self._tick_once)
              await self._fanout(snapshot)
              if self._db_writer is not None:
                  self._buffer_operational(snapshot)
                  if time.monotonic() - self._last_flush_at >= OP_FLUSH_INTERVAL_S:
                      await asyncio.to_thread(self._db_writer, list(self._op_buffer))
                      self._op_buffer.clear()
                      self._last_flush_at = time.monotonic()
              await asyncio.sleep(self.tick_period_s)
          # Final flush.
          if self._db_writer and self._op_buffer:
              await asyncio.to_thread(self._db_writer, list(self._op_buffer))
              self._op_buffer.clear()

      def _tick_once(self) -> Dict[str, Any]:
          t = self._tick
          for rec in self._system.valves.values():
              rec.coil = Coil(
                  design_flow_gpm=rec.coil.design_flow_gpm,
                  design_dT_C=rec.coil.design_dT_C,
                  load_fraction=self._scenario.load_fraction(rec.valve_id, t),
              )
          states = self._system.tick(t)
          if self._mode == "belimo":
              commands = self._controller.step(states)
          else:
              commands = self._controller.step(states, t_seconds=float(t))
          self._system.set_positions(commands)
          total_flow = self._system.solve_network()
          head = self._system.pump.head_kpa(total_flow)
          pump_kw = self._system.pump.power_kw(total_flow, head)
          self._tick += 1
          return {
              "type": "state", "tick": t, "pump_kw": pump_kw,
              "pump_head_kpa": head, "total_flow_gpm": total_flow,
              "valves": [
                  {
                      "valve_id": s.valve_id, "branch_id": s.branch_id,
                      "flow_gpm": s.flow_gpm, "dT_C": s.dT_C,
                      "position_pct": s.position_pct,
                      "is_leader": s.is_leader,
                      "anomaly_detected": s.anomaly_detected,
                      "anomaly_confidence": s.anomaly_confidence,
                      "rule_fired": s.rule_fired,
                      "safety_override_active": s.safety_override_active,
                  }
                  for s in states
              ],
          }

      def _buffer_operational(self, snapshot: Dict[str, Any]) -> None:
          ts = float(snapshot["tick"])
          mode = self._mode
          for v in snapshot["valves"]:
              self._op_buffer.append((
                  ts, v["valve_id"], v["branch_id"],
                  v["flow_gpm"], v["dT_C"], v["position_pct"],
                  snapshot["pump_head_kpa"], mode,
              ))

      async def _fanout(self, snapshot: Dict[str, Any]) -> None:
          dead: List[asyncio.Queue] = []
          for q in self._subscribers:
              try:
                  q.put_nowait(snapshot)
              except asyncio.QueueFull:
                  # Slow consumer — drop snapshot for them.
                  pass
          # Cleanup of cancelled queues happens via unsubscribe.
  ```
- **MIRROR**: ENGINE_WRAPPING_PATTERN.
- **GOTCHA**:
  - `asyncio.to_thread` is critical — the simulation step has scipy's `brentq`, network solve, and small numpy work that would block the event loop if run inline.
  - `_subscribers` list is mutated from `subscribe`/`unsubscribe` (caller's coroutine) and read from `_fanout` (engine task). Since asyncio is single-threaded, this is safe as long as no `await` happens between read and write inside one transition — and `put_nowait` is sync.
  - `_paused` and `_stop` are `asyncio.Event` objects; setting them from a REST handler is safe (no thread crossing within a single event loop).
  - On `reset()`, we set stop then await the task — important to await so the next start() doesn't race with a half-dead loop.
- **VALIDATE**: `tests/test_backend_orchestrator.py`.

### Task 4: `backend/websocket.py` — connection manager (thin)
- **ACTION**: Tiny helper used by `/ws`. Actual queue ownership lives in `EngineService`.
- **IMPLEMENT**:
  ```python
  """WebSocket connection helpers."""
  from __future__ import annotations
  import asyncio
  from typing import AsyncIterator


  async def drain_queue(q: asyncio.Queue) -> AsyncIterator[dict]:
      while True:
          msg = await q.get()
          yield msg
  ```
  Kept minimal — the heavy lifting is in `EngineService.subscribe/unsubscribe`.
- **GOTCHA**: No graceful shutdown signal in `drain_queue` — caller handles `WebSocketDisconnect` and unsubscribes.

### Task 5: `backend/main.py` — FastAPI app
- **ACTION**: Wire everything together.
- **IMPLEMENT**:
  ```python
  """FastAPI app for ChillValve. PRD §7."""
  from __future__ import annotations
  from contextlib import asynccontextmanager
  from pathlib import Path
  from typing import Optional

  from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
  from fastapi.middleware.cors import CORSMiddleware

  from backend.db import open_db, query_history, write_operational_batch
  from backend.models import (
      HealthResponse, HistoryResponse, HistoryRow, StartResponse, StatusResponse,
  )
  from backend.orchestrator import EngineService
  from backend.websocket import drain_queue

  DB_PATH = Path(__file__).resolve().parent.parent / "data" / "chillvalve.db"


  @asynccontextmanager
  async def lifespan(app: FastAPI):
      conn = open_db(DB_PATH)
      engine = EngineService()
      engine.attach_db_writer(lambda rows: write_operational_batch(conn, rows))
      app.state.engine = engine
      app.state.db = conn
      try:
          yield
      finally:
          await engine.shutdown()
          conn.close()


  app = FastAPI(title="ChillValve Backend", version="0.5.0", lifespan=lifespan)
  app.add_middleware(
      CORSMiddleware,
      allow_origins=["http://localhost:5173"],
      allow_methods=["*"],
      allow_headers=["*"],
  )


  @app.get("/health", response_model=HealthResponse)
  async def health() -> HealthResponse:
      st = app.state.engine.status()
      return HealthResponse(
          status="ok", engine=st["engine"], scenario=st["scenario"],
          mode=st["mode"], tick=st["tick"],
      )


  @app.post("/scenario/start", response_model=StartResponse)
  async def start_scenario(name: str = Query("steady_state"), mode: str = Query("chillvalve")) -> StartResponse:
      try:
          result = await app.state.engine.start(name, mode)
      except ValueError as e:
          raise HTTPException(400, str(e))
      except FileNotFoundError:
          raise HTTPException(404, f"scenario not found: {name}")
      return StartResponse(**result)


  @app.post("/scenario/pause", response_model=StatusResponse)
  async def pause_scenario() -> StatusResponse:
      await app.state.engine.pause()
      st = app.state.engine.status()
      return StatusResponse(**st)


  @app.post("/scenario/resume", response_model=StatusResponse)
  async def resume_scenario() -> StatusResponse:
      await app.state.engine.resume()
      st = app.state.engine.status()
      return StatusResponse(**st)


  @app.post("/scenario/reset", response_model=StatusResponse)
  async def reset_scenario() -> StatusResponse:
      await app.state.engine.reset()
      st = app.state.engine.status()
      return StatusResponse(**st)


  @app.post("/mode/{mode}", response_model=StatusResponse)
  async def set_mode(mode: str) -> StatusResponse:
      try:
          await app.state.engine.set_mode(mode)
      except ValueError as e:
          raise HTTPException(400, str(e))
      except RuntimeError as e:
          raise HTTPException(409, str(e))
      st = app.state.engine.status()
      return StatusResponse(**st)


  @app.get("/history", response_model=HistoryResponse)
  async def history(since: float = Query(0.0, description="Unix seconds or tick number")) -> HistoryResponse:
      rows = query_history(app.state.db, since)
      return HistoryResponse(since_s=since, rows=[HistoryRow(**r) for r in rows])


  @app.websocket("/ws")
  async def ws_stream(websocket: WebSocket):
      await websocket.accept()
      q = await app.state.engine.subscribe()
      try:
          async for msg in drain_queue(q):
              await websocket.send_json(msg)
      except WebSocketDisconnect:
          pass
      finally:
          await app.state.engine.unsubscribe(q)
  ```
- **MIRROR**: LIFESPAN_PATTERN; consistent HTTPException error model.
- **GOTCHA**:
  - CORS allowed only for `localhost:5173` — Phase 6 frontend port.
  - `/scenario/start` rejects unknown scenarios with 404, unknown modes with 400.
  - `/mode/{mode}` returns 409 if engine isn't started (RuntimeError → conflict).
  - `/ws` subscribes BEFORE the engine starts producing. Clients that connect before `/scenario/start` will simply block on `q.get()` until ticks begin.
- **VALIDATE**: `tests/test_backend_rest.py`, `tests/test_backend_websocket.py`.

### Task 6: Tests
- **ACTION**: One test file per module + shared fixtures.
- **IMPLEMENT** (key cases per file):
  - `tests/conftest.py`:
    ```python
    @pytest.fixture
    def app_with_tmp_db(tmp_path, monkeypatch):
        from backend import main as backend_main
        monkeypatch.setattr(backend_main, "DB_PATH", tmp_path / "test.db")
        from fastapi.testclient import TestClient
        with TestClient(backend_main.app) as c:
            yield c
    ```
  - `test_backend_db.py`:
    - `open_db` creates 4 tables
    - `write_operational_batch` round-trips 12 rows → query_history returns them
    - `write_anomaly_event` writes; row count increments
    - `query_history(since=t)` filters correctly
  - `test_backend_orchestrator.py` (uses `asyncio` directly, no FastAPI):
    - `EngineService.status() == {"engine":"idle",...}` initially
    - After `start("steady_state","chillvalve")`, status becomes "running" and tick advances
    - `pause()` halts tick advancement
    - `reset()` returns to idle
    - `set_mode("belimo")` swaps controller mid-run
    - `set_mode("bogus")` raises ValueError
  - `test_backend_websocket.py`:
    - Connect to `/ws`, POST start, receive ≥ 3 state messages, each is valid JSON with `type=state`, `tick`, `valves`
    - Disconnect mid-stream → engine unsubscribes (verified by `len(engine._subscribers)==0`)
  - `test_backend_rest.py`:
    - `GET /health` returns engine=idle on a fresh app
    - `POST /scenario/start` returns 200 with started status
    - `POST /scenario/start?name=missing` → 404
    - `POST /scenario/start?mode=bogus` → 400
    - `POST /mode/belimo` without running engine → 409
    - `GET /history?since=0` returns rows after at least one flush
- **MIRROR**: TEST_STRUCTURE; FastAPI TestClient pattern.
- **GOTCHA**:
  - WebSocket tests must use `client.websocket_connect("/ws")`; this is sync-style but works with TestClient.
  - Some tests need to wait briefly for the engine to tick — use small `asyncio.sleep` or send/receive synchronously with TestClient.
  - SQLite tests use `tmp_path` to avoid polluting `data/chillvalve.db`.
- **VALIDATE**: `uv run pytest -v` — all pass.

### Task 7: `scripts/validate_backend_e2e.py`
- **ACTION**: Smoke validation that starts uvicorn, hits endpoints, drains WS.
- **IMPLEMENT**:
  ```python
  """E2E smoke for the FastAPI backend.

  Starts uvicorn in a subprocess on port 8765, drives a short scenario,
  drains the WebSocket for 5 seconds, asserts > 50 state messages, exits.

  Usage:
      uv run python scripts/validate_backend_e2e.py
  """
  from __future__ import annotations
  import asyncio
  import json
  import subprocess
  import sys
  import time
  from pathlib import Path

  sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

  import httpx  # noqa: E402
  import websockets  # noqa: E402

  PORT = 8765
  BASE = f"http://localhost:{PORT}"
  WS = f"ws://localhost:{PORT}/ws"


  async def drive() -> int:
      async with httpx.AsyncClient() as http:
          for _ in range(20):
              try:
                  r = await http.get(f"{BASE}/health")
                  if r.status_code == 200:
                      break
              except httpx.RequestError:
                  pass
              await asyncio.sleep(0.25)
          else:
              print("FAIL: server didn't come up", file=sys.stderr)
              return 1

          r = await http.post(f"{BASE}/scenario/start", params={"name": "steady_state", "mode": "chillvalve"})
          assert r.status_code == 200, r.text

          received = 0
          async with websockets.connect(WS) as ws:
              try:
                  while received < 100:
                      msg = await asyncio.wait_for(ws.recv(), timeout=2.0)
                      data = json.loads(msg)
                      assert data["type"] == "state"
                      received += 1
              except asyncio.TimeoutError:
                  pass
          print(f"validated: received {received} state messages")
          if received < 50:
              print(f"FAIL: only {received} messages in 2 s", file=sys.stderr)
              return 1
          await http.post(f"{BASE}/scenario/pause")
      return 0


  def main() -> int:
      proc = subprocess.Popen(
          [sys.executable, "-m", "uvicorn", "backend.main:app", "--port", str(PORT), "--log-level", "warning"],
          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
      )
      try:
          time.sleep(1.0)
          return asyncio.run(drive())
      finally:
          proc.terminate()
          try:
              proc.wait(timeout=3)
          except subprocess.TimeoutExpired:
              proc.kill()


  if __name__ == "__main__":
      sys.exit(main())
  ```
- **VALIDATE**: exits 0; PNG/JSONL files are NOT produced (this script bypasses the CLI engine).

### Task 8: pyproject + README + final sweep
- **ACTION**: Add `httpx` and `websockets-client` dev deps if missing (we already have `websockets` for uvicorn[standard]); update README; run ruff + pytest + validate.
- **VALIDATE**: All green.

---

## Testing Strategy

### Unit + Integration Tests
~20 new tests across 5 files. Combined with Phase 1–3's 78 → ~95–100 in suite.

### Edge Cases Checklist
- [ ] Start engine while already running → resets and restarts cleanly
- [ ] Mode swap mid-run preserves tick counter
- [ ] WebSocket disconnect during message send → engine unsubscribes
- [ ] Multiple WebSocket clients receive identical streams
- [ ] Slow client doesn't block fast clients (`QueueFull` drop)
- [ ] Pause then resume continues from same tick
- [ ] Reset then start with different scenario works
- [ ] Invalid scenario name → 404
- [ ] Invalid mode → 400
- [ ] `/history?since=large_value` returns empty list (not error)

---

## Validation Commands

### Static Analysis
```bash
uv run ruff check .
```

### Tests
```bash
uv run pytest -v
```
EXPECT: ~95+ tests pass.

### Coverage
```bash
uv run pytest --cov=backend --cov=sim --cov-report=term-missing
```
EXPECT: ≥ 85% on `backend/`, ≥ 90% on `sim/`.

### Backend smoke
```bash
uv run python scripts/validate_backend_e2e.py
```
EXPECT: Exit 0 with `received N state messages` where N > 50.

### Manual
```bash
uv run uvicorn backend.main:app --port 8000 &
curl localhost:8000/health
curl -X POST 'localhost:8000/scenario/start?name=steady_state&mode=chillvalve'
# In another terminal:
websocat ws://localhost:8000/ws | head -5
curl -X POST localhost:8000/scenario/pause
kill %1
```

---

## Acceptance Criteria
- [ ] All tasks 1–8 completed
- [ ] Ruff and pytest green
- [ ] WebSocket streams ≥ 20 messages per second (1 message per simulated tick at 50 ms cadence = 20 Hz)
- [ ] All 4 SQLite tables created on startup
- [ ] Operational data persisted (batched flush every 5 s)
- [ ] All REST endpoints documented in OpenAPI auto-spec (visit `/docs`)
- [ ] PRD §15 acceptance criterion #1 fully met for backend ("simulation runs end-to-end without crashes for at least 60 simulated minutes in both modes" — now driven by HTTP)

## Completion Checklist
- [ ] Code follows Phase 1–3 patterns
- [ ] No CORS wildcards; locked to `http://localhost:5173`
- [ ] `EngineService` is the only owner of mutable simulation state
- [ ] No global singletons except via `app.state`
- [ ] SQLite path uses `tmp_path` in tests, real path in prod
- [ ] No threading; all concurrency is asyncio + `asyncio.to_thread`
- [ ] WebSocket fan-out drops on slow consumer; no head-of-line blocking
- [ ] OpenAPI surface is meaningful (Literal modes, response models everywhere)

## Risks
| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| `asyncio.to_thread` doesn't truly parallelize sim step → engine starves | Medium | Medium | tick_period_s=0.05 leaves ample headroom (sim step is <5 ms); confirmed by E2E smoke (50+ msgs/sec) |
| Test client WebSocket vs real WebSocket semantics differ | Low | Low | Use `from fastapi.testclient import TestClient`; same protocol surface |
| SQLite write contention from multiple flushes | Low | Low | Single writer thread (the engine task → to_thread); reads from REST also go through to_thread eventually |
| Pause/reset race conditions | Medium | Medium | All control methods await prior task; tests cover pause-then-reset, reset-then-start |
| WebSocket disconnect cleanup leaks queues | Medium | Low | `finally: unsubscribe` in `/ws` handler; tests verify `len(subscribers) == 0` after disconnect |
| Phase 4 ML pending — Layer 2 still placeholder during backend tests | N/A | None | Backend is layer-agnostic; placeholder works fine |

## Notes
- Tick cadence is `TICK_PERIOD_S = 0.05` (20 Hz wall-clock × 1 simulated second per tick). At this rate, a 60-min simulated scenario plays back in 60 × 60 × 0.05 = 180 wall-clock seconds. Configurable via constructor for faster demo replay.
- We keep `sim/engine.py` CLI intact for offline runs — backend doesn't replace it, it wraps the same `HydraulicSystem` + controllers.
- SQLite is in `data/chillvalve.db` per PRD §3. The directory was created in Phase 1.
- `backend/orchestrator.py` filename matches PRD §3 even though our class is `EngineService` (PRD shows `MessageBroker` there; the broker now lives in `sim/broker.py` and stays there to avoid an import cycle).

---

**Confidence Score: 7/10** — Large but mechanical. Highest risk is the asyncio/sync boundary around `to_thread` and the WebSocket fan-out queue semantics. Plan covers both with explicit tests.
