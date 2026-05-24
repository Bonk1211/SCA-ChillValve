# Plan: Simulation Core — 6-Valve System, Pump Model, Belimo Baseline, Scenario Engine

## Summary
Build the runnable single-mode simulation: a 2-branch / 6-valve hydraulic network with a single shared pump, the Belimo Energy Valve baseline controller, a scenario loader (steady-state scenario A), and an `engine.py` main loop that ticks the simulation at 1 sim-second cadence, computes coil thermal behavior, accumulates pump energy, and emits a JSON timeseries. Output validates that a 60-min steady-state run produces pump energy in the realistic ~10 kWh range called out in PRD §6.

## User Story
As the software lead, I want a working single-mode simulation that runs end-to-end with the Belimo baseline controller, so that Phase 3 (three-layer intelligence) has a reference to compare against and Phase 5 (FastAPI backend) has a tickable simulation to stream from.

## Problem → Solution
**Current state:** After Phase 1, `sim/valve.py` computes flow for a single valve given position and ΔP. There is no system-level coupling: no pump, no branch aggregation, no coil thermals, no time loop, no controller, no scenario, no output. Cannot demo or measure anything.
**Desired state:** `uv run python -m sim.engine --scenario steady_state --mode belimo` runs a 60-min simulated scenario in <10s wall-clock, writes a JSON timeseries to `data/runs/{scenario}_{mode}_{timestamp}.json`, prints a summary (total pump energy in kWh, mean ΔT, min/max valve position) to stdout. Acceptance: pump energy lands in 8–15 kWh for the steady-state scenario (matches PRD §6 baseline expectation of ~10 kWh).

## Metadata
- **Complexity**: Medium
- **Source PRD**: `docs/ChillValve_Implementation_PRD_v1.md`
- **PRD Phase**: Phase 2 — Simulation Core (PRD §10, steps 4–7)
- **Estimated Files**: ~10 (system.py, pump.py, coil.py, controllers/belimo_baseline.py, scenarios.py, engine.py, data/scenarios/steady_state.json, tests for each)

---

## UX Design

### Before
Developer can call `Valve(DN65).flow_gpm(0.7, 100.0)` and get a number. No way to run a scenario or observe behavior over time.

### After
```
$ uv run python -m sim.engine --scenario steady_state --mode belimo
[engine] loaded scenario 'steady_state' (60 min, 6 valves, 2 branches)
[engine] mode=belimo, tick=1s, total_ticks=3600
[engine] tick 0   pump_dP=180 kPa  pump_kW=2.10  total_flow=520 GPM
[engine] tick 300 pump_dP=178 kPa  pump_kW=2.08  total_flow=515 GPM
...
[engine] complete in 4.2s wall-clock
[summary] total_pump_energy = 10.43 kWh
[summary] mean_dT            = 4.92 C
[summary] valve_pos_range    = [0.62, 0.78]
[summary] timeseries written to data/runs/steady_state_belimo_20260524_111532.json
```

### Interaction Changes
| Touchpoint | Before | After | Notes |
|---|---|---|---|
| CLI | `pytest` only | `python -m sim.engine ...` runs scenarios | Argparse interface |
| Output | None | JSON timeseries per run | One record per tick per valve + system-level row |
| Validation | Unit tests only | `pytest` + `scripts/validate_baseline_energy.py` | Asserts kWh in expected range |

---

## Mandatory Reading

| Priority | File | Lines | Why |
|---|---|---|---|
| P0 | `docs/ChillValve_Implementation_PRD_v1.md` | 138–225 | §4 — system config, hydraulic equations, pump model, scenarios |
| P0 | `docs/ChillValve_Implementation_PRD_v1.md` | 620–693 | §6 — Belimo baseline controller spec + expected energy outcome |
| P0 | `sim/valve.py` | all | Phase 1 hydraulic primitive — `Valve.flow_gpm(position, dP_kPa)` |
| P0 | `sim/types.py` | all | `ValveState`, `ValveSpec`, `ValveCommand`; conventions for downstream |
| P0 | `sim/units.py` | all | Conversion constants; `gpm_to_kg_per_s` used by coil thermal model |
| P1 | `docs/ChillValve_Implementation_PRD_v1.md` | 750–793 | §7.3 — SQLite schema reference (we don't write SQL yet, but JSON keys should mirror so Phase 5 can ingest) |
| P1 | `.claude/PRPs/plans/completed/foundation-repo-and-hydraulic-model.plan.md` | all | Phase 1 plan — patterns to mirror exactly |
| P2 | `.claude/PRPs/reports/foundation-repo-and-hydraulic-model-report.md` | all | Phase 1 deviations & lessons (sys.path script pattern, dropped UP ruff rules, etc.) |

## External Documentation

| Topic | Source | Key Takeaway |
|---|---|---|
| Pump affinity laws | Standard HVAC reference | `P_hyd [kW] = (Q[GPM] × ΔP[psi]) / 5308`; with η: `P_pump = P_hyd / η`. The PRD §4.3 formula uses 3960 (HP eq) but works in mixed units — verify against a sanity case. |
| Newton's method / fixed-point iteration | scipy.optimize | For network solving: given all valve positions and pump curve, find ΔP per branch such that ΔP_pump = ΔP_branch_loss + ΔP_branch_valve and Σ branch flows = pump_Q(ΔP). Use `scipy.optimize.brentq` for the 1-D root. |
| argparse for CLI | Python stdlib | `python -m sim.engine --scenario steady_state --mode belimo --duration 3600` |

---

## Patterns to Mirror

Phase 1 established patterns. Continue them exactly.

### NAMING_CONVENTION
// SOURCE: `sim/valve.py` (Phase 1)
```python
# Modules: snake_case
# Classes: PascalCase, frozen dataclasses for value types, regular dataclasses for state
# Functions: snake_case, leading _ for private
# Constants: UPPER_SNAKE
# Type hints: Optional[...] / List[...] per PRD-mirror (ruff UP disabled)
```

### ERROR_HANDLING
// SOURCE: `sim/valve.py` lines 30, 38 (raise ValueError on out-of-domain input)
```python
if not 0.0 <= position <= 1.0:
    raise ValueError(f"position must be in [0, 1], got {position!r}")
# Pattern: cheap input guards on public methods; no try/except, no fallbacks.
# Internal call sites are trusted (per top-level system prompt).
```

### TEST_STRUCTURE
// SOURCE: `tests/test_valve.py` (Phase 1)
```python
import math
import pytest
from sim.valve import Valve
from sim.types import ValveSpec

@pytest.mark.parametrize("spec, expected", [(ValveSpec.DN65, 47.0), ...])
def test_thing(spec, expected):
    assert math.isclose(actual, expected, rel_tol=1e-9)
```

### SCRIPT_SHEBANG
// SOURCE: `scripts/plot_cv_curves.py` (Phase 1)
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
# Required because no [build-system] in pyproject; `sim/` is not installed.
```

### TYPE_FILE_LAYOUT
// SOURCE: `sim/types.py` — dataclasses grouped, constants UPPER_SNAKE at module level

### ENGINE_LOOP_PATTERN
```python
# Inspired by PRD §5 + §11 pseudocode. Synchronous tick loop.
for tick in range(total_ticks):
    state = system.step(tick, controller, scenario)
    history.append(state.snapshot())
```

---

## Files to Change

| File | Action | Justification |
|---|---|---|
| `sim/pump.py` | CREATE | `Pump` class with affinity-curve based head/power per PRD §4.3 |
| `sim/coil.py` | CREATE | `Coil` thermal model — capacity_demand, ΔT_achieved per PRD §4.2 lines 176–188 |
| `sim/system.py` | UPDATE (replace stub) | `HydraulicSystem`: 6 `Valve` instances + 1 `Pump`; solves the steady-state flow network each tick; exposes `step(commands) -> List[ValveState]` |
| `sim/controllers/belimo_baseline.py` | UPDATE (replace stub) | `BelimoController.step(state) -> ValveCommand` exactly per PRD §6 |
| `sim/scenarios.py` | UPDATE (replace stub) | `Scenario` dataclass + loader from JSON; computes per-tick load disturbance |
| `sim/engine.py` | UPDATE (replace stub) | Argparse CLI; loads scenario, instantiates system + controller, ticks the loop, writes timeseries JSON, prints summary |
| `sim/io.py` | CREATE | `write_timeseries(path, records)` — append-friendly JSON Lines format |
| `data/scenarios/steady_state.json` | CREATE | Scenario A per PRD §4.4: 6 valves at 70% load, ±5% fluctuations every 5 min, 60 min duration |
| `tests/test_pump.py` | CREATE | Pump curve sanity: zero flow → static head; affinity scaling |
| `tests/test_coil.py` | CREATE | Coil thermal: under-flow → ΔT collapse; over-flow → ΔT degrades; design flow → ΔT_design |
| `tests/test_system.py` | CREATE | 6-valve system steady-state convergence; sum of branch flows = pump flow; mass-balance invariant |
| `tests/test_belimo.py` | CREATE | Belimo step logic: under-ΔT → close; over-ΔT → open; deadband |
| `tests/test_scenarios.py` | CREATE | Steady-state scenario produces 3600 ticks; load disturbance bounded to ±5% |
| `tests/test_engine.py` | CREATE | End-to-end smoke: 60-min Belimo run completes; pump energy in 8–15 kWh; output JSON valid |
| `scripts/validate_baseline_energy.py` | CREATE | Runs the scenario and asserts pump energy is in expected range; non-zero exit if out of bounds |
| `README.md` | UPDATE | Add "Run a scenario" section; update Status line to "Phase 2 complete" |

## NOT Building

- Layer 1/2/3 intelligence (still Phase 3)
- ChillValve controller (`sim/controllers/chillvalve.py` stays a stub — Phase 3)
- ML training (`ml/` stays empty — Phase 4)
- FastAPI / WebSocket (Phase 5)
- SQLite persistence (Phase 5 — JSON output here is intentionally simple)
- Frontend (Phase 6)
- Load Spike scenario B and Fault scenario C (Phase 3/4 — only steady_state scenario A in Phase 2)
- Fault injection (Phase 3/4)
- Belimo baseline pump "constant-ΔP at remote sensor" — we approximate with constant-ΔP at the pump for Phase 2; the remote-sensor variant is a Phase 2.1 polish if time permits

---

## Step-by-Step Tasks

### Task 1: Implement `sim/pump.py`
- **ACTION**: Create `Pump` class with system-curve based head and power.
- **IMPLEMENT**:
  ```python
  """Pump model. PRD §4.3."""
  from __future__ import annotations
  from dataclasses import dataclass


  @dataclass(frozen=True)
  class Pump:
      """Single variable-speed pump serving both branches.

      Head curve (approximate): ΔP_pump = ΔP_static + k * Q^2
      Power: P_pump_kW = (Q[GPM] * ΔP_pump[kPa]) / (3960 * η) * conversion

      PRD §4.3 uses 3960 (imperial HP equation); we keep it consistent by
      converting inputs to imperial inside `power_kw`.
      """

      max_head_kpa: float = 250.0     # PRD §4.1 pump max head
      max_flow_gpm: float = 800.0     # PRD §4.1 pump max flow
      efficiency: float = 0.65        # PRD §4.1
      static_head_kpa: float = 50.0   # base head at zero flow

      @property
      def k(self) -> float:
          # ΔP(Q_max) = max_head ⇒ k = (max_head - static_head) / Q_max^2
          return (self.max_head_kpa - self.static_head_kpa) / (self.max_flow_gpm ** 2)

      def head_kpa(self, flow_gpm: float) -> float:
          if flow_gpm < 0.0:
              raise ValueError(f"flow_gpm must be >= 0, got {flow_gpm!r}")
          return self.static_head_kpa + self.k * flow_gpm * flow_gpm

      def power_kw(self, flow_gpm: float, head_kpa: float) -> float:
          if flow_gpm < 0.0 or head_kpa < 0.0:
              raise ValueError("flow_gpm and head_kpa must be >= 0")
          from sim.units import kpa_to_psi
          head_psi = kpa_to_psi(head_kpa)
          hydraulic_hp = (flow_gpm * head_psi) / 3960.0
          return (hydraulic_hp * 0.7457) / self.efficiency
  ```
- **MIRROR**: NAMING_CONVENTION, ERROR_HANDLING. `frozen=True` like `Valve`.
- **IMPORTS**: `dataclasses`, `sim.units.kpa_to_psi` (lazy import to avoid circular).
- **GOTCHA**: PRD §4.3 formula uses 3960 which yields hydraulic horsepower (imperial) for Q in GPM × ΔP in psi. Convert to kW (×0.7457) **then** divide by efficiency (mechanical power input). Sanity: at 500 GPM × 200 kPa (29 psi) with η=0.65, expect ~4 kW.
- **VALIDATE**: `tests/test_pump.py`; smoke: `Pump().power_kw(500, 200)` returns ~4.2 kW.

### Task 2: Implement `sim/coil.py`
- **ACTION**: Coil thermal behavior per PRD §4.2.
- **IMPLEMENT**:
  ```python
  """Coil thermal model. PRD §4.2 lines 176–188."""
  from __future__ import annotations
  from dataclasses import dataclass

  from sim.units import CP_WATER_KJ_PER_KG_K, gpm_to_kg_per_s


  @dataclass(frozen=True)
  class Coil:
      """Air-side load coupled to chilled-water flow via design ΔT.

      capacity_demand_kW = m_dot_design * Cp * dT_design
      m_dot_design is computed from a design flow (per-valve sizing).
      """

      design_flow_gpm: float       # set by valve sizing (DN65: ~50 GPM, DN100: ~150 GPM)
      design_dT_C: float = 5.0     # PRD §4.1
      load_fraction: float = 1.0   # fraction of design load currently applied (set by scenario)

      @property
      def capacity_demand_kw(self) -> float:
          m_dot_design = gpm_to_kg_per_s(self.design_flow_gpm)
          return self.load_fraction * m_dot_design * CP_WATER_KJ_PER_KG_K * self.design_dT_C

      def achieved_dT(self, flow_gpm: float) -> float:
          """ΔT actually achieved given the current flow.

          Underflow: capacity bound by flow → ΔT collapses upward (return temp rises only
            as much as flow can absorb). PRD says "ΔT collapses when underflowing".
          Overflow: capacity bound by load → ΔT degrades downward.
          """
          if flow_gpm <= 0.0:
              return 0.0
          m_dot = gpm_to_kg_per_s(flow_gpm)
          # capacity the coil could deliver if flow had ΔT_design
          design_capacity = gpm_to_kg_per_s(self.design_flow_gpm) * CP_WATER_KJ_PER_KG_K * self.design_dT_C
          demand = self.load_fraction * design_capacity
          # achievable: m_dot * Cp * ΔT = min(demand, m_dot * Cp * ΔT_design)
          max_capacity_at_design_dT = m_dot * CP_WATER_KJ_PER_KG_K * self.design_dT_C
          actual_capacity = min(demand, max_capacity_at_design_dT)
          return actual_capacity / (m_dot * CP_WATER_KJ_PER_KG_K)

      def delivered_capacity_kw(self, flow_gpm: float) -> float:
          return self.achieved_dT(flow_gpm) * gpm_to_kg_per_s(flow_gpm) * CP_WATER_KJ_PER_KG_K
  ```
- **MIRROR**: NAMING_CONVENTION; mirror Valve's `@dataclass(frozen=True)` for value objects.
- **IMPORTS**: `sim.units`.
- **GOTCHA**: PRD §4.2 has two branches: (i) `m_dot_actual < m_dot_design` → "ΔT collapses" (formula yields larger ΔT than design when capacity_demand fixed but flow drops — physical because slower water absorbs more degrees), (ii) `m_dot_actual > m_dot_design` → "ΔT degrades" (more flow than needed, capacity is load-bound). Our `min(demand, max_capacity)` correctly captures both regimes. **Do not** "fix" the PRD's "ΔT collapses upward" wording — that's the correct physics; faster underflow → bigger ΔT.
- **VALIDATE**: `tests/test_coil.py`; at design flow, `achieved_dT == design_dT`; below design flow, `achieved_dT > design_dT`.

### Task 3: Implement `sim/system.py` (replace stub)
- **ACTION**: 6-valve, 2-branch, 1-pump hydraulic network with steady-state network solver.
- **IMPLEMENT**:
  ```python
  """6-valve hydraulic system with shared pump. PRD §4."""
  from __future__ import annotations
  from dataclasses import dataclass, field
  from datetime import datetime
  from typing import Dict, List

  from scipy.optimize import brentq

  from sim.coil import Coil
  from sim.pump import Pump
  from sim.types import ValveCommand, ValveSpec, ValveState
  from sim.valve import Valve


  # --- Branch / valve topology per PRD §4.1 ---
  # Branch A = 3 × DN65 (CRAH), Branch B = 3 × DN100 (AHU)
  BRANCH_TOPOLOGY: Dict[str, List[tuple]] = {
      "A": [("A1", ValveSpec.DN65, 50.0), ("A2", ValveSpec.DN65, 50.0), ("A3", ValveSpec.DN65, 50.0)],
      "B": [("B1", ValveSpec.DN100, 150.0), ("B2", ValveSpec.DN100, 150.0), ("B3", ValveSpec.DN100, 150.0)],
  }
  # tuple = (valve_id, spec, design_flow_gpm)

  SUPPLY_TEMP_C = 7.0   # PRD §4.1
  DESIGN_DT_C = 5.0     # PRD §4.1
  BRANCH_PIPE_LOSS_COEF_KPA_PER_GPM2 = 0.0001  # tunable; small distributed branch loss


  @dataclass
  class ValveRecord:
      """Static metadata + dynamic state for one valve."""
      valve_id: str
      branch_id: str
      spec: ValveSpec
      valve: Valve
      coil: Coil
      position: float = 0.5     # unit interval, current actuator position
      commanded_position: float = 0.5


  @dataclass
  class HydraulicSystem:
      """6-valve / 2-branch network with one shared pump.

      Per tick: given the current valve positions and the pump curve, solves
      the network for branch ΔPs and per-valve flows by 1-D root finding on
      total system flow.
      """

      pump: Pump = field(default_factory=Pump)
      valves: Dict[str, ValveRecord] = field(default_factory=dict)

      @classmethod
      def build_default(cls) -> "HydraulicSystem":
          sys = cls()
          for branch_id, members in BRANCH_TOPOLOGY.items():
              for vid, spec, design_flow in members:
                  sys.valves[vid] = ValveRecord(
                      valve_id=vid,
                      branch_id=branch_id,
                      spec=spec,
                      valve=Valve(spec=spec),
                      coil=Coil(design_flow_gpm=design_flow, design_dT_C=DESIGN_DT_C),
                  )
          return sys

      def set_positions(self, commands: Dict[str, ValveCommand]) -> None:
          for vid, cmd in commands.items():
              rec = self.valves[vid]
              rec.commanded_position = max(0.0, min(1.0, cmd.position_pct / 100.0))
              # For Phase 2 we assume instantaneous actuator (no slew rate)
              rec.position = rec.commanded_position

      def _branch_flow(self, branch_id: str, branch_dP_kpa: float) -> float:
          """Sum of valve flows in a branch at the given ΔP across the branch."""
          total = 0.0
          for rec in self.valves.values():
              if rec.branch_id != branch_id:
                  continue
              total += rec.valve.flow_gpm(rec.position, branch_dP_kpa)
          return total

      def _total_flow_at_pump_head(self, head_kpa: float) -> float:
          """Both branches see the same available head (parallel)."""
          # Subtract a small distributed branch pipe loss (Δp_loss = k * Q^2 per branch)
          # For Phase 2 simplicity assume pipe loss is small; we set branch_dP ≈ head.
          # (Refinement available in Phase 2.1 if needed.)
          return sum(self._branch_flow(b, head_kpa) for b in BRANCH_TOPOLOGY)

      def solve_network(self) -> float:
          """Return the equilibrium total flow [GPM]. Equation: pump curve == system curve.

          pump.head_kpa(Q) decreases with Q; valves' total flow at that head increases with Q
          (more head → more flow per valve). The root is where they intersect.
          Define f(Q) = _total_flow_at_pump_head(pump.head_kpa(Q)) - Q  and find f(Q) = 0.
          """

          def residual(q: float) -> float:
              head = self.pump.head_kpa(q)
              return self._total_flow_at_pump_head(head) - q

          # Bracket: at Q=0, head is max → valves can supply > 0; residual > 0.
          # At Q = pump.max_flow_gpm, head is at minimum → valves can supply < Q; residual < 0.
          lo, hi = 0.0, self.pump.max_flow_gpm
          f_lo = residual(lo + 1e-6)
          f_hi = residual(hi - 1e-6)
          if f_lo <= 0:
              return 0.0
          if f_hi >= 0:
              return hi
          return brentq(residual, lo + 1e-6, hi - 1e-6, xtol=1e-3)

      def tick(self, t_seconds: int) -> List[ValveState]:
          """Solve the network and return one ValveState per valve."""
          total_flow = self.solve_network()
          head = self.pump.head_kpa(total_flow)
          now = datetime.utcnow()
          out: List[ValveState] = []
          for rec in self.valves.values():
              flow = rec.valve.flow_gpm(rec.position, head)
              dT = rec.coil.achieved_dT(flow)
              cap_delivered = rec.coil.delivered_capacity_kw(flow)
              out.append(ValveState(
                  flow_gpm=flow,
                  dT_C=dT,
                  position_pct=rec.position * 100.0,
                  supply_temp_C=SUPPLY_TEMP_C,
                  return_temp_C=SUPPLY_TEMP_C + dT,
                  dP_kPa=head,
                  capacity_demand_kW=rec.coil.capacity_demand_kw,
                  capacity_delivered_kW=cap_delivered,
                  rule_fired=None,
                  safety_override_active=False,
                  anomaly_detected=False,
                  anomaly_confidence=0.0,
                  anomaly_features=[],
                  is_leader=False,
                  coordination_setpoint=None,
                  peer_states_count=0,
                  last_election_time=None,
                  timestamp=now,
                  valve_id=rec.valve_id,
                  branch_id=rec.branch_id,
              ))
          return out

      def pump_power_kw(self) -> float:
          q = self.solve_network()
          return self.pump.power_kw(q, self.pump.head_kpa(q))
  ```
- **MIRROR**: NAMING_CONVENTION; dataclass conventions from Phase 1.
- **IMPORTS**: scipy.optimize.brentq, sim.coil, sim.pump, sim.types, sim.valve, datetime.
- **GOTCHA**: 
  - Network solver uses `scipy.optimize.brentq` (1-D bracketed root). Pump curve monotone-decreasing in Q; valve-supply curve monotone-increasing in head. Single intersection guaranteed for non-pathological inputs.
  - At Q=0 the pump can deliver max head but valves at that head would carry > 0 flow → residual > 0 at lower bracket. At Q=max_flow_gpm the pump head bottoms out at `static_head_kpa` → valves would carry < max flow → residual < 0 at upper bracket. If either bound has the wrong sign (e.g. all valves nearly closed), return the bracket endpoint instead of asserting — robust against degenerate scenarios.
  - We assume instantaneous actuator response (commanded_position = position next tick). Phase 3+ may add slew-rate limits.
  - `ValveState` has many fields that don't apply in Phase 2 (anomaly, leader). Fill with neutral defaults (False, 0.0, [], None) since Phase 1 plan explicitly chose no dataclass defaults.
  - We use `datetime.utcnow()` — deprecated in 3.12 but fine in 3.10. Phase 5 may switch to `datetime.now(timezone.utc)`.
- **VALIDATE**: `tests/test_system.py`; smoke: `HydraulicSystem.build_default().tick(0)` returns 6 `ValveState`s with positive flows.

### Task 4: Implement `sim/controllers/belimo_baseline.py` (replace stub)
- **ACTION**: Belimo Energy Valve baseline per PRD §6.
- **IMPLEMENT**:
  ```python
  """Belimo Energy Valve baseline controller. PRD §6."""
  from __future__ import annotations
  from dataclasses import dataclass
  from typing import Dict, List

  from sim.types import ValveCommand, ValveState


  TARGET_DT_C = 5.0       # PRD §4.1 design ΔT
  DEADBAND_C = 0.5        # PRD §6 — within ±0.5°C, hold
  STEP_PCT = 2.0          # PRD §6 — move 2% per tick


  @dataclass
  class BelimoController:
      """Per-valve independent ΔT control. No peer awareness."""

      target_dT_C: float = TARGET_DT_C
      deadband_C: float = DEADBAND_C
      step_pct: float = STEP_PCT

      def step(self, states: List[ValveState]) -> Dict[str, ValveCommand]:
          commands: Dict[str, ValveCommand] = {}
          for s in states:
              if s.dT_C < self.target_dT_C - self.deadband_C:
                  new_pos = max(0.0, s.position_pct - self.step_pct)
              elif s.dT_C > self.target_dT_C + self.deadband_C:
                  new_pos = min(100.0, s.position_pct + self.step_pct)
              else:
                  new_pos = s.position_pct
              commands[s.valve_id] = ValveCommand(position_pct=new_pos)
          return commands
  ```
- **MIRROR**: NAMING_CONVENTION; mirror PRD §6 logic exactly.
- **IMPORTS**: `sim.types`.
- **GOTCHA**:
  - PRD §6 reads ΔT < target → close (reduce position); ΔT > target → open. This is **counterintuitive** at first but correct: low ΔT means too much flow (water leaves too cold), so close. Match PRD direction exactly.
  - Phase 2 controller works only on `position_pct` (0–100) per `ValveCommand`. Conversion to unit interval happens at the system boundary in `HydraulicSystem.set_positions`.
- **VALIDATE**: `tests/test_belimo.py`; under-ΔT → command decreases; over-ΔT → command increases; in-deadband → no change.

### Task 5: Implement `sim/scenarios.py` (replace stub)
- **ACTION**: Scenario loader + steady-state load disturbance.
- **IMPLEMENT**:
  ```python
  """Scenario definitions and load disturbance generators. PRD §4.4."""
  from __future__ import annotations
  import json
  import math
  from dataclasses import dataclass, field
  from pathlib import Path
  from typing import Dict, List


  @dataclass
  class Scenario:
      """A scenario describes per-tick load fractions per valve."""
      name: str
      duration_seconds: int
      base_load_fraction: float
      fluctuation_amplitude: float    # ± fraction (e.g. 0.05 = ±5%)
      fluctuation_period_seconds: int
      valve_ids: List[str] = field(default_factory=list)

      def load_fraction(self, valve_id: str, t_seconds: int) -> float:
          # Sinusoidal per-valve fluctuation; phase shifted per valve so they don't sync.
          phase = (hash(valve_id) % 1000) / 1000.0
          omega = 2.0 * math.pi / self.fluctuation_period_seconds
          delta = self.fluctuation_amplitude * math.sin(omega * t_seconds + phase * 2 * math.pi)
          return max(0.0, self.base_load_fraction + delta)

      @classmethod
      def load(cls, path: Path) -> "Scenario":
          data = json.loads(path.read_text())
          return cls(**data)
  ```
- **MIRROR**: NAMING_CONVENTION; dataclass conventions.
- **IMPORTS**: stdlib only.
- **GOTCHA**: Per-valve phase offset prevents all 6 valves from peaking simultaneously, which is unrealistic and produces zero coordination opportunity.
- **VALIDATE**: `tests/test_scenarios.py`; load fraction stays in `[base - amp, base + amp]`.

### Task 6: Implement `sim/io.py`
- **ACTION**: JSON Lines timeseries writer.
- **IMPLEMENT**:
  ```python
  """Timeseries IO helpers."""
  from __future__ import annotations
  import json
  from dataclasses import asdict, is_dataclass
  from datetime import datetime
  from pathlib import Path
  from typing import Any, Iterable


  def _default(o: Any) -> Any:
      if isinstance(o, datetime):
          return o.isoformat()
      if is_dataclass(o):
          return asdict(o)
      raise TypeError(f"not serializable: {type(o)}")


  def write_jsonl(path: Path, records: Iterable[dict]) -> None:
      path.parent.mkdir(parents=True, exist_ok=True)
      with path.open("w") as f:
          for r in records:
              f.write(json.dumps(r, default=_default) + "\n")
  ```
- **MIRROR**: NAMING_CONVENTION.
- **IMPORTS**: stdlib only.
- **GOTCHA**: Use JSON Lines (one record per line) so the file is append-friendly and stream-parseable. Phase 5 can replace the writer with a SQLite INSERT without changing call sites significantly.
- **VALIDATE**: covered indirectly via `tests/test_engine.py`.

### Task 7: Implement `sim/engine.py` (replace stub) — main CLI
- **ACTION**: Argparse CLI that wires everything together.
- **IMPLEMENT**:
  ```python
  """Main simulation loop. PRD §10 Phase 2 step 6.

  Usage:
      uv run python -m sim.engine --scenario steady_state --mode belimo
  """
  from __future__ import annotations
  import argparse
  from datetime import datetime
  from pathlib import Path
  from typing import List

  from sim.controllers.belimo_baseline import BelimoController
  from sim.io import write_jsonl
  from sim.scenarios import Scenario
  from sim.system import HydraulicSystem


  SCENARIOS_DIR = Path(__file__).resolve().parent.parent / "data" / "scenarios"
  RUNS_DIR = Path(__file__).resolve().parent.parent / "data" / "runs"


  def run(scenario_name: str, mode: str, log_every: int = 300) -> Path:
      if mode != "belimo":
          raise ValueError(f"Phase 2 only supports mode=belimo, got {mode!r}")
      scenario = Scenario.load(SCENARIOS_DIR / f"{scenario_name}.json")
      system = HydraulicSystem.build_default()
      # Sync scenario.valve_ids with system valves if not specified
      if not scenario.valve_ids:
          scenario.valve_ids = list(system.valves.keys())

      controller = BelimoController()
      total_energy_kwh = 0.0
      records: List[dict] = []
      states = system.tick(0)
      print(f"[engine] loaded scenario '{scenario.name}' ({scenario.duration_seconds // 60} min, "
            f"{len(system.valves)} valves)")
      print(f"[engine] mode={mode}, tick=1s, total_ticks={scenario.duration_seconds}")

      for t in range(scenario.duration_seconds):
          # Update coil load fractions from scenario
          for rec in system.valves.values():
              # Coil is frozen — rebuild with new load_fraction
              # (cheap: 6 small dataclasses per tick)
              rec.coil = rec.coil.__class__(
                  design_flow_gpm=rec.coil.design_flow_gpm,
                  design_dT_C=rec.coil.design_dT_C,
                  load_fraction=scenario.load_fraction(rec.valve_id, t),
              )

          # Controller decides positions from previous tick's states
          commands = controller.step(states)
          system.set_positions(commands)
          states = system.tick(t)

          # Pump energy: power [kW] × 1 s = kJ → kWh
          pump_kw = system.pump_power_kw()
          total_energy_kwh += pump_kw * (1.0 / 3600.0)

          # Per-tick record
          records.append({
              "tick": t,
              "pump_kw": pump_kw,
              "pump_head_kpa": system.pump.head_kpa(system.solve_network()),
              "total_flow_gpm": system.solve_network(),
              "valves": [s.__dict__ for s in states],
          })

          if t % log_every == 0:
              print(f"[engine] tick {t:4d}  pump_kw={pump_kw:.2f}  energy_so_far={total_energy_kwh:.3f} kWh")

      # Write output
      RUNS_DIR.mkdir(parents=True, exist_ok=True)
      ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
      out = RUNS_DIR / f"{scenario_name}_{mode}_{ts}.jsonl"
      write_jsonl(out, records)

      mean_dT = sum(s.dT_C for r in records for s in [type("S", (), v) for v in r["valves"]]) / (len(records) * len(system.valves))
      print(f"[engine] complete; total_pump_energy = {total_energy_kwh:.2f} kWh")
      print(f"[engine] mean_dT = {mean_dT:.2f} C")
      print(f"[engine] timeseries written to {out}")
      return out


  def main() -> None:
      p = argparse.ArgumentParser()
      p.add_argument("--scenario", default="steady_state")
      p.add_argument("--mode", default="belimo", choices=["belimo"])
      p.add_argument("--log-every", type=int, default=300)
      args = p.parse_args()
      run(args.scenario, args.mode, log_every=args.log_every)


  if __name__ == "__main__":
      main()
  ```
- **MIRROR**: SCRIPT_SHEBANG NOT needed (invoked as `python -m sim.engine`, sim is already importable). NAMING_CONVENTION. ENGINE_LOOP_PATTERN.
- **IMPORTS**: argparse, datetime, pathlib, plus sim internals.
- **GOTCHA**:
  - `Coil` is `frozen=True` so per-tick load update requires rebuilding the dataclass. Cheap (6 valves).
  - We call `system.solve_network()` three times per tick (for energy, head display, total flow). Cache it in a local variable for production; for Phase 2 the cost is acceptable (~3600 ticks × 3 calls × <1ms each = <11s).
  - The mean_dT computation is messy (we recompute from records to keep the loop simple). Acceptable for Phase 2; Phase 5 will have a proper aggregator.
- **VALIDATE**: `tests/test_engine.py`; running smoke test: `python -m sim.engine --scenario steady_state --mode belimo --log-every 600` completes in <30s wall-clock and produces 8 < kWh < 15.

### Task 8: Create `data/scenarios/steady_state.json`
- **ACTION**: JSON scenario file matching `Scenario.__init__` signature.
- **IMPLEMENT**:
  ```json
  {
    "name": "steady_state",
    "duration_seconds": 3600,
    "base_load_fraction": 0.70,
    "fluctuation_amplitude": 0.05,
    "fluctuation_period_seconds": 300,
    "valve_ids": []
  }
  ```
- **MIRROR**: N/A.
- **GOTCHA**: `valve_ids: []` lets the engine auto-fill from the system's valves. Per PRD §4.4: 70% load, ±5%, 5-minute period.
- **VALIDATE**: `tests/test_scenarios.py` loads it.

### Task 9: Tests
- **ACTION**: Write `test_pump.py`, `test_coil.py`, `test_system.py`, `test_belimo.py`, `test_scenarios.py`, `test_engine.py`.
- **IMPLEMENT** (key cases per file):
  - `test_pump.py`: head decreases as flow rises; `head(0) == static_head`; power=0 at flow=0; raise on negative inputs.
  - `test_coil.py`: at design flow, achieved_dT ≈ design_dT; below design flow with same load → achieved_dT > design (collapse); above design flow → achieved_dT < design (degrade); flow=0 → achieved_dT=0.
  - `test_system.py`: `build_default()` has 6 valves split 3/3; `tick(0)` returns 6 ValveStates with positive flows; sum of valve flows ≈ total flow from `solve_network()`.
  - `test_belimo.py`: ΔT below band → command < current position; ΔT above band → command > current position; ΔT in band → command == current; bounds clamp at 0/100.
  - `test_scenarios.py`: `load()` reads the JSON; `load_fraction` stays in `[base - amp, base + amp]` for many random t values; different valve_ids produce different phases.
  - `test_engine.py`: `run("steady_state", "belimo", log_every=10000)` (silent) returns a path; the output file is JSONL with `duration_seconds` lines; pump energy reported is between 8 and 15 kWh; rejects `mode != "belimo"`.
- **MIRROR**: TEST_STRUCTURE.
- **GOTCHA**: `test_engine.py` is slow (~5–10s). Mark with `@pytest.mark.slow` if a fast tier is desired; for Phase 2 we accept it always-on (the suite is still <15s).
- **VALIDATE**: `uv run pytest` exits 0; all new tests pass.

### Task 10: `scripts/validate_baseline_energy.py`
- **ACTION**: Script that asserts the kWh range and exits non-zero on failure.
- **IMPLEMENT**:
  ```python
  """Validate that the Belimo baseline produces realistic pump energy.

  Per PRD §6: expected ~10 kWh for 60-min steady-state. We accept 8–15 kWh.

  Usage:
      uv run python scripts/validate_baseline_energy.py
  """
  from __future__ import annotations
  import sys
  from pathlib import Path

  sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

  from sim.engine import run  # noqa: E402

  EXPECTED_MIN_KWH = 8.0
  EXPECTED_MAX_KWH = 15.0


  def main() -> int:
      out = run("steady_state", "belimo", log_every=10**9)  # silent
      # Re-read kWh from the printed value isn't ideal; re-run with capture.
      # For now: parse the JSONL and sum pump_kw / 3600.
      import json
      total = 0.0
      with out.open() as f:
          for line in f:
              rec = json.loads(line)
              total += rec["pump_kw"] / 3600.0
      print(f"validated: pump energy = {total:.2f} kWh")
      if not EXPECTED_MIN_KWH <= total <= EXPECTED_MAX_KWH:
          print(f"FAIL: pump energy {total:.2f} outside [{EXPECTED_MIN_KWH}, {EXPECTED_MAX_KWH}] kWh", file=sys.stderr)
          return 1
      return 0


  if __name__ == "__main__":
      sys.exit(main())
  ```
- **MIRROR**: SCRIPT_SHEBANG.
- **GOTCHA**: If energy is out of range, tune `Pump.static_head_kpa` or branch-loss coefficient. Do NOT widen the accepted range — that masks the bug.
- **VALIDATE**: `uv run python scripts/validate_baseline_energy.py` exits 0.

### Task 11: Update README + run final validation
- **ACTION**: Add "Run a scenario" + status update; run full ruff + pytest + validation.
- **IMPLEMENT**: Append to README.md:
  ```markdown
  ## Run a scenario

  ```bash
  uv run python -m sim.engine --scenario steady_state --mode belimo
  uv run python scripts/validate_baseline_energy.py
  ```

  ## Status
  Phase 2 (Simulation Core) — complete. 6-valve system + Belimo baseline + steady-state scenario.
  Next: Phase 3 (three-layer intelligence).
  ```
- **VALIDATE**: `uv run ruff check . && uv run pytest && uv run python scripts/validate_baseline_energy.py`.

---

## Testing Strategy

### Unit Tests

Per Task 9 above. Total expected: 20–25 new tests + Phase 1's 16 = ~40 tests in suite.

### Edge Cases Checklist
- [ ] All valves at 0% position → near-zero flow, pump head ≈ static head, low power
- [ ] All valves at 100% position → near-max flow, pump at low head, high power
- [ ] Mixed branches: A at 30%, B at 90% → branches see same head but very different flows
- [ ] Scenario starts before steady-state convergence (first 10 ticks may be transient) → energy aggregate still bounded
- [ ] Negative flow attempts → ValueError
- [ ] Scenario file missing → FileNotFoundError (acceptable — explicit)
- [ ] Invalid mode → ValueError before any simulation work

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
EXPECT: All tests pass; ≥ 40 total.

### Coverage
```bash
uv run pytest --cov=sim --cov-report=term-missing
```
EXPECT: ≥ 85% on sim/ as a whole (stubs and engine.py main() bring the avg down acceptably).

### End-to-end run
```bash
uv run python -m sim.engine --scenario steady_state --mode belimo
```
EXPECT: Completes in <30s wall-clock, prints summary with kWh in [8, 15], writes JSONL file.

### Baseline-energy assertion
```bash
uv run python scripts/validate_baseline_energy.py
```
EXPECT: Exit 0 with `pump energy = X.XX kWh` where 8 ≤ X ≤ 15.

### Manual Validation
- [ ] Inspect a few lines of the JSONL output — each record has tick/pump_kw/total_flow_gpm/valves
- [ ] mean_dT printed by engine is in [3.5, 5.5] °C
- [ ] No valve position pegged at 0 or 100 for the entire run (would indicate controller saturation)

---

## Acceptance Criteria
- [ ] All tasks 1–11 completed
- [ ] All ruff and pytest checks green
- [ ] 60-min steady-state run produces 8 ≤ pump_energy_kwh ≤ 15
- [ ] JSONL output is valid line-delimited JSON, one record per tick
- [ ] Mean ΔT is within ±1.0 °C of design (4.0–6.0 °C)
- [ ] PRD acceptance criterion #1 partially met (sim runs end-to-end ≥ 60 simulated minutes in belimo mode)

## Completion Checklist
- [ ] Code follows Phase 1 patterns
- [ ] No backwards-compat shims, no feature flags
- [ ] No comments explaining what code does — only why-non-obvious
- [ ] Tests cover happy path + edge cases
- [ ] No hardcoded magic numbers — pull from `sim.types` / `sim.units` / scenario JSON
- [ ] `Coil` and `Pump` are `frozen=True` like `Valve`
- [ ] `ValveState` constructed with all fields explicit (no defaults) per Phase 1 convention

## Risks
| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Network solver doesn't converge for extreme valve positions | Medium | Medium | Bracketed `brentq` with explicit endpoint-return fallback in `solve_network` |
| Pump kWh outside [8, 15] expected range | Medium | High | Tune `Pump.static_head_kpa` (default 50) or branch-loss; validation script flags it |
| `Coil` rebuild every tick is slow | Low | Low | 6 dataclasses × 3600 ticks = 21600 trivial allocations, <100ms total |
| `datetime.utcnow()` deprecation noise on 3.12+ | Low | Low | Pinned to 3.10 in pyproject |
| `scipy` not lock-pinned | Low | Low | `uv.lock` from Phase 2 commit pins it |
| Belimo controller direction sign error (close vs open) | Low | High | Test `test_belimo.py` asserts the PRD-exact direction; visible at code review |

## Notes
- Branch pipe loss is set to a tiny coefficient (effectively zero) for Phase 2. Real branches have meaningful pipe loss; Phase 2.1 can add `branch_pipe_loss_kpa = k * branch_flow^2` and subtract from pump head per-branch. Skipped now to avoid solver complexity.
- Pump is treated as "constant-speed shape, variable operating point on its curve". The "constant-ΔP at remote sensor" Belimo behavior is approximated as the steady-state intersection here. A future enhancement could add an integral controller that drives the pump to a target sensor ΔP.
- The PRD §6 expected outcome is "Belimo baseline pump energy: ~10 kWh; ChillValve: ~8.7 kWh". We're validating only the Belimo arm in Phase 2. The ~13% delta will be measured in Phase 3 once ChillValveController exists.

---

**Confidence Score: 7/10** — Medium complexity. The network solver is the only genuinely tricky piece; everything else is mechanical. Main risk is energy landing outside the [8,15] range on first try and needing pump parameter tuning. The scoped `data/scenarios/steady_state.json` keeps disturbance small enough that the Belimo controller should track stably.
