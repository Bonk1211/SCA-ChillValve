# Plan: Three-Layer Intelligence + ChillValve Controller + Multi-Agent Coordination

## Summary
Implement the three intelligence layers from PRD §5 — Layer 1 deterministic rules, Layer 2 ML anomaly detection placeholder, Layer 3 distributed multi-agent coordination via in-process pub/sub broker with bully leader election — and wire them into `ChillValveController` (PRD §6). Extend `sim/engine.py` to support `--mode chillvalve` and `--mode compare`. End-to-end: `python -m sim.engine --mode compare` runs both controllers against the same scenario and reports the relative pump-energy delta.

## User Story
As the software lead, I want both controllers running side-by-side under identical scenarios with all three layers observable, so that Phase 5 (FastAPI dashboard) has live data to stream and the demo's "13 % savings" claim is measured rather than asserted.

## Problem → Solution
**Current state:** After Phase 2, only the Belimo baseline exists. Layer 1/2/3 modules are 1-line docstring stubs. `ChillValveController` is a stub. No leader election, no inter-valve messaging, no overrides.
**Desired state:**
- `Layer1Rules.evaluate(state)` returns a `RuleAction` or `None` for all 5 PRD rules.
- `Layer2ML.evaluate(state)` returns a benign `AnomalyResult` (placeholder; Phase 4 replaces with a real Isolation Forest).
- `MessageBroker` provides sync `broadcast(channel, sender, payload)` / `collect(channel, since)` semantics; trims to 60 s history.
- `ValveAgent` runs the per-tick loop from PRD §5.3, including bully election with 3-second window.
- `ChillValveController` orchestrates Layer 1 (override) → Layer 2 (informational) → Layer 3 (setpoint) → Layer 1 (final validate) per PRD §6.
- `engine.py --mode chillvalve` runs the new controller; `--mode compare` runs both modes back-to-back on identical scenario and prints the delta.
- Tests cover each rule individually, the broker's pub/sub, election convergence, leader logic, and an end-to-end ChillValve-vs-Belimo energy comparison.

## Metadata
- **Complexity**: Large
- **Source PRD**: `docs/ChillValve_Implementation_PRD_v1.md`
- **PRD Phase**: Phase 3 — Three Layers (PRD §10 steps 8–13)
- **Estimated Files**: ~15 (5 source files modified/created, 5 test files, README update, engine extensions)

---

## UX Design

### Before
```
$ uv run python -m sim.engine --scenario steady_state --mode belimo
[engine] total_pump_energy = 3.76 kWh; mean_dT = 5.05 C
```
Only Belimo mode. Layers 1–3 inactive.

### After
```
$ uv run python -m sim.engine --scenario steady_state --mode chillvalve
[engine] mode=chillvalve, tick=1s, total_ticks=3600
[layer3] tick 0    branch A leader=A1   branch B leader=B1
[layer1] tick 117  A2 rule 'flow_exceeds_max_110pct' fired → reduce_position
[summary] total_pump_energy = 3.22 kWh   mean_dT = 4.98 C
[summary] layer1_fires = 4   leader_elections = 2   coord_messages = 432

$ uv run python -m sim.engine --scenario steady_state --mode compare
[compare] belimo:     pump_kwh = 3.76   mean_dT = 5.05
[compare] chillvalve: pump_kwh = 3.22   mean_dT = 4.98
[compare] delta:      -0.54 kWh   (-14.4 %)
```

### Interaction Changes
| Touchpoint | Before | After | Notes |
|---|---|---|---|
| `--mode` | belimo only | belimo, chillvalve, compare | `compare` runs both back-to-back |
| Layer indicators | none | logged per-fire | dashboard (Phase 6) will visualize |
| Leader badge | none | tracked in `ValveState.is_leader` | already a `ValveState` field from Phase 1 |
| Output JSONL | per-tick valve metrics | + per-tick `rule_fired`, `anomaly_detected`, `is_leader` | downstream Phase 5 can ingest |

---

## Mandatory Reading

| Priority | File | Lines | Why |
|---|---|---|---|
| P0 | `docs/ChillValve_Implementation_PRD_v1.md` | 231–298 | §5.1 Layer 1 — all 5 rules with exact triggers and actions |
| P0 | `docs/ChillValve_Implementation_PRD_v1.md` | 296–425 | §5.2 Layer 2 — interface; Phase 3 only implements the surface |
| P0 | `docs/ChillValve_Implementation_PRD_v1.md` | 427–574 | §5.3 Layer 3 — ValveAgent loop, leader election, leader logic |
| P0 | `docs/ChillValve_Implementation_PRD_v1.md` | 620–693 | §6 Belimo vs ChillValve controllers — exact orchestration order |
| P0 | `docs/ChillValve_Implementation_PRD_v1.md` | 715–745 | §7.2 MessageBroker spec — we implement a sync version now |
| P0 | `sim/types.py` | all | `ValveState`, `RuleAction`, `AnomalyResult`, `ValveCommand` — already defined in Phase 1 |
| P0 | `sim/engine.py` | all | Phase 2 loop we extend |
| P0 | `sim/controllers/belimo_baseline.py` | all | Mirror its structure for ChillValve |
| P1 | `docs/ChillValve_Implementation_PRD_v1.md` | 1025–1096 | §11 algorithm pseudocode — orchestration order reference |
| P1 | `.claude/PRPs/reports/simulation-core-and-belimo-baseline-report.md` | all | Phase 2 deviations & validation band — Phase 3 inherits them |

## External Documentation

| Topic | Source | Key Takeaway |
|---|---|---|
| Bully election algorithm | Garcia-Molina (1982) | Each node broadcasts candidacy with its id; after a quiet window, lowest (or highest, per convention) id wins. PRD §5.3 line 568 uses **lowest** id. |
| In-process pub/sub vs async | Python stdlib | For sync engine, `defaultdict(list)` channels with monotonic-timestamp dedup is sufficient. Async wrapping is Phase 5. |
| `time.monotonic()` vs `time.time()` | Python stdlib | Use `time.monotonic()` for relative comparisons (heartbeats, election windows). `time.time()` for human-readable timestamps. |

---

## Patterns to Mirror

### NAMING_CONVENTION
// SOURCE: `sim/controllers/belimo_baseline.py` (Phase 2)
```python
# Controller pattern: dataclass with config defaults, single `step(states) -> Dict[str, ValveCommand]`
# Layer pattern: class with `evaluate(state) -> Optional[Action]`
# Broker pattern: module-level singleton OR explicitly-injected instance
```

### ERROR_HANDLING
// SOURCE: `sim/valve.py`, `sim/pump.py` (Phase 1+2)
```python
# ValueError on out-of-domain input. No try/except, no silent fallbacks.
# Layer 1's `use_last_known_good` is the ONE place where we substitute — and only after a sensor invalidity check.
```

### TEST_STRUCTURE
// SOURCE: `tests/test_belimo.py` (Phase 2)
```python
# Use _state(valve_id, dT, pos, ...) helper for ValveState construction
# Parametrize the table-of-cases
# One assertion per behavior
```

### CONTROLLER_ORCHESTRATION
// SOURCE: PRD §6 lines 660–683 (verbatim spec)
```python
# 1. Layer 1.evaluate; if CRITICAL action → return command with override=True (skip 2,3)
# 2. Layer 2.evaluate; write anomaly_detected / confidence onto state (informational)
# 3. Layer 3.get_current_setpoint; if available → use; else fallback to local PID
# 4. Layer 1.validate_command(final_position); clamp / sanity check
# 5. Return ValveCommand(position_pct, override=False)
```

### BROKER_API
// SOURCE: PRD §7.2 lines 719–744 (sync adaptation)
```python
class MessageBroker:
    def broadcast(self, channel: str, sender_id: str, payload: dict, t_now: float) -> None
    def collect(self, channel: str, since: float, t_now: float) -> List[Message]
    # Auto-trim messages older than 60 s on each broadcast
```

### LEADER_ELECTION
// SOURCE: PRD §5.3 lines 480–509 (Bully algorithm — synchronous adaptation)
```python
# 1. On heartbeat timeout: broadcast election message with candidate=my_id
# 2. Wait `election_window_s` (3.0 s simulated time, NOT wall time)
# 3. Collect all election messages received since election start
# 4. New leader = min(candidate_ids)
# 5. If I'm the leader, start sending heartbeats
```
*Note:* PRD §5.3 uses `await asyncio.sleep(3.0)`. In our sync engine, we run the election over multiple ticks instead — election "completes" after 3 simulated seconds of accumulated election messages.

---

## Files to Change

| File | Action | Justification |
|---|---|---|
| `sim/layers/layer1_rules.py` | REWRITE (was stub) | All 5 rules per PRD §5.1, plus `validate_command(commanded_position, state)` helper |
| `sim/layers/layer2_ml.py` | REWRITE (was stub) | Placeholder returning benign `AnomalyResult`; signature matches Phase 4's eventual ML implementation |
| `sim/layers/layer3_agent.py` | REWRITE (was stub) | `ValveAgent` per-tick loop, election state machine, leader logic |
| `sim/broker.py` | CREATE | `MessageBroker` sync pub/sub — moves to `backend/` in Phase 5 |
| `sim/controllers/chillvalve.py` | REWRITE (was stub) | `ChillValveController.step(states) -> Dict[str, ValveCommand]`; instantiates broker + agents internally; orchestrates all 3 layers per PRD §6 |
| `sim/engine.py` | UPDATE | Add `chillvalve` and `compare` to `--mode`; record per-tick layer activity in JSONL; print delta in compare mode |
| `sim/system.py` | UPDATE | Populate `rule_fired`, `safety_override_active`, `anomaly_detected`, `anomaly_confidence`, `is_leader`, `last_election_time` fields on `ValveState` (currently hard-coded to defaults) — accept these from the controller |
| `tests/test_layer1_rules.py` | CREATE | One test per rule fire; one for happy-path (no fire); validate_command bounds |
| `tests/test_layer2_ml.py` | CREATE | Placeholder returns benign result; signature stable |
| `tests/test_broker.py` | CREATE | broadcast→collect round-trip; channel isolation; 60-s trim; ordering |
| `tests/test_layer3_agent.py` | CREATE | Election convergence (lowest id wins); heartbeat keepalive; non-leader fallback |
| `tests/test_chillvalve_controller.py` | CREATE | Layer 1 override beats Layer 3 setpoint; in absence of setpoint, local PID; rule fires propagate to ValveCommand |
| `tests/test_engine.py` | UPDATE | Add `test_chillvalve_full_scenario_produces_realistic_energy` and `test_compare_mode_reports_delta` |
| `scripts/validate_chillvalve_vs_belimo.py` | CREATE | E2E sanity: runs compare, asserts ChillValve energy ≤ Belimo energy + tolerance |
| `README.md` | UPDATE | Add ChillValve + Compare mode usage; status line → Phase 3 complete |

## NOT Building

- **Real ML model** — Layer 2 ships as a placeholder; Phase 4 trains the Isolation Forest
- **Async / FastAPI integration** — broker is sync; Phase 5 wraps it in `asyncio`
- **MQTT or BACnet broker** — in-process only (PRD §7.2 explicitly accepts in-process for prototype)
- **Fault injection scenario (C)** — Phase 4 (depends on real ML)
- **Load spike scenario (B)** — Phase 4 or 7 polish
- **Operator approval / advisory mode** (PRD Q8) — autonomous mode only for prototype
- **Persistent leader state across restarts** — election runs from scratch on engine start
- **Heartbeat over an actual network** — heartbeats are message broker entries, leader emits one per Layer 3 cycle

---

## Step-by-Step Tasks

### Task 1: Implement `sim/layers/layer1_rules.py`
- **ACTION**: All 5 rules per PRD §5.1 plus a `validate_command` helper used by the ChillValve controller's final stage.
- **IMPLEMENT**:
  ```python
  """Layer 1 — deterministic rules. PRD §5.1.

  Fires every tick. Microsecond response. Never overridden by Layer 2 or 3.
  """
  from __future__ import annotations
  import math
  from dataclasses import dataclass, field
  from typing import Dict, Optional, Tuple

  from sim.types import RuleAction, ValveState

  CRITICAL_ACTIONS = frozenset({"emergency_close", "use_last_known_good", "raise_fault"})

  # Tunable thresholds (PRD §5.1)
  FLOW_CEILING_MULTIPLIER = 1.10
  DP_FAILSAFE_KPA = 600.0
  ACTUATOR_TIMEOUT_S = 30.0
  ACTUATOR_TOLERANCE = 0.05


  def _isnan_or_outlier(v: float) -> bool:
      return v is None or (isinstance(v, float) and (math.isnan(v) or math.isinf(v)))


  @dataclass
  class Layer1Rules:
      """Deterministic rules. Always active. Cannot be overridden."""

      flow_max_gpm_per_valve: Dict[str, float] = field(default_factory=dict)
      last_known_good: Dict[str, Tuple[float, float, float]] = field(default_factory=dict)
      commanded_position_timestamps: Dict[str, Tuple[float, float]] = field(default_factory=dict)
      # valve_id -> (commanded_position, t_commanded_seconds)

      def evaluate(self, state: ValveState, t_seconds: float) -> Optional[RuleAction]:
          vid = state.valve_id

          # Rule 1: Clamp position to physical limits.
          # (Position is always clamped at the system boundary by HydraulicSystem.set_positions,
          # so this rule is informational — it fires if a controller emits an out-of-bound
          # command. We check the *current* position_pct.)
          if not 0.0 <= state.position_pct <= 100.0:
              return RuleAction(
                  action="clamp_position",
                  value=max(0.0, min(100.0, state.position_pct)),
                  reason="position_out_of_bounds",
              )

          # Rule 2: Flow ceiling — flow > 110% of valve's per-valve flow max.
          flow_max = self.flow_max_gpm_per_valve.get(vid)
          if flow_max is not None and state.flow_gpm > flow_max * FLOW_CEILING_MULTIPLIER:
              return RuleAction(
                  action="reduce_position",
                  value=state.position_pct * 0.9,
                  reason="flow_exceeds_max_110pct",
              )

          # Rule 3: Pressure failsafe (water-hammer protection).
          if state.dP_kPa > DP_FAILSAFE_KPA:
              return RuleAction(
                  action="emergency_close",
                  value=0.0,
                  reason="dP_exceeds_600kPa",
              )

          # Rule 4: Sensor validity.
          if any(_isnan_or_outlier(v) for v in [state.flow_gpm, state.dT_C, state.dP_kPa]):
              last = self.last_known_good.get(vid)
              return RuleAction(
                  action="use_last_known_good",
                  value=last[0] if last else None,
                  reason="sensor_invalid",
              )

          # Rule 5: Actuator timeout — commanded vs actual position diverged >0.05 for >30s.
          ts = self.commanded_position_timestamps.get(vid)
          if ts is not None:
              commanded, t_commanded = ts
              if (t_seconds - t_commanded) > ACTUATOR_TIMEOUT_S and \
                  abs(state.position_pct / 100.0 - commanded) > ACTUATOR_TOLERANCE:
                  return RuleAction(
                      action="raise_fault",
                      value=None,
                      reason="actuator_unresponsive",
                  )

          # No rule fired — record last known good.
          self.last_known_good[vid] = (state.flow_gpm, state.dT_C, state.dP_kPa)
          return None

      def validate_command(self, commanded_position_pct: float, state: ValveState) -> float:
          """Final sanity check on a position command from Layer 3 / local PID.

          Clamps to [0, 100]; if Rule 3 (dP failsafe) is currently active, forces to 0.
          """
          if state.dP_kPa > DP_FAILSAFE_KPA:
              return 0.0
          return max(0.0, min(100.0, commanded_position_pct))

      def record_command(self, valve_id: str, commanded_position_unit: float, t_seconds: float) -> None:
          """Called by the controller whenever it emits a new position command."""
          self.commanded_position_timestamps[valve_id] = (commanded_position_unit, t_seconds)
  ```
- **MIRROR**: NAMING_CONVENTION, ERROR_HANDLING, dataclass pattern from Phase 2.
- **IMPORTS**: stdlib only; `sim.types`.
- **GOTCHA**:
  - PRD §5.1 uses `valve.commanded_position_age_s`; our `ValveState` doesn't have that field, so we maintain command timestamps inside the `Layer1Rules` instance — same effect.
  - Rule 1 in PRD operates on unit-interval position; our `ValveState.position_pct` is 0–100, so the check is `0..100` here. Conversion documented inline.
  - `flow_max_gpm_per_valve` is populated by the `ChillValveController` at construction time from the system's valve specs (DN65 design_flow=50, DN100=150). Rule 2 is therefore inactive if the controller forgets to populate it (graceful — log nothing).
- **VALIDATE**: `tests/test_layer1_rules.py` — one test per rule, plus happy path returns None.

### Task 2: Implement `sim/layers/layer2_ml.py` (placeholder)
- **ACTION**: Surface-stable placeholder; Phase 4 swaps internals.
- **IMPLEMENT**:
  ```python
  """Layer 2 — ML anomaly detection. PRD §5.2.

  Phase 3 placeholder: always returns a benign result. Phase 4 will load
  data/models/isolation_forest.pkl and feature_scaler.pkl and compute the
  real score.
  """
  from __future__ import annotations
  from dataclasses import dataclass
  from datetime import datetime

  from sim.types import AnomalyResult, ValveState


  @dataclass
  class Layer2ML:
      """Anomaly detector. Placeholder in Phase 3."""

      def evaluate(self, state: ValveState) -> AnomalyResult:
          return AnomalyResult(
              anomaly_detected=False,
              confidence=0.0,
              raw_score=0.0,
              features=[],
              timestamp=state.timestamp or datetime.utcnow(),
          )
  ```
- **MIRROR**: dataclass pattern; surface signature exactly matches PRD §5.2 lines 380–419 so Phase 4 only fills the body.
- **GOTCHA**: Don't add the trained-model loader signature now — Phase 4 will refactor the constructor when it adds `model_path` / `scaler_path`. Keeping the surface minimal here avoids churn.
- **VALIDATE**: `tests/test_layer2_ml.py` — placeholder returns `anomaly_detected=False, confidence=0.0`.

### Task 3: Implement `sim/broker.py`
- **ACTION**: Synchronous in-process pub/sub broker.
- **IMPLEMENT**:
  ```python
  """In-process message broker. PRD §7.2 (sync adaptation for Phase 3).

  Phase 5 will wrap this in asyncio when FastAPI lands.
  """
  from __future__ import annotations
  from collections import defaultdict
  from dataclasses import dataclass, field
  from typing import Any, Dict, List

  MESSAGE_RETENTION_S = 60.0


  @dataclass
  class Message:
      channel: str
      sender_id: str
      payload: Dict[str, Any]
      timestamp: float   # simulated seconds (monotonic in scenario time)


  @dataclass
  class MessageBroker:
      channels: Dict[str, List[Message]] = field(default_factory=lambda: defaultdict(list))

      def broadcast(self, channel: str, sender_id: str, payload: Dict[str, Any], t_now: float) -> None:
          self.channels[channel].append(Message(channel, sender_id, payload, t_now))
          # Trim to last 60 s.
          cutoff = t_now - MESSAGE_RETENTION_S
          self.channels[channel] = [m for m in self.channels[channel] if m.timestamp >= cutoff]

      def collect(self, channel: str, since: float, t_now: float) -> List[Message]:
          return [m for m in self.channels.get(channel, []) if m.timestamp > since and m.timestamp <= t_now]
  ```
- **MIRROR**: dataclass pattern; module-level constant `MESSAGE_RETENTION_S`.
- **GOTCHA**:
  - Timestamps are **simulated seconds** (passed in by the engine), not wall time. This keeps election windows deterministic regardless of wall-clock speed.
  - Cutoff is strict (`>= cutoff`) to avoid floating-point edge cases at exactly 60 s.
- **VALIDATE**: `tests/test_broker.py` — broadcast then collect; different channels isolated; 60-s trim drops old messages.

### Task 4: Implement `sim/layers/layer3_agent.py`
- **ACTION**: `ValveAgent` per-tick loop with election state machine + leader logic.
- **IMPLEMENT**:
  ```python
  """Layer 3 — distributed multi-agent coordination. PRD §5.3.

  Each valve runs one ValveAgent. Agents communicate via MessageBroker.
  Synchronous adaptation: election runs over multiple ticks instead of asyncio.sleep.
  """
  from __future__ import annotations
  from dataclasses import dataclass, field
  from typing import Any, Dict, List, Optional

  from sim.broker import MessageBroker
  from sim.types import ValveState

  HEARTBEAT_TIMEOUT_S = 15.0      # PRD §5.3 line 477
  ELECTION_WINDOW_S = 3.0         # PRD §5.3 line 493
  COORDINATION_CADENCE_S = 5.0    # PRD §5.3 line 432


  def _branch_member_ids(branch_id: str, all_ids: List[str]) -> List[str]:
      return [vid for vid in all_ids if vid.startswith(branch_id)]


  @dataclass
  class ElectionState:
      in_progress: bool = False
      started_at: float = 0.0
      my_candidate_seen: bool = False


  @dataclass
  class ValveAgent:
      """Distributed agent. One per valve. Synchronous tick-driven."""

      valve_id: str
      branch_id: str
      broker: MessageBroker
      peer_states: Dict[str, Dict[str, Any]] = field(default_factory=dict)
      is_leader: bool = False
      last_leader_heartbeat: float = 0.0
      last_collected_at: float = 0.0
      last_setpoint_broadcast_at: float = -1e9
      latest_setpoint: Optional[float] = None
      election: ElectionState = field(default_factory=ElectionState)

      # --- Channels ---
      def _state_channel(self) -> str:
          return f"branch/{self.branch_id}/state"

      def _election_channel(self) -> str:
          return f"branch/{self.branch_id}/election"

      def _setpoint_channel(self) -> str:
          return f"branch/{self.branch_id}/setpoints"

      # --- Per-tick loop ---
      def tick(self, my_state: ValveState, all_valve_ids: List[str], t_seconds: float) -> None:
          # 1. Broadcast my state to peers in the branch.
          self.broker.broadcast(
              self._state_channel(), self.valve_id,
              {"flow_gpm": my_state.flow_gpm,
               "dT_C": my_state.dT_C,
               "position_pct": my_state.position_pct,
               "capacity_demand_kW": my_state.capacity_demand_kW,
               "capacity_delivered_kW": my_state.capacity_delivered_kW,
               "anomaly_detected": my_state.anomaly_detected},
              t_seconds,
          )

          # 2. Collect peer states.
          for msg in self.broker.collect(self._state_channel(), self.last_collected_at, t_seconds):
              if msg.sender_id != self.valve_id:
                  self.peer_states[msg.sender_id] = msg.payload

          # 3. Collect setpoint broadcasts from leader.
          for msg in self.broker.collect(self._setpoint_channel(), self.last_collected_at, t_seconds):
              if msg.payload.get("leader_alive"):
                  self.last_leader_heartbeat = t_seconds
              if not self.is_leader:
                  vp = msg.payload.get("valve_setpoints", {}).get(self.valve_id)
                  if vp is not None:
                      self.latest_setpoint = vp

          # 4. Election bookkeeping.
          self._election_tick(all_valve_ids, t_seconds)

          # 5. Leader logic (broadcasts setpoints + heartbeat).
          if self.is_leader and (t_seconds - self.last_setpoint_broadcast_at) >= COORDINATION_CADENCE_S:
              self._leader_broadcast(all_valve_ids, t_seconds)

          self.last_collected_at = t_seconds

      def _election_tick(self, all_valve_ids: List[str], t_seconds: float) -> None:
          # If we're a non-leader and the leader is stale → trigger election.
          if (not self.is_leader) and not self.election.in_progress and \
              (t_seconds - self.last_leader_heartbeat) > HEARTBEAT_TIMEOUT_S:
              self._start_election(t_seconds)

          # If we're mid-election, check if the window has elapsed.
          if self.election.in_progress and (t_seconds - self.election.started_at) >= ELECTION_WINDOW_S:
              self._resolve_election(all_valve_ids, t_seconds)

      def _start_election(self, t_seconds: float) -> None:
          self.election.in_progress = True
          self.election.started_at = t_seconds
          self.broker.broadcast(
              self._election_channel(), self.valve_id,
              {"candidate_id": self.valve_id}, t_seconds,
          )

      def _resolve_election(self, all_valve_ids: List[str], t_seconds: float) -> None:
          candidates = {self.valve_id}
          for msg in self.broker.collect(
              self._election_channel(), self.election.started_at - 1e-9, t_seconds,
          ):
              cid = msg.payload.get("candidate_id")
              if cid in _branch_member_ids(self.branch_id, all_valve_ids):
                  candidates.add(cid)
          new_leader = min(candidates)
          self.is_leader = (new_leader == self.valve_id)
          self.election.in_progress = False
          self.last_leader_heartbeat = t_seconds
          if self.is_leader:
              # Force immediate setpoint broadcast on first leadership.
              self.last_setpoint_broadcast_at = -1e9

      def _leader_broadcast(self, all_valve_ids: List[str], t_seconds: float) -> None:
          # Aggregate branch demand.
          branch_ids = _branch_member_ids(self.branch_id, all_valve_ids)
          peer_vals = [self.peer_states.get(vid, {}) for vid in branch_ids if vid != self.valve_id]
          peer_vals = [v for v in peer_vals if v]
          total_demand = sum(v.get("capacity_demand_kW", 0.0) for v in peer_vals)

          # Priority-based allocation: anomaly valves bumped 1.5x.
          allocations: Dict[str, float] = {}
          for vid in branch_ids:
              if vid == self.valve_id:
                  continue
              vp = self.peer_states.get(vid, {})
              deficit = max(
                  0.0,
                  vp.get("capacity_demand_kW", 0.0) - vp.get("capacity_delivered_kW", 0.0),
              )
              anomaly_penalty = 1.5 if vp.get("anomaly_detected") else 1.0
              priority = deficit * anomaly_penalty
              # Allocate a small position bump proportional to priority.
              current_pos = vp.get("position_pct", 50.0)
              allocations[vid] = max(0.0, min(100.0, current_pos + priority * 0.02))

          self.broker.broadcast(
              self._setpoint_channel(), self.valve_id,
              {"leader_id": self.valve_id,
               "leader_alive": True,
               "branch_total_demand_kW": total_demand,
               "valve_setpoints": allocations},
              t_seconds,
          )
          self.last_setpoint_broadcast_at = t_seconds

      def consume_setpoint(self) -> Optional[float]:
          """Pop the latest leader-provided setpoint (one-shot)."""
          s = self.latest_setpoint
          self.latest_setpoint = None
          return s
  ```
- **MIRROR**: NAMING_CONVENTION; dataclass with `field(default_factory=...)`.
- **GOTCHA**:
  - PRD §5.3 uses `await asyncio.sleep(3.0)`. In sync engine we use elapsed simulated time — the election state machine straddles multiple ticks naturally.
  - Channels are namespaced per branch — branch A election does not interfere with branch B.
  - Leader skips itself in allocation (it broadcasts setpoints for its peers; its own position is controlled by its local PID via the ChillValveController).
  - `consume_setpoint()` is one-shot to ensure we apply each new leader directive at most once.
- **VALIDATE**: `tests/test_layer3_agent.py` — election convergence, peer-state collection, leader allocation.

### Task 5: Implement `sim/controllers/chillvalve.py`
- **ACTION**: Orchestrate Layer 1 → Layer 2 → Layer 3 → Layer 1 validate per PRD §6.
- **IMPLEMENT**:
  ```python
  """ChillValve controller. PRD §6.

  Orchestrates Layer 1 (rules), Layer 2 (ML), Layer 3 (multi-agent).
  Layer 1 has hard override; Layer 2 is informational; Layer 3 provides
  setpoints with fallback to local PID.
  """
  from __future__ import annotations
  from dataclasses import dataclass, field
  from typing import Dict, List

  from sim.broker import MessageBroker
  from sim.layers.layer1_rules import CRITICAL_ACTIONS, Layer1Rules
  from sim.layers.layer2_ml import Layer2ML
  from sim.layers.layer3_agent import ValveAgent
  from sim.types import ValveCommand, ValveState

  LOCAL_PID_TARGET_DT = 5.0
  LOCAL_PID_GAIN = 1.5   # %/°C error


  @dataclass
  class ChillValveController:
      layer1: Layer1Rules = field(default_factory=Layer1Rules)
      layer2: Layer2ML = field(default_factory=Layer2ML)
      broker: MessageBroker = field(default_factory=MessageBroker)
      agents: Dict[str, ValveAgent] = field(default_factory=dict)
      _initialized_at: float = -1.0

      def initialize(self, valve_ids: List[str], flow_max_per_valve: Dict[str, float], t_seconds: float) -> None:
          self.layer1.flow_max_gpm_per_valve = dict(flow_max_per_valve)
          for vid in valve_ids:
              branch_id = vid[0]  # 'A1' → 'A'
              self.agents[vid] = ValveAgent(valve_id=vid, branch_id=branch_id, broker=self.broker)
          # Boot-time leader: lowest id per branch.
          for branch_id in {vid[0] for vid in valve_ids}:
              branch_members = sorted(vid for vid in valve_ids if vid.startswith(branch_id))
              if branch_members:
                  self.agents[branch_members[0]].is_leader = True
                  self.agents[branch_members[0]].last_leader_heartbeat = t_seconds
          self._initialized_at = t_seconds

      def step(self, states: List[ValveState], t_seconds: float) -> Dict[str, ValveCommand]:
          all_ids = [s.valve_id for s in states]
          commands: Dict[str, ValveCommand] = {}

          # --- Layer 2: enrich each state with anomaly info ---
          for s in states:
              ar = self.layer2.evaluate(s)
              s.anomaly_detected = ar.anomaly_detected
              s.anomaly_confidence = ar.confidence

          # --- Layer 3: tick all agents (broadcast / collect / election / leader logic) ---
          for s in states:
              agent = self.agents[s.valve_id]
              agent.tick(s, all_ids, t_seconds)
              s.is_leader = agent.is_leader

          # --- Per-valve decision: Layer 1 override → Layer 3 setpoint → local PID → Layer 1 validate ---
          for s in states:
              rule_action = self.layer1.evaluate(s, t_seconds)
              if rule_action is not None and rule_action.action in CRITICAL_ACTIONS:
                  s.rule_fired = rule_action.reason
                  s.safety_override_active = True
                  pos = rule_action.value if rule_action.value is not None else 0.0
                  commands[s.valve_id] = ValveCommand(position_pct=pos, override=True)
                  self.layer1.record_command(s.valve_id, pos / 100.0, t_seconds)
                  continue

              if rule_action is not None:
                  s.rule_fired = rule_action.reason

              # Layer 3 setpoint, else local PID.
              agent = self.agents[s.valve_id]
              setpoint = agent.consume_setpoint()
              if setpoint is not None:
                  pos = setpoint
              else:
                  err = s.dT_C - LOCAL_PID_TARGET_DT
                  pos = s.position_pct + err * LOCAL_PID_GAIN

              pos = self.layer1.validate_command(pos, s)
              commands[s.valve_id] = ValveCommand(position_pct=pos, override=False)
              self.layer1.record_command(s.valve_id, pos / 100.0, t_seconds)

          return commands
  ```
- **MIRROR**: CONTROLLER_ORCHESTRATION pattern (PRD §6 exact order).
- **GOTCHA**:
  - The controller **mutates** `ValveState` to write back layer outputs (`anomaly_detected`, `is_leader`, `rule_fired`, `safety_override_active`). This matches PRD §5.4 line 596–608 explicit design.
  - Local PID falls back to per-valve ΔT control similar to Belimo but with a stronger gain (1.5 %/°C vs Belimo's fixed 2 %/tick) — agents that miss a leader broadcast still track design ΔT.
  - Boot-time leader assignment skips Phase 3's "every valve assumes it might be leader" phase from PRD §5.3 line 569 — instead we deterministically set lowest-id-per-branch leader at init. Election still runs naturally if the leader goes silent.
  - `branch_id = vid[0]` exploits the A1/A2/.../B1/.../B3 naming convention.
- **VALIDATE**: `tests/test_chillvalve_controller.py` — Layer 1 override beats Layer 3; Layer 2 anomaly status written; local PID fires on no-setpoint.

### Task 6: Extend `sim/engine.py` for chillvalve + compare modes
- **ACTION**: Add modes; capture per-tick layer activity; print delta.
- **IMPLEMENT** (replace `run()` and `main()`):
  ```python
  """Main simulation loop. PRD §10 Phases 2 + 3."""
  from __future__ import annotations
  import argparse
  from dataclasses import asdict
  from datetime import datetime
  from pathlib import Path
  from typing import Dict, List, Optional

  from sim.coil import Coil
  from sim.controllers.belimo_baseline import BelimoController
  from sim.controllers.chillvalve import ChillValveController
  from sim.io import write_jsonl
  from sim.scenarios import Scenario
  from sim.system import HydraulicSystem

  SCENARIOS_DIR = Path(__file__).resolve().parent.parent / "data" / "scenarios"
  RUNS_DIR = Path(__file__).resolve().parent.parent / "data" / "runs"


  def _summarize(records: List[dict]) -> Dict[str, float]:
      n = len(records)
      n_valves = len(records[0]["valves"])
      total_kwh = sum(r["pump_kw"] for r in records) / 3600.0
      mean_dT = sum(st["dT_C"] for r in records for st in r["valves"]) / (n * n_valves)
      l1_fires = sum(1 for r in records for st in r["valves"] if st.get("rule_fired"))
      leader_changes = sum(
          1
          for r0, r1 in zip(records, records[1:], strict=False)
          for s0, s1 in zip(r0["valves"], r1["valves"], strict=False)
          if s0.get("is_leader") != s1.get("is_leader")
      )
      return {
          "pump_kwh": total_kwh,
          "mean_dT": mean_dT,
          "layer1_fires": l1_fires,
          "leader_changes": leader_changes,
      }


  def _run_single(scenario_name: str, mode: str, log_every: int) -> tuple[Path, Dict[str, float]]:
      scenario = Scenario.load(SCENARIOS_DIR / f"{scenario_name}.json")
      system = HydraulicSystem.build_default()
      if not scenario.valve_ids:
          scenario.valve_ids = list(system.valves.keys())

      controller: object
      if mode == "belimo":
          controller = BelimoController()
      elif mode == "chillvalve":
          controller = ChillValveController()
          flow_max = {vid: rec.coil.design_flow_gpm * 1.5 for vid, rec in system.valves.items()}
          controller.initialize(list(system.valves.keys()), flow_max, t_seconds=0.0)
      else:
          raise ValueError(f"unsupported mode: {mode!r}")

      records: List[dict] = []
      states = system.tick(0)

      print(f"[engine] '{scenario.name}' mode={mode} ticks={scenario.duration_seconds}")
      for t in range(scenario.duration_seconds):
          for rec in system.valves.values():
              rec.coil = Coil(
                  design_flow_gpm=rec.coil.design_flow_gpm,
                  design_dT_C=rec.coil.design_dT_C,
                  load_fraction=scenario.load_fraction(rec.valve_id, t),
              )

          if mode == "belimo":
              commands = controller.step(states)
          else:
              commands = controller.step(states, t_seconds=float(t))

          system.set_positions(commands)
          states = system.tick(t)

          total_flow = system.solve_network()
          head = system.pump.head_kpa(total_flow)
          pump_kw = system.pump.power_kw(total_flow, head)

          records.append({
              "tick": t,
              "pump_kw": pump_kw,
              "pump_head_kpa": head,
              "total_flow_gpm": total_flow,
              "valves": [
                  {
                      "valve_id": st.valve_id,
                      "branch_id": st.branch_id,
                      "flow_gpm": st.flow_gpm,
                      "dT_C": st.dT_C,
                      "position_pct": st.position_pct,
                      "rule_fired": st.rule_fired,
                      "safety_override_active": st.safety_override_active,
                      "anomaly_detected": st.anomaly_detected,
                      "anomaly_confidence": st.anomaly_confidence,
                      "is_leader": st.is_leader,
                  }
                  for st in states
              ],
          })

          if t % log_every == 0:
              print(f"[engine] tick {t:4d}  pump_kw={pump_kw:.2f}  flow={total_flow:.0f} GPM")

      RUNS_DIR.mkdir(parents=True, exist_ok=True)
      ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
      out = RUNS_DIR / f"{scenario_name}_{mode}_{ts}.jsonl"
      write_jsonl(out, records)
      summary = _summarize(records)
      print(f"[summary] pump_kwh={summary['pump_kwh']:.2f}  mean_dT={summary['mean_dT']:.2f}  "
            f"layer1_fires={summary['layer1_fires']}  leader_changes={summary['leader_changes']}")
      return out, summary


  def run(scenario_name: str, mode: str, log_every: int = 300) -> Path:
      if mode in ("belimo", "chillvalve"):
          path, _ = _run_single(scenario_name, mode, log_every)
          return path
      if mode == "compare":
          _, belimo = _run_single(scenario_name, "belimo", log_every)
          _, cv = _run_single(scenario_name, "chillvalve", log_every)
          delta = cv["pump_kwh"] - belimo["pump_kwh"]
          pct = (delta / belimo["pump_kwh"]) * 100.0 if belimo["pump_kwh"] else 0.0
          print(f"[compare] belimo:     pump_kwh={belimo['pump_kwh']:.2f}  mean_dT={belimo['mean_dT']:.2f}")
          print(f"[compare] chillvalve: pump_kwh={cv['pump_kwh']:.2f}  mean_dT={cv['mean_dT']:.2f}")
          print(f"[compare] delta:      {delta:+.2f} kWh   ({pct:+.1f} %)")
          return Path("compare")
      raise ValueError(f"unsupported mode: {mode!r}")


  def main() -> None:
      p = argparse.ArgumentParser()
      p.add_argument("--scenario", default="steady_state")
      p.add_argument("--mode", default="belimo", choices=["belimo", "chillvalve", "compare"])
      p.add_argument("--log-every", type=int, default=300)
      args = p.parse_args()
      run(args.scenario, args.mode, log_every=args.log_every)


  if __name__ == "__main__":
      main()
  ```
- **MIRROR**: existing engine.py structure.
- **GOTCHA**:
  - `_run_single` is shared between belimo, chillvalve, and the two halves of compare. `compare` always runs belimo first so the user sees the slower (faster wall-clock-anyway) baseline early.
  - `flow_max` for Layer 1 Rule 2 is set to 1.5× design flow per valve — generous so legitimate steady-state behavior doesn't trip it. PRD doesn't specify; this is a pragmatic default.
  - `consume_setpoint()` in ChillValve agents pops on read — controller calls it once per tick to ensure each setpoint is applied at most once.
- **VALIDATE**: `python -m sim.engine --mode chillvalve` runs to completion; `--mode compare` prints a delta line.

### Task 7: Tests
- **ACTION**: New test files per Files-to-Change.
- **IMPLEMENT** (key cases):
  - `test_layer1_rules.py`:
    - Each of 5 rules has a triggering state → returns expected `RuleAction`
    - Happy-path state → returns `None` and records `last_known_good`
    - `validate_command` clamps to [0,100]; forces 0 when `dP > 600`
  - `test_layer2_ml.py`:
    - Placeholder returns `anomaly_detected=False, confidence=0.0`
  - `test_broker.py`:
    - broadcast then collect returns the message
    - Two channels are isolated
    - Messages older than 60 s are pruned on broadcast
    - `collect(since)` excludes messages at/before `since`
  - `test_layer3_agent.py`:
    - Election converges to lowest valve_id after heartbeat timeout
    - Non-leader receives setpoints from leader broadcast
    - Leader's `_leader_broadcast` emits a setpoint for each peer
    - `consume_setpoint()` is one-shot
  - `test_chillvalve_controller.py`:
    - Critical rule fires → ValveCommand has `override=True` and skips Layer 3
    - With no leader broadcasts yet, fallback local PID adjusts position toward target ΔT
    - `initialize` boots branch leaders deterministically
  - `test_engine.py` (extend):
    - chillvalve full scenario produces pump_kwh in [1, 8] and mean_dT in [3.5, 6.5]
    - compare mode prints both summaries and runs to completion
- **MIRROR**: TEST_STRUCTURE from Phase 2.
- **GOTCHA**: Election tests must explicitly advance "t_seconds" through the agent.tick calls — the broker has no real clock.
- **VALIDATE**: `uv run pytest -v` — all new tests pass.

### Task 8: `scripts/validate_chillvalve_vs_belimo.py`
- **ACTION**: Asserts both modes complete and reports the delta.
- **IMPLEMENT**:
  ```python
  """Validate that ChillValve mode runs end-to-end and reports a measurable delta.

  Does NOT assert "ChillValve must save X%" — Phase 3 coordination is light
  (placeholder Layer 2, no fault scenarios). Phase 4 (real ML + fault scenarios)
  is when meaningful savings are expected. This script just confirms both modes
  complete and the delta is reported.

  Usage:
      uv run python scripts/validate_chillvalve_vs_belimo.py
  """
  from __future__ import annotations
  import json
  import sys
  from pathlib import Path

  sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

  from sim.engine import _run_single  # noqa: E402


  def main() -> int:
      _, belimo = _run_single("steady_state", "belimo", log_every=10**9)
      _, cv = _run_single("steady_state", "chillvalve", log_every=10**9)
      delta = cv["pump_kwh"] - belimo["pump_kwh"]
      pct = (delta / belimo["pump_kwh"]) * 100.0
      print(f"belimo:     pump_kwh={belimo['pump_kwh']:.3f}  mean_dT={belimo['mean_dT']:.2f}")
      print(f"chillvalve: pump_kwh={cv['pump_kwh']:.3f}  mean_dT={cv['mean_dT']:.2f}")
      print(f"delta:      {delta:+.3f} kWh ({pct:+.1f} %)")
      # Sanity bounds — both should be in the same physical envelope as Phase 2.
      for name, s in (("belimo", belimo), ("chillvalve", cv)):
          if not 1.0 <= s["pump_kwh"] <= 10.0:
              print(f"FAIL: {name} pump_kwh {s['pump_kwh']} outside [1, 10]", file=sys.stderr)
              return 1
          if not 3.0 <= s["mean_dT"] <= 7.0:
              print(f"FAIL: {name} mean_dT {s['mean_dT']} outside [3, 7] C", file=sys.stderr)
              return 1
      return 0


  if __name__ == "__main__":
      sys.exit(main())
  ```
- **VALIDATE**: `uv run python scripts/validate_chillvalve_vs_belimo.py` exits 0.

### Task 9: Update README
- **ACTION**: Add ChillValve and compare modes; update status.
- **IMPLEMENT**: Append a "ChillValve mode + comparison" section and update Status line to "Phase 3 complete".
- **VALIDATE**: `grep chillvalve README.md` returns lines.

### Task 10: Final sweep
- **ACTION**: ruff, pytest with coverage, both validate scripts.
- **VALIDATE**: All green.

---

## Testing Strategy

### Unit Tests
~20 new tests across 5 new test files. Combined with Phase 1+2's 48, expect ~68 tests in suite.

### Edge Cases Checklist
- [ ] All 5 rules fire under exact triggers; happy path returns None
- [ ] Layer 2 placeholder returns benign result
- [ ] Broker 60-s trim works at the boundary
- [ ] Two simultaneous elections in branch A and branch B do not interfere
- [ ] Leader dies (we drop is_leader on a fake agent) → new election → new leader is next-lowest id
- [ ] Local PID kicks in when Layer 3 has no setpoint yet (boot ticks)
- [ ] Critical rule (dP > 600 kPa) forces position=0 even if Layer 3 wanted otherwise

---

## Validation Commands

### Static Analysis
```bash
uv run ruff check .
```
EXPECT: All checks passed.

### Unit Tests
```bash
uv run pytest -v
```
EXPECT: ~68 tests pass.

### Coverage
```bash
uv run pytest --cov=sim --cov-report=term-missing
```
EXPECT: ≥ 85 % overall on sim/.

### ChillValve E2E
```bash
uv run python -m sim.engine --scenario steady_state --mode chillvalve
```
EXPECT: pump_kwh and mean_dT in physical envelope; engine prints layer1_fires/leader_changes line.

### Compare mode
```bash
uv run python -m sim.engine --scenario steady_state --mode compare
```
EXPECT: prints belimo / chillvalve summaries + delta.

### Validate script
```bash
uv run python scripts/validate_chillvalve_vs_belimo.py
```
EXPECT: Exit 0.

### Manual Validation
- [ ] At least 1 leader change shows up in chillvalve run summary
- [ ] `is_leader=true` is recorded in JSONL for A1 and B1 (boot leaders)
- [ ] No layer1 false-positive fires in steady state (count should be ~0 unless dT spikes happen)

---

## Acceptance Criteria
- [ ] All tasks 1–10 completed
- [ ] Ruff and pytest green
- [ ] Coverage on new files ≥ 85 %
- [ ] `--mode chillvalve` runs to completion
- [ ] `--mode compare` prints both summaries and delta
- [ ] PRD §15 acceptance #6 partially met: "leader failover scenario demonstrates Layer 3 recovering within 30 seconds" — covered by `test_layer3_agent.py` election convergence test

## Completion Checklist
- [ ] Code follows Phase 1+2 patterns
- [ ] No backwards-compat shims, no premature abstractions
- [ ] All ValveState layer-output fields populated by ChillValveController (no longer hard-coded defaults from HydraulicSystem)
- [ ] Layer 2 placeholder signature matches what Phase 4 will need
- [ ] No comments explaining what code does — only why-non-obvious
- [ ] Election test asserts the bully outcome, not just "some leader emerged"

## Risks
| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Election windows in sim-seconds tangle with engine tick=1s cadence | Medium | Medium | Tests pass explicit `t_seconds`; engine passes `float(t)` (tick number) |
| ChillValve makes things *worse* (positive delta) | Medium | Low | Phase 3 placeholder Layer 2 + no fault scenarios mean meaningful savings come in Phase 4; validate script doesn't require negative delta |
| Layer 1 Rule 2 (flow ceiling) fires under normal steady state | Medium | Low | `flow_max = design_flow * 1.5` gives ample headroom; test verifies no fire in steady state |
| Broker memory grows unbounded under high message volume | Low | Low | 60-s trim on every broadcast; bounded by O(tick_rate × 60) per channel |
| Local PID fallback gain (1.5 %/°C) over- or under-shoots | Medium | Low | Mean ΔT band [3.5, 6.5] in validate script catches divergence |
| `branch_id = vid[0]` breaks if valve ids change format | Low | High | Tests use literal "A1"/"B2" etc.; if format changes, tests fail loudly |

## Notes
- The sync broker is intentionally minimalist — Phase 5 wraps it for asyncio without changing the message semantics.
- Boot-time deterministic leader assignment (lowest id) skips the noisy startup election from PRD §5.3 line 568 — saves ~15s of simulated time before coordination is online.
- Phase 4's ML model will swap out only `Layer2ML.evaluate`'s body and the `__init__` signature. All call sites remain stable because we only consume `AnomalyResult`.
- The compare-mode delta in Phase 3 is **not** expected to show meaningful savings. Real savings need (a) the trained Isolation Forest and (b) fault scenarios that exercise the coordination logic. This is documented in the Phase 3 report and ChillValve-vs-Belimo script comments.

---

**Confidence Score: 6/10** — Large complexity with three orthogonal subsystems (rules, agents, controller orchestration). Highest risk is the agent election state machine working correctly across simulated ticks. Plan covers it with explicit time-passing tests. Local PID gain may need tuning if mean_dT drifts.
