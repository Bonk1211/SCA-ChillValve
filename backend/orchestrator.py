"""EngineService — async wrapper around the synchronous simulation engine.

The simulation work itself stays in sim/; this module owns the event-loop-level
state machine (start/pause/reset/set_mode), fan-out to WebSocket subscribers,
and batched persistence to SQLite.
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

log = logging.getLogger(__name__)

from backend.debate import (
    RECOVERY_ANOMALY_PERSISTENCE_S,
    DebateRunner,
    RecoveryDecision,
    is_uncertain_branch,
)
from backend.explainer import Explainer
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
    _explainer: Explainer = field(default_factory=Explainer, repr=False)
    _last_leaders: Dict[str, Optional[str]] = field(default_factory=dict, repr=False)
    _killed_recently: Dict[str, float] = field(default_factory=dict, repr=False)
    _debate: DebateRunner = field(default_factory=DebateRunner, repr=False)
    _debate_overrides: Dict[str, float] = field(default_factory=dict, repr=False)
    _debate_in_flight: Dict[str, bool] = field(default_factory=dict, repr=False)
    _fault_overrides: Dict[str, float] = field(default_factory=dict, repr=False)
    _anomaly_first_tick: Dict[str, int] = field(default_factory=dict, repr=False)
    _anomaly_last_tick: Dict[str, int] = field(default_factory=dict, repr=False)
    _recovery_in_flight: Dict[str, bool] = field(default_factory=dict, repr=False)
    _post_recovery_grace_until: Dict[str, int] = field(default_factory=dict, repr=False)
    _recovery_history: Dict[str, List[str]] = field(default_factory=dict, repr=False)
    _last_emitted_recovery: Dict[str, tuple] = field(default_factory=dict, repr=False)
    _bg_tasks: set = field(default_factory=set, repr=False)
    # Energy tracker — accumulate pump_kWh and per-phase mean pump_kW so the
    # end-of-run summary can quote MEASURED savings from L3 recovery, not
    # marketing numbers. State machine: pre_fault → during_fault → post_recovery.
    _energy_phase: str = field(default="pre_fault", repr=False)
    _total_kwh: float = field(default=0.0, repr=False)
    _phase_kw_sum: Dict[str, float] = field(default_factory=dict, repr=False)
    _phase_kw_count: Dict[str, int] = field(default_factory=dict, repr=False)
    _dt_compliant_ticks: int = field(default=0, repr=False)
    _dt_total_samples: int = field(default=0, repr=False)
    _summary_emitted: bool = field(default=False, repr=False)

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
        self._fault_overrides.clear()
        self._anomaly_first_tick.clear()
        self._anomaly_last_tick.clear()
        self._recovery_in_flight.clear()
        self._post_recovery_grace_until.clear()
        self._recovery_history.clear()
        self._last_emitted_recovery.clear()
        self._energy_phase = "pre_fault"
        self._total_kwh = 0.0
        self._phase_kw_sum.clear()
        self._phase_kw_count.clear()
        self._dt_compliant_ticks = 0
        self._dt_total_samples = 0
        self._summary_emitted = False
        # Clear LLM-runner per-run state too — otherwise stored last_debate_at
        # from the prior run is way ahead of the new sim_t=0 and can_debate()
        # blocks forever on REPLAY.
        self._debate.reset()
        # Cancel + drop any orphan background tasks from a previous run.
        for t in list(self._bg_tasks):
            t.cancel()
        self._bg_tasks.clear()

    async def kill_leader(self, valve_id: str) -> None:
        """Simulate leader failure. Drops is_leader on the targeted agent and
        backdates all branch members' heartbeats so the next election fires
        immediately. Only valid in chillvalve mode."""
        if self._task is None or self._task.done():
            raise RuntimeError("engine not started")
        if self._mode != "chillvalve":
            raise RuntimeError("kill_leader requires chillvalve mode")
        ctrl = self._controller
        agents = getattr(ctrl, "agents", {})
        if valve_id not in agents:
            raise ValueError(f"unknown valve_id: {valve_id!r}")
        target_branch = agents[valve_id].branch_id
        agents[valve_id].is_leader = False
        agents[valve_id].is_dead = True
        agents[valve_id].last_leader_heartbeat = -1e9
        for vid, ag in agents.items():
            if vid != valve_id and ag.branch_id == target_branch:
                ag.last_leader_heartbeat = -1e9
        # Mark the branch so the next leader-change explanation knows the cause.
        self._killed_recently[target_branch] = float(self._tick)

    async def inject_fault(self, valve_id: str, severity: float) -> None:
        """Runtime fault override. Persists across ticks until cleared.
        severity=0 clears the override and reverts to scenario-driven faults."""
        if self._task is None or self._task.done():
            raise RuntimeError("engine not started")
        if self._system is None or valve_id not in self._system.valves:
            raise ValueError(f"unknown valve_id: {valve_id!r}")
        if severity <= 0:
            self._fault_overrides.pop(valve_id, None)
        else:
            self._fault_overrides[valve_id] = max(0.0, min(1.0, float(severity)))

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
            self._accumulate_energy(snapshot)
            await self._fanout(snapshot)
            await self._detect_leader_changes(snapshot)
            if self._mode == "chillvalve":
                self._track_anomalies(snapshot)
                await self._maybe_run_debate(snapshot)
                await self._maybe_run_recovery(snapshot)
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
        # Scenario ran to completion (not externally stopped). Emit the
        # end-of-run energy summary — this is the honest, measured proof of
        # what L3 recovery saved, computed from per-tick pump_kW samples.
        if not self._stop.is_set():
            await self._emit_summary()

    def _accumulate_energy(self, snapshot: Dict[str, Any]) -> None:
        """Per-tick: integrate pump_kWh and bucket pump_kW into the current
        phase. Phase transitions: pre_fault → during_fault (first anomaly
        seen) → post_recovery (first executed actuator_reset)."""
        pump_kw = snapshot.get("pump_kw", 0.0) or 0.0
        # tick_period_s is wall-clock; sim tick == 1 sim-second by convention.
        # Use 1 sim-second per tick → kWh = sum(kW) / 3600.
        self._total_kwh += pump_kw / 3600.0
        self._phase_kw_sum[self._energy_phase] = (
            self._phase_kw_sum.get(self._energy_phase, 0.0) + pump_kw
        )
        self._phase_kw_count[self._energy_phase] = (
            self._phase_kw_count.get(self._energy_phase, 0) + 1
        )
        # ΔT compliance: count valves within 0.7°C of 5°C target.
        for v in snapshot["valves"]:
            self._dt_total_samples += 1
            if abs(v["dT_C"] - 5.0) <= 0.7:
                self._dt_compliant_ticks += 1
        # Phase transitions.
        if self._energy_phase == "pre_fault":
            if any(v["anomaly_detected"] for v in snapshot["valves"]):
                self._energy_phase = "during_fault"
                log.info(
                    "energy phase → during_fault at tick=%d (pump_kw=%.2f)",
                    snapshot["tick"], pump_kw,
                )
        elif self._energy_phase == "during_fault":
            # Transition to post_recovery once an executed actuator_reset has
            # fired AND anomaly_detected has dropped back to false.
            reset_fired = any(
                "attempt_actuator_reset" in self._recovery_history.get(vid, [])
                for vid in self._recovery_history
            )
            no_active_anomaly = not any(
                v["anomaly_detected"] for v in snapshot["valves"]
            )
            if reset_fired and no_active_anomaly:
                self._energy_phase = "post_recovery"
                log.info(
                    "energy phase → post_recovery at tick=%d (pump_kw=%.2f)",
                    snapshot["tick"], pump_kw,
                )

    async def _emit_summary(self) -> None:
        if self._summary_emitted:
            return
        self._summary_emitted = True

        def _mean(phase: str) -> float:
            c = self._phase_kw_count.get(phase, 0)
            return (self._phase_kw_sum.get(phase, 0.0) / c) if c > 0 else 0.0

        mean_pre = _mean("pre_fault")
        mean_during = _mean("during_fault")
        mean_post = _mean("post_recovery")
        recovery_fired = "post_recovery" in self._phase_kw_count
        # Savings interpretation: the during_fault phase shows what the pump
        # had to draw while B2 was choking the branch (peers compensating at
        # high positions → more head needed → more pump kW). post_recovery
        # shows the pump after L3 cleared the fault. Delta × remaining
        # scenario duration ≈ kWh that would have been wasted without L3.
        recovery_savings_kw = (
            max(0.0, mean_during - mean_post) if recovery_fired else 0.0
        )
        # Project the savings over the typical remaining duration past
        # recovery (assume a real-world fault would have persisted to scenario
        # end without intervention).
        post_count = self._phase_kw_count.get("post_recovery", 0)
        recovery_savings_kwh = recovery_savings_kw * (post_count / 3600.0)
        dt_compliance_pct = (
            100.0 * self._dt_compliant_ticks / self._dt_total_samples
            if self._dt_total_samples > 0
            else 0.0
        )
        scenario_name = self._scenario.name if self._scenario else "(unknown)"
        msg = {
            "type": "summary",
            "scenario": scenario_name,
            "duration_s": int(self._tick),
            "total_kwh": round(self._total_kwh, 4),
            "mean_kw_pre_fault": round(mean_pre, 3),
            "mean_kw_during_fault": round(mean_during, 3),
            "mean_kw_post_recovery": round(mean_post, 3),
            "recovery_fired": recovery_fired,
            "recovery_savings_kw": round(recovery_savings_kw, 3),
            "recovery_savings_kwh": round(recovery_savings_kwh, 4),
            "dt_compliance_pct": round(dt_compliance_pct, 1),
        }
        log.info("scenario summary: %s", msg)
        for q in self._subscribers:
            try:
                q.put_nowait(msg)
            except asyncio.QueueFull:
                pass

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
            sev = self._fault_overrides.get(
                rec.valve_id, self._scenario.fault_severity(rec.valve_id, t)
            )
            self._system.set_fault_severity(rec.valve_id, sev)
        states = self._system.tick(t)
        if self._mode == "belimo":
            commands = self._controller.step(states)  # type: ignore[union-attr]
        else:
            # Atomic swap: take the current overrides and replace with empty
            # dict in one bytecode step. Without this, the event-loop-side
            # _run_and_apply_debate can write between `dict(...)` and `clear()`
            # and lose an allocation. The single attribute assignment is GIL-atomic.
            overrides = self._debate_overrides
            self._debate_overrides = {}
            commands = self._controller.step(
                states, t_seconds=float(t), debate_overrides=overrides,
            )  # type: ignore[union-attr]
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

    async def _maybe_run_debate(self, snapshot: Dict[str, Any]) -> None:
        """Per-branch: if Layer 2 confidence is in the uncertain band and the
        branch isn't already debating and cooldown has elapsed, spawn a
        debate task. Result lands in self._debate_overrides for the next
        controller.step to consume."""
        if self._scenario is not None and self._scenario.disable_debate:
            return
        branches: Dict[str, List[Dict[str, Any]]] = {}
        for v in snapshot["valves"]:
            branches.setdefault(v["branch_id"], []).append(v)
        for branch_id, valves in branches.items():
            if self._debate_in_flight.get(branch_id):
                continue
            if not is_uncertain_branch(valves):
                continue
            if not self._debate.can_debate(branch_id, float(snapshot["tick"])):
                continue
            leader = next((v["valve_id"] for v in valves if v["is_leader"]), None)
            if leader is None:
                continue
            self._debate_in_flight[branch_id] = True
            task = asyncio.create_task(
                self._run_and_apply_debate(branch_id, leader, valves, snapshot["tick"])
            )
            self._bg_tasks.add(task)
            task.add_done_callback(self._bg_tasks.discard)

    async def _run_and_apply_debate(
        self, branch_id: str, leader_id: str,
        valves: List[Dict[str, Any]], tick: int,
    ) -> None:
        try:
            round_ = await self._debate.run(branch_id, leader_id, valves, float(tick))
            if round_ is None:
                return
            # Stage allocations so the next tick's controller.step picks them up.
            for vid, pos in round_.allocations.items():
                self._debate_overrides[vid] = pos
            # Fan out the debate transcript so the dashboard can render it.
            msg = {
                "type": "debate",
                "branch_id": round_.branch_id,
                "tick": round_.tick,
                "leader_id": leader_id,
                "speeches": round_.speeches,
                "allocations": round_.allocations,
                "rationale": round_.rationale,
                "cached": round_.cached,
                "wall_clock_s": round(round_.wall_clock_s, 2),
            }
            for q in self._subscribers:
                try:
                    q.put_nowait(msg)
                except asyncio.QueueFull:
                    pass
        finally:
            self._debate_in_flight[branch_id] = False

    def _track_anomalies(self, snapshot: Dict[str, Any]) -> None:
        """Maintain per-valve 'first tick anomaly went true' + 'last tick
        anomaly was true', tolerating short flickers. Pops only after the
        anomaly has been absent for ANOMALY_FLICKER_GRACE_S sim-seconds.
        Also honors a post-recovery grace window so we don't re-track a
        valve that was just remediated."""
        t = snapshot["tick"]
        ANOMALY_FLICKER_GRACE_S = 5
        for v in snapshot["valves"]:
            vid = v["valve_id"]
            grace = self._post_recovery_grace_until.get(vid)
            if grace is not None and t < grace:
                # Skip tracking entirely while the hydraulic state catches up
                # after a recovery action.
                continue
            if v["anomaly_detected"]:
                self._anomaly_first_tick.setdefault(vid, t)
                self._anomaly_last_tick[vid] = t
            else:
                last_seen = self._anomaly_last_tick.get(vid)
                if last_seen is None or (t - last_seen) > ANOMALY_FLICKER_GRACE_S:
                    self._anomaly_first_tick.pop(vid, None)
                    self._anomaly_last_tick.pop(vid, None)

    async def _maybe_run_recovery(self, snapshot: Dict[str, Any]) -> None:
        """Per-valve: if anomaly has persisted past the threshold and no
        recovery is in flight, spawn a recovery-debate task. LLM picks
        the corrective action; we execute it on the next tick."""
        if self._scenario is not None and self._scenario.disable_debate:
            return
        tick = snapshot["tick"]
        # Group valves by branch so we can pass the right peer list.
        branches: Dict[str, List[Dict[str, Any]]] = {}
        for v in snapshot["valves"]:
            branches.setdefault(v["branch_id"], []).append(v)
        for vid, first_tick in list(self._anomaly_first_tick.items()):
            age_s = float(tick - first_tick)
            if age_s < RECOVERY_ANOMALY_PERSISTENCE_S:
                continue
            if self._recovery_in_flight.get(vid):
                continue
            if not self._debate.can_recover(vid, float(tick)):
                continue
            # Find the valve's branch + leader.
            target = next(
                (v for v in snapshot["valves"] if v["valve_id"] == vid), None
            )
            if target is None:
                continue
            branch_id = target["branch_id"]
            branch_valves = branches.get(branch_id, [])
            leader_id = next(
                (v["valve_id"] for v in branch_valves if v["is_leader"]), None
            )
            if leader_id is None:
                continue
            self._recovery_in_flight[vid] = True
            task = asyncio.create_task(
                self._run_and_apply_recovery(
                    branch_id, vid, leader_id, branch_valves, tick, age_s
                )
            )
            self._bg_tasks.add(task)
            task.add_done_callback(self._bg_tasks.discard)

    async def _run_and_apply_recovery(
        self,
        branch_id: str,
        target_valve_id: str,
        leader_id: str,
        valves: List[Dict[str, Any]],
        tick: int,
        anomaly_age_s: float,
    ) -> None:
        """Run a recovery debate, then execute the LLM's chosen action.
        If the LLM dithers (picks schedule_maintenance / accept_degradation
        twice in a row WITHOUT ever attempting a reset), auto-promote the
        next decision to attempt_actuator_reset so flow actually restores."""
        try:
            history = list(self._recovery_history.get(target_valve_id, []))
            decision = await self._debate.run_recovery_debate(
                branch_id, target_valve_id, leader_id, valves,
                float(tick), anomaly_age_s, recent_actions=history,
            )
            if decision is None:
                return
            # Escalation: if LLM keeps refusing to attempt reset, force one.
            never_reset = "attempt_actuator_reset" not in history
            non_reset_picks = sum(
                1 for a in history if a != "attempt_actuator_reset"
            )
            promoted = False
            if (
                never_reset
                and non_reset_picks >= 1
                and decision.action != "attempt_actuator_reset"
            ):
                decision = RecoveryDecision(
                    branch_id=decision.branch_id,
                    target_valve_id=decision.target_valve_id,
                    leader_id=decision.leader_id,
                    tick=decision.tick,
                    action="attempt_actuator_reset",
                    rationale=(
                        f"AUTO-PROMOTED to reset after "
                        f"{non_reset_picks} non-reset pick(s) without ever "
                        f"attempting one (was: {decision.action}). Original "
                        f"reason: {decision.rationale}"
                    ),
                    wall_clock_s=decision.wall_clock_s,
                )
                promoted = True
            # Record into history AFTER promotion so escalation logic uses what
            # actually got executed.
            self._recovery_history.setdefault(target_valve_id, []).append(
                decision.action
            )
            executed_text = decision.rationale
            executed = False
            if decision.action == "attempt_actuator_reset":
                # The LLM has decided to attempt a soft actuator reset.
                # In the sim this translates to clearing the runtime fault
                # override (flow_multiplier returns to 1.0 because the
                # scenario's own fault_severity is what _tick_once falls
                # back to via dict.get default). On a real valve this would
                # issue an actuator power-cycle command.
                # Use pop() to match the contract used by inject_fault — that
                # way a later inject_fault(vid, 0) call has the same effect.
                # NOTE: this only "heals" B2 in the demo because the scenario's
                # own fault_severity is now treated as the ground truth; for
                # the current demo scenario the engine intentionally re-emits
                # zero severity post-pop because scenario.fault_severity stays
                # at fault_max_severity. So we ALSO override to 0.0 explicitly
                # via a separate "engine cleared" marker.
                self._fault_overrides[target_valve_id] = 0.0
                self._anomaly_first_tick.pop(target_valve_id, None)
                self._anomaly_last_tick.pop(target_valve_id, None)
                # Block _track_anomalies from re-recording for ~5s while the
                # hydraulic state catches up; otherwise the next tick re-flags
                # the valve as anomalous and pollutes the L2 panel.
                self._post_recovery_grace_until[target_valve_id] = tick + 5
                executed = True
                executed_text = f"actuator soft-reset issued; {executed_text}"
            elif decision.action == "schedule_maintenance":
                executed_text = f"maintenance work-order filed; {executed_text}"
            elif decision.action == "accept_degradation":
                executed_text = f"degradation accepted; {executed_text}"
            # Dedup: skip emitting if the same (valve, action) already went
            # out within the last 10 sim-seconds. Always emit on action change
            # (the user needs to see escalation) and always emit on executed
            # actions (those change physical state).
            last = self._last_emitted_recovery.get(target_valve_id)
            same_action_recent = (
                last is not None
                and last[0] == decision.action
                and (tick - last[1]) < 10
            )
            if same_action_recent and not executed and not promoted:
                return
            self._last_emitted_recovery[target_valve_id] = (decision.action, tick)
            msg = {
                "type": "remediation",
                "branch_id": branch_id,
                "target_valve_id": target_valve_id,
                "leader_id": leader_id,
                "tick": decision.tick,
                "action": decision.action,
                "rationale": decision.rationale,
                "executed": executed,
                "text": executed_text,
                "wall_clock_s": round(decision.wall_clock_s, 2),
            }
            for q in self._subscribers:
                try:
                    q.put_nowait(msg)
                except asyncio.QueueFull:
                    pass
        finally:
            self._recovery_in_flight[target_valve_id] = False

    async def _detect_leader_changes(self, snapshot: Dict[str, Any]) -> None:
        """Compare current leader per branch against last snapshot; spawn an
        async explanation task on transitions. Non-blocking."""
        current: Dict[str, Optional[str]] = {}
        for v in snapshot["valves"]:
            branch = v["branch_id"]
            if v["is_leader"]:
                current[branch] = v["valve_id"]
            current.setdefault(branch, None)
        for branch, new_leader in current.items():
            prev = self._last_leaders.get(branch)
            if new_leader != prev and new_leader is not None:
                cause = "killed" if branch in self._killed_recently else (
                    "boot" if prev is None else "election"
                )
                self._killed_recently.pop(branch, None)
                task = asyncio.create_task(
                    self._explain_and_fanout(branch, prev, new_leader, cause, snapshot["tick"])
                )
                self._bg_tasks.add(task)
                task.add_done_callback(self._bg_tasks.discard)
            # Only update when a leader exists; leaderless interim preserves the
            # previous leader so the next election's explanation has the right
            # "previous_leader" attribution.
            if new_leader is not None:
                self._last_leaders[branch] = new_leader

    async def _explain_and_fanout(
        self, branch_id: str, prev: Optional[str], new_leader: str, cause: str, tick: int
    ) -> None:
        text = await self._explainer.explain_leader_change(
            branch_id, prev, new_leader, cause, float(tick)
        )
        msg = {
            "type": "explanation",
            "kind": "leader",
            "branch_id": branch_id,
            "previous_leader": prev,
            "new_leader": new_leader,
            "cause": cause,
            "tick": tick,
            "text": text,
        }
        for q in self._subscribers:
            try:
                q.put_nowait(msg)
            except asyncio.QueueFull:
                pass

    async def _fanout(self, snapshot: Dict[str, Any]) -> None:
        for q in self._subscribers:
            try:
                q.put_nowait(snapshot)
            except asyncio.QueueFull:
                # Slow consumer — drop this snapshot for them.
                pass
