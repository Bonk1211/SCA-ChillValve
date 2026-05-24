"""Tests for backend/main.py /ws endpoint."""
from __future__ import annotations

import time


def test_websocket_receives_state_messages(client_with_tmp_db):
    # Start a scenario first so the engine produces snapshots.
    client_with_tmp_db.post(
        "/scenario/start", params={"name": "steady_state", "mode": "chillvalve"}
    )
    time.sleep(0.05)
    with client_with_tmp_db.websocket_connect("/ws") as ws:
        msgs = []
        for _ in range(3):
            msgs.append(ws.receive_json())
    assert len(msgs) == 3
    for m in msgs:
        assert m["type"] == "state"
        assert "tick" in m
        assert len(m["valves"]) == 6
    client_with_tmp_db.post("/scenario/reset")


def test_websocket_unsubscribes_on_disconnect(client_with_tmp_db):
    from backend import main as backend_main
    engine = backend_main.app.state.engine
    client_with_tmp_db.post(
        "/scenario/start", params={"name": "steady_state", "mode": "chillvalve"}
    )
    time.sleep(0.05)
    with client_with_tmp_db.websocket_connect("/ws") as ws:
        ws.receive_json()
        assert len(engine._subscribers) >= 1
    # Give the server a moment to process the disconnect.
    time.sleep(0.1)
    assert len(engine._subscribers) == 0
    client_with_tmp_db.post("/scenario/reset")
