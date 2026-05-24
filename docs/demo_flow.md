# ChillValve — Demo Flow

A single-scenario, 4-minute autonomous run that exercises all three control
layers (L1 deterministic rules, L2 ML anomaly detection, L3 multi-agent LLM
debate) end-to-end. Designed for judge presentations: pick scenario, click
START, watch the system handle a severe fault without operator intervention.

---

## Summary (TL;DR)

> **Six smart valves coordinate over a real chilled-water hydraulic model.
> When one valve fails, the others negotiate via LLM debate to absorb its
> load — no operator, no central controller, no rewriting of rules.
> Energy use stays below the Belimo market reference throughout.**

| Metric judges should remember | Value |
|---|---|
| Time to detect the fault | < 10 sim-seconds (L2 ML) |
| Time to coordinated response | < 30 sim-seconds (L3 LLM debate) |
| Time to full recovery (ΔT back in band) | ~ 90 sim-seconds |
| Operator actions required | 0 |
| Pump kW vs Belimo datasheet baseline | continuously lower |
| LLM provider | DeepSeek (`deepseek-chat`) via OpenAI-compatible API |

---

## How to Run

### Prerequisites

1. Backend deps installed: `pip install -e .` (project root)
2. Frontend deps installed: `cd frontend && npm install`
3. `.env` at repo root with `DEEPSEEK_API_KEY=sk-...` for live LLM debate
   (without it, debate falls back to deterministic strings — demo still works
   but the LLM transcript is replaced by a fixed allocation message)

### Launch

```bash
# Terminal 1 — backend
cd /Users/limjiale/SCA-ChillValve
python -m uvicorn backend.main:app --port 8000

# Terminal 2 — frontend
cd frontend
npm run dev
```

Open <http://localhost:5173>.

### Drive the demo

1. Dashboard loads — no scenario active yet. Banner says "Pick a scenario above to start."
2. Click the single scenario card **`SCENARIO 1 · FULL RUN · L1+L2+L3`** at
   the top of the dashboard.
3. Backend resets engine, loads `demo_full_run.json`, starts chillvalve mode.
   Engine auto-runs for 240 sim-seconds (~ 4 wall-minutes at 20 Hz).
4. **STOP** to pause mid-run; **RESUME** to continue; **REPLAY** to reset
   and re-run from t=0.

There is no manual stepping. The scenario is fully autonomous — judges
watch it unfold.

---

## The Scenario — `demo_full_run`

A single hydraulic fault on valve B2 (AHU-02), severe enough to trip all
three layers in a clean cascade.

```jsonc
// data/scenarios/demo_full_run.json
{
  "name": "demo_full_run",
  "duration_seconds": 240,
  "base_load_fraction": 0.95,      // high pump demand → big dP swings
  "fluctuation_amplitude": 0.02,
  "fluctuation_period_seconds": 300,
  "fault_target_valve_id": "B2",
  "fault_start_seconds": 12,
  "fault_ramp_seconds": 28,        // slow enough for ML to dwell in uncertain band
  "fault_max_severity": 0.92,      // B2 chokes to 8% capacity
  "disable_debate": false          // L3 enabled
}
```

### Why these numbers

| Knob | Choice | Reason |
|---|---|---|
| `base_load_fraction` 0.95 | Near-max system demand | Pump pushes hard against the restriction → dP at B2 climbs past the L1 failsafe (600 kPa) |
| `fault_max_severity` 0.92 | B2 down to 8% flow capacity | Severe enough to make dP cross 600 kPa → L1 fires reliably |
| `fault_ramp_seconds` 28 | Gradual ramp | ML anomaly_confidence spends ~10s in the uncertain band [0.30, 0.85] → L3 debate gets triggered (instant ramps would skip past) |
| `disable_debate` false | L3 enabled | This is the scenario where the cooperative-agent story plays |

---

## Timeline (sim-seconds)

| t (s) | What's happening | Visible where |
|---|---|---|
| **0 – 12** | Steady-state baseline. All 6 valves nominal. ΔT compliance KPI green. | Schematic green LEDs, sparklines flat |
| **12** | Fault begins ramping on B2 (coil fouling / actuator drift profile) | None yet — fault sub-threshold |
| **15** | B2 capacity at 90%. Flow starts dropping. | B2 sparkline (per-valve chart) begins to dip |
| **20** | B2 capacity at 74%. ML model starts noticing. | L2 panel: first `[anomaly]` entry |
| **25–35** | ML confidence in uncertain band [0.30, 0.85] | **L3 debate stage lights up** — peer valves (B1, B3) speak, leader synthesises allocation. Real LLM transcript streams in (typewriter effect ~45 chars/sec) |
| **30** | B2 capacity at ~40%. Pump still pushing → dP across B2 climbing. | Pump-kW gauge spikes; B1 + B3 sparklines start rising |
| **35–45** | dP at B2 exceeds 600 kPa | **L1 rules panel fires red** — `dP_exceeds_600kPa`. Safety override forces B2 commanded position to 0. Schematic LED on B2 turns red. |
| **40** | B2 at full fault (8% capacity, held) | B2 sparkline floored |
| **40+** | Peers (B1 + B3) absorb the load via the debate-allocated setpoints | B1 + B3 sparklines climb visibly above pre-fault levels |
| **90+** | ΔT compliance KPI recovers to ≥80%. Energy savings vs Belimo widens. | Center KPI card turns green |
| **240** | Engine completes the scenario, stops | "READY" badge in banner |

---

## Why Three Layers

A single-layer controller (Belimo's PICV approach, traditional PID) handles
*one* of the following well, but never all three:

| Need | Belimo PICV | ChillValve approach |
|---|---|---|
| **Microsecond-deterministic safety** (close before pipe burst) | ✅ analog override | ✅ **Layer 1** — pure deterministic rules, no ML, no LLM, microsecond response |
| **Catching faults before they break thresholds** (early warning) | ❌ | ✅ **Layer 2** — Isolation Forest trained on the LBNL Fault Detection Dataset + sim-matched feature subset |
| **Coordinated re-allocation** (don't just close one valve, reshape the whole branch) | ❌ — each valve is independent | ✅ **Layer 3** — multi-agent LLM debate. Peers describe their state, leader synthesises a new allocation for the whole branch |

### What each layer is responsible for

**Layer 1 — Deterministic safety rules** (`sim/layers/layer1_rules.py`):
- 5 rules, hard-coded thresholds
- `dP_exceeds_600kPa` → emergency close
- `flow_exceeds_max_110pct` → reduce position
- `position_out_of_bounds`, `sensor_invalid`, `actuator_unresponsive`
- Fires every tick. Cannot be overridden by L2 or L3. Microsecond response.

**Layer 2 — ML anomaly detection** (Isolation Forest):
- Trained on `LBNL_FDD_Data` + simulator-matched features
- Outputs `anomaly_detected: bool` + `anomaly_confidence: float`
- Catches drift before it breaches L1 thresholds (the "early warning" gap
  that Belimo doesn't fill)

**Layer 3 — Multi-agent LLM debate** (`backend/debate.py`):
- Fires only when L2 confidence is uncertain — band `[0.30, 0.85]`
- 30-second cooldown per branch to bound cost
- Cached on coarse state fingerprint to avoid duplicate LLM calls
- Peer valves each speak once (parallel `asyncio.gather` of 2 LLM calls)
- Elected leader synthesises a JSON allocation + rationale (1 more LLM call)
- Layer 1 still validates the proposed positions — LLM *recommends*, never
  bypasses safety

### Why LLM, not a hand-tuned controller?

The "what should B1 and B3 do when B2 fouls?" decision depends on:
- per-valve current state (flow, ΔT, position, anomaly confidence)
- branch topology
- demand profile across the whole branch
- soft preferences (stay near current position unless justified)

Hand-tuning a controller for every fault permutation × branch configuration
is exactly the kind of N²-rules problem LLMs handle gracefully. Cost is
bounded by cooldown + caching (~$0.02 per 4-minute scenario at flash-lite
rates).

---

## What Judges Should Notice (Demo Talking Points)

While the scenario runs, point out these on-screen:

1. **The cliff** — B2's per-valve sparkline drops visibly. *"That's the fault. No alarms going off yet — the system is still computing what it should be."*
2. **L2 wakes up first** — amber `[anomaly]` line scrolls into the L2 panel. *"That's the Isolation Forest. Sees the drift before any safety rule trips. Belimo has no equivalent."*
3. **The debate stage lights up** — three boxes (B1, B3 peers + B1 leader). Text streams character-by-character. *"This is a live LLM call. The valves are negotiating in real-time. Look at the rationale — B1 is allocating flow to B3 because B3's ΔT is lower."*
4. **L1 fires red** — `dP_exceeds_600kPa`. *"At the same time, the deterministic safety layer hard-closes B2. The LLM doesn't bypass safety — it works around it."*
5. **The recovery** — B1 + B3 sparklines climb to compensate. ΔT compliance KPI flips back to green. *"No operator clicked anything. The valves figured it out themselves."*
6. **Energy savings KPI** — stays positive throughout vs the 20.5 kW Belimo datasheet reference. *"Even mid-fault, we're using less pump energy than the market alternative."*

---

## Architecture (Backend Mechanics)

For follow-up questions about how the demo actually works.

### Tick cadence

`backend/orchestrator.py` runs the engine at **20 Hz** (`TICK_PERIOD_S = 0.05`).
Each tick:

1. Compute load fraction per valve (scenario controls baseline + sine fluctuation)
2. Compute fault severity per valve (scenario controls ramp)
3. Solve hydraulic network → flow, dP, pump head, pump kW
4. Run controller (`ChillValveController`): Layer 1 evaluate → Layer 2 ML → Layer 3 leader-allocated setpoint
5. Broadcast WebSocket snapshot to all subscribers
6. Async-spawn debate task if L2 uncertain (non-blocking, applies on next tick after LLM completes)

### WebSocket messages

Three types over a single WS at `/ws`:

- `state` (every tick): full per-valve snapshot + pump aggregates
- `explanation` (on leader transitions): LLM-narrated event log line
- `debate` (on debate completion): full transcript — peer speeches + leader rationale + allocations

### Scenario control

REST endpoints in `backend/main.py`:

- `POST /scenario/start?name=...&mode=chillvalve` — load JSON, build hydraulic model, start tick loop
- `POST /scenario/pause` / `resume` / `reset`
- `POST /scenario/inject_fault?valve_id=...&severity=...` — runtime override (used by older multi-step storyboards; current single-scenario demo doesn't need it)

### LLM debate flow

```
                 ┌────────────────────────────────────────┐
                 │   _maybe_run_debate(snapshot)          │
                 │   gate: scenario.disable_debate?       │
                 │   gate: any valve.conf in [0.3, 0.85]? │
                 │   gate: cooldown elapsed for branch?   │
                 └─────────────────┬──────────────────────┘
                                   │
                  asyncio.create_task(...)
                                   │
                                   ▼
         ┌─────────────────────────────────────────────────┐
         │  DebateRunner.run(branch, leader, valves, t)    │
         │                                                 │
         │  Phase 1 — parallel peer speeches:              │
         │    await asyncio.gather([                       │
         │      _peer_speech(v) for v in peers             │
         │    ])  ← N LLM calls in parallel                │
         │                                                 │
         │  Phase 2 — leader synthesis:                    │
         │    JSON {"allocations": {...}, "rationale":...} │
         │    ← 1 LLM call                                 │
         │                                                 │
         │  Phase 3 — sanitize:                            │
         │    clamp positions to [0, 100], drop unknown ids│
         └─────────────────┬───────────────────────────────┘
                           │
                           ▼
        Stage allocations in self._debate_overrides
        (next tick's controller.step picks them up)

        Broadcast debate WS message to all subscribers
        (DebateStage component animates the transcript)
```

### Cost control

- **Cooldown**: 30 sim-seconds per branch. Prevents back-to-back debates.
- **Cache**: state hash at coarse resolution (5% position, 0.5°C ΔT, 10 GPM flow, 0.1 confidence). Similar conditions hit cache → no new LLM call.
- **Gate**: only fires inside the uncertain band [0.30, 0.85]. Steady state never calls the LLM.
- Estimated cost per 4-min scenario: ~$0.02 (1 peer-pair debate × 3 LLM calls × ~$0.0003 each) at DeepSeek flash rates.

---

## Files Touched (Reference)

### Backend
- `sim/scenarios.py` — `Scenario` dataclass, `disable_debate` field
- `sim/layers/layer1_rules.py` — 5 deterministic rules
- `sim/controllers/chillvalve.py` — wires L1 + L2 + L3 setpoints into per-tick control
- `backend/orchestrator.py` — async engine loop, debate gating, WS fan-out
- `backend/explainer.py` — DeepSeek-backed leader-change narration
- `backend/debate.py` — DeepSeek-backed multi-agent debate runner
- `data/scenarios/demo_full_run.json` — the single demo scenario

### Frontend (`frontend/src/components/v5/`)
- `scenarios.js` — single scenario metadata + `runScenario()` helper
- `ScenarioPicker.jsx` — top-of-dashboard scenario card
- `ScenarioBanner.jsx` — active scenario detail + watch-for checklist
- `Schematic.jsx` — live P&ID, valve LEDs, flow animation
- `FlowChart.jsx` — 6 per-valve sparkline cards (left sidebar)
- `KpiTrio.jsx` — ΔT compliance, energy vs Belimo, active anomalies
- `DebateStage.jsx` — multi-agent LLM transcript with typewriter streaming
- `EventLog.jsx` — filterable log; rendered 3× (one per layer) in right sidebar
- `ValveTable.jsx` — per-valve numbers table
- `ControlBar.jsx` — START / STOP / REPLAY

---

## Failure Modes & Graceful Degradation

| Failure | Result |
|---|---|
| No `DEEPSEEK_API_KEY` set | L3 debate disabled, controller falls back to deterministic Layer-3 allocation. Banner still shows L1+L2+L3 expected, but DebateStage stays empty. |
| DeepSeek API returns malformed JSON | Single warning logged, that debate skipped, controller uses deterministic fallback for that tick. |
| DeepSeek rate-limited / quota exceeded | Single warning, subsequent debates suppressed for the rest of the run. L1 + L2 still operate normally. |
| Backend WebSocket disconnects | Frontend auto-reconnects with exponential backoff [1, 2, 4, 10] seconds. |
| Backend not running at all | Dashboard still renders (with placeholder zeros) — connection badge shows red. |
| Frontend disconnects mid-debate | Reconnect → new WS subscriber starts fresh; in-flight debates not replayed (queue is per-subscriber). |

---

## Common Judge Questions

For the full Q&A defense sheet see `docs/qa_defense.md`. Specific to the demo:

**Q: Is the LLM debate real or scripted?**
A: Real. `backend/debate.py:248-266` calls `client.chat.completions.create(...)` against DeepSeek's API. If you remove the API key, the DebateStage stays empty — the controller has no scripted fallback that produces transcripts. The typewriter streaming on the frontend is a visual replay; the LLM calls themselves happen in parallel on the backend in ~5 seconds wall-clock.

**Q: Why does the per-valve flow chart not show smooth lines?**
A: 20 Hz ticks, 120-tick rolling window (~6 wall-seconds). Each pixel is one engine tick. The "noise" is real fluctuation from the scenario's sine load + the controller's per-tick response.

**Q: Why is energy savings calculated against a static number?**
A: We can't run two physics models in parallel on the same backend. The 20.5 kW Belimo reference is from Belimo EV/EPIV product datasheets for an equivalent 5MW DC chilled-water loop at design conditions. Constant defined in `frontend/src/lib/valveConfig.js`.

**Q: How would this scale to 60 valves?**
A: Debate fan-out scales as O(N) per branch (currently 2-3 valves per branch). Cooldown is per-branch, so a 10-branch system fires at most 10 debates per 30-second window. Cache hit rate climbs with N (more state similarity). At 60 valves we'd still expect <$1/hour LLM spend.
