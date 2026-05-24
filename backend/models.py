"""API schemas for the ChillValve backend."""
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
    engine: EngineStatus
    tick: int
    scenario: Optional[str] = None
    mode: Optional[Mode] = None


class HistoryRow(BaseModel):
    timestamp_s: float
    valve_id: str
    branch_id: str
    flow_gpm: Optional[float]
    dT_C: Optional[float]
    position_pct: Optional[float]
    dP_kPa: Optional[float]
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
