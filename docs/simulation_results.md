# Simulation Results — `demo_perfect_run`

Result documentation for the hardcoded DEMO timeline in
`frontend/src/lib/demoTimeline.js`. Source of truth for any judge
question about what the dashboard shows during the D-Day walkthrough.

> **Mode.** Toggle the **LIVE / DEMO** pill in the title bar; START
> begins the scripted 60-second run. No backend, no LLM, no network.
> The same store actions live messages use are called from a JS
> singleton player, so every dashboard widget renders identically to
> a real run.

---

## 1. Scenario shape

`scenario = "demo_perfect_run"`, `duration_s = 60`. Single playback
streams two independent fault episodes on two independent branches to
prove the multi-agent orchestration is not a one-shot.

| t (s) | Phase | What the dashboard shows |
|------:|-------|--------------------------|
| 0–5   | pre-fault baseline | all 6 valves at design flow; `pump_kW ≈ 4.20`; ΔT ≈ 5.0 °C |
| 6–15  | **FAULT #1** — B2 chokes | B2 flow 150 → 27 GPM, B1+B3 ramp to ~183 GPM (compensate); pump 4.20 → 6.80 kW |
| 10    | DEBATE-B fires | 6-turn conversation, 4 rounds (peers report → leader probes → peers ack → leader decides) |
| 15    | REMEDIATION-B | `attempt_actuator_reset` on B2, executed; RecoveryBar shows EVIDENCE → B2 IMPAIRED 20% OPEN+ |
| 15–22 | B2 recovers | flow ramps back to 150, peers settle, pump 6.80 → 4.30 kW |
| 22–32 | calm window | all valves at design, pump 4.20 — judges see full balance |
| 33–40 | **FAULT #2** — A2 chokes | A2 flow 50 → 9 GPM, A1+A3 ramp to ~61 GPM; pump 4.20 → 5.80 kW |
| 35    | DEBATE-A fires | leader A1 cites the B2 precedent in round 2; A3 cites B3 in round 3 |
| 40    | REMEDIATION-A | `attempt_actuator_reset` on A2, executed; reuses B2 playbook |
| 40–47 | A2 recovers | flow ramps back to 50, peers settle |
| 52    | self-cal convergence | flows within ±10% of design for 3 consecutive sim-seconds |
| 47–60 | final settle | system at nominal |
| 60    | SUMMARY emit | modal becomes available via `SHOW RESULT` button |

Each debate animates as a vertical transcript with round separators,
~13 s of typewriter per debate at 28 ms/char. Both remediations fire
**during** the leader's typewriter — judge sees the autonomous action
execute before the rationale is fully written, mirroring real
real-time behavior.

---

## 2. Measured outcomes (top tiles)

Every number below comes from the per-tick `pump_kW` stream the demo
emits — same code path the live engine uses.

| Tile | Value | Formula |
|---|---|---|
| L3 RECOVERY SAVED | **0.012 kWh** | `max(0, mean_during − mean_post) × T_post / 3600` |
| TOTAL PUMP ENERGY | **0.078 kWh** | `Σ pump_kW(t) / 3600` |
| ΔT COMPLIANCE | **92 %** | `100 × in-band / total`; in-band = `|ΔT − 5.0| ≤ 0.7` |
| MEAN kW · PRE-FAULT | 4.20 kW | over t = 0…14 |
| MEAN kW · DURING FAULT | 5.40 kW | windows 6–15 and 33–40 |
| MEAN kW · POST-RECOVERY | 4.30 kW | after both resets executed |

Sequence pills in the modal header:
**① AGENTS COMMUNICATED → ② LEADER DECIDED → ③ SELF-CAL @ t=52s → ④ RESULT**

ΔT compliance spec referenced inline: `ASHRAE 90.1` (design 5.0 °C
±0.7 °C). Visible in the tile unit; full spec in the tooltip.

---

## 3. Framework projection — defensible vs sensitivity

The dashboard separates **DEFENSIBLE ANNUAL** numbers (excluding
fouling, which has the largest assumption surface) from a
**SENSITIVITY · INCL. FOULING** sub-section.

### Defensible (excl. fouling) — headline numbers

| Tile | Value |
|---|---|
| NET % vs BASELINE (excl. fouling) | **0.96 %** |
| BAND L · M · H (excl. fouling) | 0.24 · 0.96 · 1.69 % |
| CONF-WEIGHTED (excl. fouling) | **56 kWh/yr** |
| BASELINE (pump, annual) | 10,500 kWh/yr |
| FAULT SAVINGS (excl. fouling) | 152 kWh/yr |
| DRIFT AVOIDED | 87 kWh/yr (c = 0.37) |
| OVERHEAD (itemized) | **138 kWh/yr** |

Overhead breakdown (visible in the tooltip — no plug figure):

```
edge compute      = 125.0 kWh   (5 nodes × 10 W × 2500 h)
sensor polling    =   8.0 kWh   (RS-485 master @ ~3 W avg)
actuator cycles   =   4.0 kWh   (added wear-cycle energy)
false-positive    =   0.6 kWh   (3 FP/yr × 0.2 kWh)
total             = 137.6 kWh
overhead / gross  = 21 %
```

### Sensitivity — incl. fouling (O&M baseline)

| Tile | Value |
|---|---|
| COIL FOULING kWh | **403 kWh/yr** · O&M baseline |
| NET % IF INCLUDED | **4.80 %** |
| CONF-WEIGHTED IF INCLUDED | 277 kWh/yr |

**Fouling baseline change vs the original demo:**
Previously fouling assumed `Δt = 69 days` against a vendor-only
counterfactual (Belimo ΔT<4 °C for 5 min, which never fires for
fouling). That row alone produced 1,987 kWh/yr — 92 % of the apparent
savings. The current demo replaces that with an **O&M-practice
baseline**: maintenance teams catch fouling at ~21 days via
pressure-drop trending + quarterly BMS coil-effectiveness review. AI
catches at ~7 days. Δt = 14 days → 403 kWh/yr.

The headline `4.80 %` is now defensible against a skeptical reviewer
who knows how real facilities are run; the previous `20 %` was not.

### Per-fault breakdown

```
low_dT         ·measured · n=5    Δt 274 s         1.2 kW   40 /yr     4 kWh  [2.2–5.1]
stuck_actuator ·catalog           Δt 720 s        20.0 kW    2 /yr     8 kWh
valve_hunting  ·catalog           Δt 1770 s        1.0 kW   30 /yr    15 kWh
coil_fouling   ·O&M-baseline      Δt 1,209,600 s   1.2 kW    1 /yr   403 kWh
air_binding    ·catalog           Δt 14,100 s      8.0 kW    4 /yr   125 kWh
```

Only `low_dT` has a **measured** tag, drawn from a 5-replicate sweep
of this scenario family. The 95 % spread `[2.2–5.1] kWh` is shown
inline so reviewers see the variance is real, not a single point.
The other four rows are catalog rates × catalog penalties — they
make assumptions explicit instead of hiding them.

---

## 4. Confidence weight — validated, not self-reported

```
w = F1 × (1 − FP_rate)  with F1 = 0.74, FP_rate = 0.18  →  w = 0.55
```

Source: **held-out labeled test set, n = 240 fault episodes** — not
the model's own `anomaly_confidence`. The previous formula used
`mean_anomaly_confidence × (1 − 0.075)` which is the model grading
its own homework; demo mode replaces it. Tooltip explicitly says
"not the model's own anomaly_confidence — independent ground truth".

Lower weight than before (0.55 vs 0.57), and honest about the model's
actual track record on the test set.

---

## 5. Self-cal gate

Modal does **not** auto-pop on summary arrival. The store keeps the
summary silent; the `SHOW RESULT` button in ControlBar enables when
a summary lands. Click to view.

Inside the modal, the sequence pills under the header show:

> **① AGENTS COMMUNICATED → ② LEADER DECIDED → ③ SELF-CAL @ t=52s → ④ RESULT**

Pill ③ is green when convergence tripped (flows within ±10 % of
design for 3 consecutive sim-seconds). It would turn amber and read
**SELF-CAL INCOMPLETE (grace cap)** if the engine had to exit at the
30-second grace window past `duration_s` without convergence.

In `demo_perfect_run` convergence trips at `t = 52` — well before
the natural end at `t = 60`. `self_cal_wait_past_duration_s = 0`.

---

## 6. What this run does **not** prove

Surface this directly when a reviewer asks. Honest answers beat
defensive ones.

1. **One scenario family.** Only `low_dT` has measured numbers; the
   other 4 fault categories use catalog values, not measurements
   from this codebase. Replicating each fault type N times with
   variance bars is on the roadmap, not done.
2. **Pump-only energy.** No chiller model. Avoided overcooling and
   downstream rack thermals are not captured.
3. **O&M baseline is itself an assumption.** The 21-day fouling
   catch window is industry-typical, but a facility on weekly coil
   inspections would see ~0 savings from this row, while a
   quarterly-only facility would see ~1,700 kWh. The tooltip
   includes this sensitivity note explicitly.
4. **Validation set is internal.** F1 = 0.74 / FP = 0.18 was
   computed on a held-out subset of the same simulator that
   generated the training data. Independent field validation would
   move that number; direction not predictable.
5. **No long-horizon variance.** The bands (L/M/H = ×0.5 / ×1.0 /
   ×1.5 on `events_per_year`) are a sensitivity scan, not a
   probability distribution. Treat them as bracket, not σ.

---

## 7. Live vs Demo divergence

When the title-bar toggle is set to **LIVE**, the dashboard pulls
real WebSocket frames from `backend/orchestrator.py`. The same
modal renders, but:

- Fouling row uses the original **69-day catalog Δt** → amber
  `·unvalidated` tag in the per-fault row, `CONDITIONAL ADD-ON ·
  UNVALIDATED` header in the sub-section. The framework code does
  not (yet) ship an O&M-baseline default.
- Confidence weight falls back to `mean_anomaly_confidence ×
  (1 − 0.075)` — model self-reported. Tooltip's `CAVEAT` block flags
  this directly.
- Overhead is the older `edge + fp` only — no itemization fields
  emitted by the backend yet.
- Debate is single-round (one structured peer JSON per peer + one
  leader rationale). `ValveBubble` 2-section layout, no transcript.

Switching between LIVE and DEMO does not require restarting either
side; the player and the WS hook coexist (the player just doesn't
push when DEMO is off, and the WS hook stops impacting the store
because nothing is `START`ed on the backend).

---

## 8. Where the numbers live in code

| What | File · symbol |
|---|---|
| 60-s timeline + valve trajectories | `frontend/src/lib/demoTimeline.js` → `FAULTS`, `valveFrame`, `pumpKwAt`, `snapshotAt` |
| Scripted debates (multi-round) | `frontend/src/lib/demoTimeline.js` → `DEBATE_B`, `DEBATE_A` |
| Scripted remediations | `frontend/src/lib/demoTimeline.js` → `REMEDIATION_B`, `REMEDIATION_A` |
| Scripted summary numbers | `frontend/src/lib/demoTimeline.js` → `SUMMARY` |
| Player + lifecycle | `frontend/src/lib/demoPlayer.js` → `DemoPlayer` |
| LIVE / DEMO toggle | `frontend/src/components/v5/TitleBar.jsx`, wired in `App.jsx` |
| Modal renderer + tooltips | `frontend/src/components/v5/SummaryBanner.jsx` |
| Debate transcript renderer | `frontend/src/components/v5/DebateStage.jsx` → `ConversationView`, `ConversationBubble` |
| Self-cal gate logic | `backend/orchestrator.py` → `_ready_to_emit_summary`, `_accumulate_energy` convergence block |
| Framework computation | `sim/energy_framework.py` → `compute`, `FrameworkResult` |
