"""Tests for backend/main.py REST endpoints."""
from __future__ import annotations

import time


def test_health_idle(client_with_tmp_db):
    r = client_with_tmp_db.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["engine"] == "idle"
    assert data["status"] == "ok"


def test_start_returns_started(client_with_tmp_db):
    r = client_with_tmp_db.post(
        "/scenario/start", params={"name": "steady_state", "mode": "chillvalve"}
    )
    assert r.status_code == 200
    assert r.json()["status"] == "started"
    client_with_tmp_db.post("/scenario/reset")


def test_start_missing_scenario_returns_404(client_with_tmp_db):
    r = client_with_tmp_db.post(
        "/scenario/start", params={"name": "ghost", "mode": "chillvalve"}
    )
    assert r.status_code == 404


def test_start_invalid_mode_returns_400(client_with_tmp_db):
    r = client_with_tmp_db.post(
        "/scenario/start", params={"name": "steady_state", "mode": "bogus"}
    )
    assert r.status_code == 400


def test_mode_swap_without_start_returns_409(client_with_tmp_db):
    r = client_with_tmp_db.post("/mode/belimo")
    assert r.status_code == 409


def test_pause_then_reset(client_with_tmp_db):
    client_with_tmp_db.post(
        "/scenario/start", params={"name": "steady_state", "mode": "chillvalve"}
    )
    time.sleep(0.05)
    r = client_with_tmp_db.post("/scenario/pause")
    assert r.status_code == 200
    assert r.json()["engine"] == "paused"
    r = client_with_tmp_db.post("/scenario/reset")
    assert r.json()["engine"] == "idle"


def test_history_empty_initially(client_with_tmp_db):
    r = client_with_tmp_db.get("/history", params={"since": 0})
    assert r.status_code == 200
    assert r.json()["rows"] == []
