"""Tests for backend/db.py."""
from __future__ import annotations

from backend.db import (
    open_db,
    query_history,
    write_anomaly_event,
    write_coordination_log,
    write_operational_batch,
)


def test_open_db_creates_four_tables(tmp_db_path):
    conn = open_db(tmp_db_path)
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = sorted(row[0] for row in cur.fetchall())
    expected = ["anomaly_events", "coordination_log", "operational_data", "scenario_metadata"]
    for e in expected:
        assert e in tables


def test_operational_batch_roundtrip(tmp_db_path):
    conn = open_db(tmp_db_path)
    rows = [
        (1.0, "A1", "A", 22.0, 5.0, 50.0, 100.0, "chillvalve"),
        (1.0, "B1", "B", 70.0, 5.0, 50.0, 100.0, "chillvalve"),
    ]
    write_operational_batch(conn, rows)
    out = query_history(conn, 0.0)
    assert len(out) == 2
    assert out[0]["valve_id"] == "A1"
    assert out[1]["valve_id"] == "B1"


def test_query_history_filters_by_since(tmp_db_path):
    conn = open_db(tmp_db_path)
    write_operational_batch(conn, [
        (1.0, "A1", "A", 1.0, 1.0, 1.0, 1.0, "x"),
        (5.0, "A1", "A", 2.0, 2.0, 2.0, 2.0, "x"),
        (10.0, "A1", "A", 3.0, 3.0, 3.0, 3.0, "x"),
    ])
    assert len(query_history(conn, 0.0)) == 3
    assert len(query_history(conn, 5.0)) == 2
    assert len(query_history(conn, 11.0)) == 0


def test_anomaly_event_persisted(tmp_db_path):
    conn = open_db(tmp_db_path)
    write_anomaly_event(conn, 2.5, "B2", 0.93, '{"x":1}', "escalated")
    cur = conn.execute("SELECT valve_id, confidence, resolution FROM anomaly_events")
    rows = cur.fetchall()
    assert len(rows) == 1
    assert rows[0] == ("B2", 0.93, "escalated")


def test_coordination_log_persisted(tmp_db_path):
    conn = open_db(tmp_db_path)
    write_coordination_log(conn, 3.0, "A", "A1", "election", '{"winner":"A1"}')
    cur = conn.execute("SELECT branch_id, leader_id, event_type FROM coordination_log")
    rows = cur.fetchall()
    assert rows == [("A", "A1", "election")]
