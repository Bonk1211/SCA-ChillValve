"""EngineService — async wrapper around the synchronous simulation engine.

The simulation work itself stays in sim/; this module owns the event-loop-level
state machine (start/pause/reset/set_mode), fan-out to WebSocket subscribers,
and batched persistence to SQLite.
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from sim.coil import Coil
from sim.controllers.belimo_baseline import BelimoController
from sim.controllers.chillvalve import ChillValveController
from sim.scenarios import Scenario
from sim.system import HydraulicSystem

TICK_PERIOD_S = 0.05         # 20 Hz wall-clock
OP_FLUSH_INTERVAL_S = 5.0    # flush operational batch every 5 wall-seconds
SUBSCRIBER_QUEUE_SIZE = 64


@dataclass
class EngineService:
    tick_period_s: float = TICK_PERIOD_S
    scenarios_dir: Path = field(
        default_factory=lambda: Path(__file__).resolve().parent.parent / "data" / "scenarios"
    )
    _system: Optional[HydraulicSystem] = None
    _controller: Optional[object] = None
    _scenario: Optional[Scenario] = None
    _mode: Optional[str] = None
    _tick: int = 0
    _task: Optional[asyncio.Task] = field(default=None, repr=False)
    _stop: Optional[asyncio.Event] = field(default=None, repr=False)
    _paused: Optional[asyncio.Event] = field(default=None, repr=False)
    _subscribers: List[asyncio.Queue] = field(default_factory=list, repr=False)
    _op_buffer: List[tuple] = field(default_factory=list, repr=False)
    _last_flush_at: float = 0.0
    _db_writer: Optional[Callable[[List[tuple]], None]] = field(default=None, repr=False)

    def attach_db_writer(self, writer: Callable[[List[tuple]], None]) -> None:
        self._db_writer = writer

    def status(self) -> Dict[str, Any]:
        if self._task is None or self._task.done():
            return {"engine": "idle", "tick": 0, "scenario": None, "mode": None}
        state = "paused" if (self._paused and self._paused.is_set()) else "running"
        return {
            "engine": state,
            "tick": self._tick,
            "scenario": self._scenario.name if self._scenario else None,
            "mode": self._mode,
        }

    async def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=SUBSCRIBER_QUEUE_SIZE)
        self._subscribers.append(q)
        return q

    async def unsubscribe(self, q: asyncio.Queue) -> None:
        if q in self._subscribers:
            self._subscribers.remove(q)

    async def start(self, scenario_name: str, mode: str) -> Dict[str, Any]:
        if mode not in ("belimo", "chillvalve"):
            raise ValueError(f"unsupported mode: {mode!r}")
        await self.reset()
        scenario_path = self.scenarios_dir / f"{scenario_name}.json"
        if not scenario_path.exists():
            raise FileNotFoundError(scenario_path)
        self._scenario = Scenario.load(scenario_path)
        self._system = HydraulicSystem.build_default()
        if not self._scenario.valve_ids:
            self._scenario.valve_ids = list(self._system.valves.keys())
        self._mode = mode
        self._build_controller()
        self._stop = asyncio.Event()
        self._paused = asyncio.Event()
        self._task = asyncio.create_task(self._loop())
        return {"status": "started", "scenario": scenario_name, "mode": mode, "tick": 0}

    async def pause(self) -> None:
        if self._paused is not None:
            self._paused.set()

    async def resume(self) -> None:
        if self._paused is not None:
            self._paused.clear()

    async def reset(self) -> None:
        if self._task is not None:
            if self._stop is not None:
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
        self._stop = None
        self._paused = None

    async def set_mode(self, mode: str) -> None:
        if mode not in ("belimo", "chillvalve"):
            raise ValueError(f"unsupported mode: {mode!r}")
        if self._task is None or self._task.done():
            raise RuntimeError("engine not started")
        self._mode = mode
        self._build_controller()

    async def shutdown(self) -> None:
        await self.reset()
        self._subscribers.clear()

    def _build_controller(self) -> None:
        assert self._system is not None
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
        assert self._scenario is not None
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
                    buf = list(self._op_buffer)
                    self._op_buffer.clear()
                    await asyncio.to_thread(self._db_writer, buf)
                    self._last_flush_at = time.monotonic()
            await asyncio.sleep(self.tick_period_s)
        # Final flush.
        if self._db_writer is not None and self._op_buffer:
            buf = list(self._op_buffer)
            self._op_buffer.clear()
            await asyncio.to_thread(self._db_writer, buf)

    def _tick_once(self) -> Dict[str, Any]:
        assert self._system is not None
        assert self._scenario is not None
        t = self._tick
        for rec in self._system.valves.values():
            rec.coil = Coil(
                design_flow_gpm=rec.coil.design_flow_gpm,
                design_dT_C=rec.coil.design_dT_C,
                load_fraction=self._scenario.load_fraction(rec.valve_id, t),
            )
        states = self._system.tick(t)
        if self._mode == "belimo":
            commands = self._controller.step(states)  # type: ignore[union-attr]
        else:
            commands = self._controller.step(states, t_seconds=float(t))  # type: ignore[union-attr]
        self._system.set_positions(commands)
        total_flow = self._system.solve_network()
        head = self._system.pump.head_kpa(total_flow)
        pump_kw = self._system.pump.power_kw(total_flow, head)
        self._tick += 1
        return {
            "type": "state",
            "tick": t,
            "pump_kw": pump_kw,
            "pump_head_kpa": head,
            "total_flow_gpm": total_flow,
            "valves": [
                {
                    "valve_id": s.valve_id,
                    "branch_id": s.branch_id,
                    "flow_gpm": s.flow_gpm,
                    "dT_C": s.dT_C,
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
        for q in self._subscribers:
            try:
                q.put_nowait(snapshot)
            except asyncio.QueueFull:
                # Slow consumer — drop this snapshot for them.
                pass
