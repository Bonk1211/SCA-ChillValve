"""SQLite persistence for ChillValve. PRD §7.3.

Schema names differ slightly from PRD §7.3 verbatim:
  - timestamps are REAL Unix seconds (or simulated tick numbers), not TIMESTAMP
  - indexes are separate CREATE INDEX statements (portable SQLite)
"""
from __future__ import annotations

import sqlite3
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
    """rows: iterable of (timestamp_s, valve_id, branch_id, flow_gpm, dT_C, position_pct, dP_kPa, mode)."""
    conn.executemany(
        "INSERT INTO operational_data "
        "(timestamp_s, valve_id, branch_id, flow_gpm, dT_C, position_pct, dP_kPa, mode) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        rows,
    )
    conn.commit()


def write_anomaly_event(
    conn: sqlite3.Connection,
    timestamp_s: float,
    valve_id: str,
    confidence: float,
    features_json: str,
    resolution: str = "pending",
) -> None:
    conn.execute(
        "INSERT INTO anomaly_events (timestamp_s, valve_id, confidence, features_json, resolution) "
        "VALUES (?, ?, ?, ?, ?)",
        (timestamp_s, valve_id, confidence, features_json, resolution),
    )
    conn.commit()


def write_coordination_log(
    conn: sqlite3.Connection,
    timestamp_s: float,
    branch_id: str,
    leader_id: str,
    event_type: str,
    payload_json: str,
) -> None:
    conn.execute(
        "INSERT INTO coordination_log "
        "(timestamp_s, branch_id, leader_id, event_type, payload_json) "
        "VALUES (?, ?, ?, ?, ?)",
        (timestamp_s, branch_id, leader_id, event_type, payload_json),
    )
    conn.commit()


def query_history(conn: sqlite3.Connection, since_s: float) -> List[dict]:
    cur = conn.execute(
        "SELECT timestamp_s, valve_id, branch_id, flow_gpm, dT_C, position_pct, dP_kPa, mode "
        "FROM operational_data WHERE timestamp_s >= ? "
        "ORDER BY timestamp_s, valve_id",
        (since_s,),
    )
    cols = ["timestamp_s", "valve_id", "branch_id", "flow_gpm", "dT_C",
            "position_pct", "dP_kPa", "mode"]
    return [dict(zip(cols, row, strict=False)) for row in cur.fetchall()]
