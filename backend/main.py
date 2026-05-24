"""FastAPI app for ChillValve. PRD §7."""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from backend.db import open_db, query_history, write_operational_batch
from backend.models import (
    HealthResponse,
    HistoryResponse,
    HistoryRow,
    StartResponse,
    StatusResponse,
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
async def start_scenario(
    name: str = Query("steady_state"),
    mode: str = Query("chillvalve"),
) -> StartResponse:
    try:
        result = await app.state.engine.start(name, mode)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    except FileNotFoundError:
        raise HTTPException(404, f"scenario not found: {name}") from None
    return StartResponse(**result)


@app.post("/scenario/pause", response_model=StatusResponse)
async def pause_scenario() -> StatusResponse:
    await app.state.engine.pause()
    return StatusResponse(**app.state.engine.status())


@app.post("/scenario/resume", response_model=StatusResponse)
async def resume_scenario() -> StatusResponse:
    await app.state.engine.resume()
    return StatusResponse(**app.state.engine.status())


@app.post("/scenario/reset", response_model=StatusResponse)
async def reset_scenario() -> StatusResponse:
    await app.state.engine.reset()
    return StatusResponse(**app.state.engine.status())


@app.post("/mode/{mode}", response_model=StatusResponse)
async def set_mode(mode: str) -> StatusResponse:
    try:
        await app.state.engine.set_mode(mode)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    except RuntimeError as e:
        raise HTTPException(409, str(e)) from e
    return StatusResponse(**app.state.engine.status())


@app.post("/agent/{valve_id}/kill_leader", response_model=StatusResponse)
async def kill_leader(valve_id: str) -> StatusResponse:
    try:
        await app.state.engine.kill_leader(valve_id)
    except ValueError as e:
        raise HTTPException(404, str(e)) from e
    except RuntimeError as e:
        raise HTTPException(409, str(e)) from e
    return StatusResponse(**app.state.engine.status())


@app.get("/history", response_model=HistoryResponse)
async def history(
    since: float = Query(0.0, description="Tick number or Unix seconds"),
) -> HistoryResponse:
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
