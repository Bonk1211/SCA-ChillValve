# Plan: Dashboard Credibility Fixes (Pre-D-Day Audit Response)

## Summary
Three dashboard bugs surfaced by an engineering audit must be fixed before judges see the demo. One is a credibility killer (a savings KPI that contradicts our own PRD); two are visual-state inconsistencies where the dashboard's own panels disagree with each other.

## User Story
As a judge evaluating the demo, I want every panel on the dashboard to be internally consistent with every other panel and with the project's PRD, so that I trust the system enough to score it.

## Problem → Solution
- **Now:** Energy card shows +71.8% savings vs Belimo (datasheet ratio) while PRD §6 documents +0.3% measured savings; anomaly KPI shows 0/6 while L3 panel marks 3+ valves IMPAIRED; valve LEDs glow green while the same valves are flagged impaired in L3.
- **After:** Energy card removed (replaced with honest Pump Power readout); anomaly count and LED color both align with the same "impaired" heuristic L3 uses, so the dashboard tells one coherent story.

## Metadata
- **Complexity:** Small (3 files, ~150 lines)
- **Source PRD:** N/A — driven by free-form audit report
- **PRD Phase:** N/A
- **Estimated Files:** 3 frontend (KpiTrio.jsx, Schematic.jsx, ValveTable.jsx); 1 new helper module (impairment.js); 1 config trim (valveConfig.js)

---

## UX Design

### Before (current state — has the three bugs)
```
┌──────────────────────────────────────────────────────────────┐
│ ΔT COMPL    │ ACTIVE ANOMALIES │ ENERGY vs BELIMO   │ PUMP   │
│ 100% ✓      │ 0 / 6   ⚠ wrong  │ +71.8% ⚠ killer    │ 5.78kW │
│ 5.0±0.7°C   │ all nominal      │ 5.78 vs 20.5 Belimo│ 228kPa │
└──────────────────────────────────────────────────────────────┘
   Schematic:  A1●  A2●  A3●     B1●  B2●  B3●    ← all green
                       ↑ but L3 says A2 IMPAIRED          ↑ but L3 says B2/B3 IMPAIRED
```

### After (fixed)
```
┌──────────────────────────────────────────────────────────────┐
│ ΔT COMPL    │ ACTIVE ANOMALIES │ PUMP POWER         │ TOTAL  │
│ 100% ✓      │ 3 / 6   ⚠ matches│ 5.78 kW            │ FLOW   │
│ 5.0±0.7°C   │ L3 panel exactly │ 28% of 20.5kW name │ 614 GPM│
└──────────────────────────────────────────────────────────────┘
   Schematic:  A1●  A2◐  A3●     B1●  B2◐  B3◐    ← amber on L3-impaired
                       ↑ matches L3 IMPAIRED label      ↑ matches L3
```

### Interaction Changes
| Touchpoint | Before | After | Notes |
|---|---|---|---|
| KPI strip card 3 | "ENERGY vs BELIMO +71.8%" | "PUMP POWER 5.78 kW · 28% nameplate" | Honest, no cross-product claim |
| KPI strip card 2 | "ACTIVE ANOMALIES 0/6" | "ACTIVE ANOMALIES 3/6" (when valves impaired) | Aligns with L3 panel |
| Schematic LED | always green when `anomaly_detected=False` | amber when L3-impaired heuristic true | Aligns with L3 panel |
| Valve table dot | same as schematic | same as schematic | Same fix, two render sites |

---

## Mandatory Reading

| Priority | File | Lines | Why |
|---|---|---|---|
| P0 | `frontend/src/components/v5/KpiTrio.jsx` | 1-130 | All three KPI cards live here |
| P0 | `frontend/src/components/v5/Schematic.jsx` | 44-80 | LED color logic for hydraulic schematic |
| P0 | `frontend/src/components/v5/ValveTable.jsx` | 58-140 | LED color logic for table dot |
| P0 | `frontend/src/lib/valveConfig.js` | 1-30 | `designFlowGpm` per valve + `BELIMO_REFERENCE_KW` to delete |
| P1 | `backend/debate.py` | 350-365 | Existing "impaired" heuristic to mirror in JS |
| P1 | `backend/models.py` | 50-65 | `ValveSnapshot` shape — confirms `anomaly_detected`, `anomaly_confidence`, `flow_gpm` all in WS payload |
| P2 | `backend/orchestrator.py` | 220-250 | Context: where `anomaly_detected` is set; do NOT change backend threshold |

## External Documentation

None — purely internal frontend fix using already-exposed snapshot fields.

---

## Patterns to Mirror

### IMPAIRED_HEURISTIC (Python source-of-truth — mirror in JS)
```python
# SOURCE: backend/debate.py:354-358
design_flow_gpm = 50 if branch_id == "A" else 150
impaired = (
    valve["flow_gpm"] < 0.6 * design_flow_gpm
    or valve["anomaly_confidence"] > 0.4
)
```

### LED_COLOR_TIER (current — to extend, not replace)
```javascript
// SOURCE: frontend/src/components/v5/Schematic.jsx:44-48
const stateColor = valve.safety_override_active
  ? "#f87171"  // red — Layer 1 fired
  : valve.anomaly_detected
  ? "#fbbf24"  // amber — Layer 2 detected
  : "#34d399"; // green — nominal
```

### KPI_CARD_STRUCTURE
```javascript
// SOURCE: frontend/src/components/v5/KpiTrio.jsx:82-90
<KpiBigCard
  label="ACTIVE ANOMALIES"
  value={anomalies.toString()}
  unit={`/ ${totalValves}`}
  sub={anomalies === 0 ? "all valves nominal" : "Layer 2 ML detection"}
/>
```

### COUNTER_PATTERN
```javascript
// SOURCE: frontend/src/components/v5/KpiTrio.jsx:63
const anomalies = valves.filter((v) => v.anomaly_detected).length;
```

---

## Files to Change

| File | Action | Justification |
|---|---|---|
| `frontend/src/lib/impairment.js` | CREATE | Single source of truth for the "impaired" heuristic, used by KPI counter and both LED render sites |
| `frontend/src/components/v5/KpiTrio.jsx` | UPDATE | Replace Energy card; rewire anomaly counter to shared heuristic |
| `frontend/src/components/v5/Schematic.jsx` | UPDATE | Bind LED color to shared heuristic instead of `anomaly_detected` alone |
| `frontend/src/components/v5/ValveTable.jsx` | UPDATE | Bind dot LED to same shared heuristic |
| `frontend/src/lib/valveConfig.js` | UPDATE | Remove orphan `BELIMO_REFERENCE_KW` after KPI replacement |
| `frontend/src/lib/__tests__/impairment.test.js` | CREATE | 6 unit cases for the heuristic |

## NOT Building

- Live Belimo shadow simulator (audit's Option B). Multi-hour build; out of scope. Slide deck + `--mode compare` CLI remain the place for any controller comparison.
- Backend threshold changes to `anomaly_detected`. Other code paths rely on the current definition; do not perturb for a UI-only display issue.
- Bernoulli equation closure check (audit's "What's Suspicious But Probably OK"). Solver is authoritative; out of scope.
- Pump power conversion-factor re-derivation. Numbers within PRD §4.4 range; out of scope.

---

## Step-by-Step Tasks

### Task 1: Create shared impairment heuristic module
- **ACTION:** Create `frontend/src/lib/impairment.js` exporting `isImpaired(valve)` matching backend `debate.py` logic.
- **IMPLEMENT:**
  ```javascript
  import { VALVE_BY_ID } from "./valveConfig";

  // Mirror of backend/debate.py:_peer_speech's impaired check.
  // Frontend single source of truth for "is this valve in trouble" — used
  // by both the ACTIVE ANOMALIES KPI and the schematic/table LED color.
  // Reason: the L3 debate panel labels valves IMPAIRED on a lower confidence
  // threshold (>0.4) than the backend's anomaly_detected boolean (>0.5).
  // The dashboard would contradict itself if the KPI counter and the L3
  // panel used different definitions.
  export function isImpaired(valve) {
    if (!valve) return false;
    const cfg = VALVE_BY_ID[valve.valve_id];
    const designFlow = cfg?.designFlowGpm ?? 50;
    return (
      valve.flow_gpm < 0.6 * designFlow ||
      valve.anomaly_confidence > 0.4
    );
  }
  ```
- **MIRROR:** IMPAIRED_HEURISTIC pattern above
- **IMPORTS:** `import { VALVE_BY_ID } from "./valveConfig"`
- **GOTCHA:** Don't compute design flow from the snapshot — backend doesn't send `design_flow_gpm`. Read from static `VALVE_BY_ID`.
- **VALIDATE:** `isImpaired({valve_id: "B2", flow_gpm: 68, anomaly_confidence: 0.49})` returns `true`.

### Task 2: Replace Energy vs Belimo card with Pump Power card
- **ACTION:** Delete `BELIMO_REFERENCE_KW` import + the `savingsPct` calc + the "ENERGY vs BELIMO" card. Add a "PUMP POWER" card.
- **IMPLEMENT:**
  - Delete the lines computing `savingsPct` (currently `KpiTrio.jsx:81-86`).
  - Remove `BELIMO_REFERENCE_KW` from imports.
  - Add local constant at top of file: `const PUMP_NAMEPLATE_KW = 20.5; // pump rated draw — NOT a Belimo comparison`.
  - Replace the card JSX with:
    ```jsx
    <KpiBigCard
      label="PUMP POWER"
      value={hasData ? currentKw.toFixed(2) : "—"}
      unit={hasData ? "kW" : ""}
      sub={
        hasData
          ? `${((currentKw / PUMP_NAMEPLATE_KW) * 100).toFixed(0)}% of ${PUMP_NAMEPLATE_KW} kW nameplate`
          : "awaiting data"
      }
    />
    ```
- **MIRROR:** KPI_CARD_STRUCTURE pattern above
- **IMPORTS:** Remove `BELIMO_REFERENCE_KW` from the `valveConfig` import. No new imports needed.
- **GOTCHA:** Do NOT just relabel "vs Belimo" → "vs nameplate" while keeping the same constant — that's a rename, not a methodology change. The new card is a pump-utilization gauge (% of pump rating), conceptually different from a controller-comparison claim.
- **VALIDATE:** Dashboard card 3 reads e.g. "PUMP POWER 5.78 kW · 28% of 20.5 kW nameplate". No mention of Belimo.

### Task 3: Rewire ACTIVE ANOMALIES counter to use shared heuristic
- **ACTION:** In `KpiTrio.jsx`, change the counter from `valves.filter(v => v.anomaly_detected)` to `valves.filter(isImpaired)`.
- **IMPLEMENT:**
  ```javascript
  // BEFORE (KpiTrio.jsx:63):
  const anomalies = valves.filter((v) => v.anomaly_detected).length;
  // AFTER:
  const anomalies = valves.filter(isImpaired).length;
  ```
  Also update the `sub` text so it doesn't lie when amber LEDs are showing:
  ```jsx
  sub={anomalies === 0 ? "all valves nominal" : `${anomalies} valve${anomalies > 1 ? "s" : ""} below design`}
  ```
- **MIRROR:** COUNTER_PATTERN — same `.filter(...).length` shape, just swap the predicate
- **IMPORTS:** `import { isImpaired } from "../../lib/impairment"`
- **GOTCHA:** The L3 panel already uses the same heuristic via the structured speech `status: "impaired"|"nominal"` field. After this change, the KPI counter aligns with the count of IMPAIRED chips in the L3 panel.
- **VALIDATE:** During demo_full_run with B2 fault active, KPI shows ≥1/6 (often 3/6 once peers compensate). Never 0/6 while any L3 panel shows IMPAIRED.

### Task 4: Rewire Schematic LED color to use shared heuristic
- **ACTION:** Change the middle tier of the LED color condition from `valve.anomaly_detected` to `isImpaired(valve)`. Red `safety_override_active` tier stays on top.
- **IMPLEMENT:**
  ```javascript
  // BEFORE (Schematic.jsx:44-48):
  const stateColor = valve.safety_override_active
    ? "#f87171"
    : valve.anomaly_detected
    ? "#fbbf24"
    : "#34d399";
  // AFTER:
  const stateColor = valve.safety_override_active
    ? "#f87171"  // red — Layer 1 emergency override
    : isImpaired(valve)
    ? "#fbbf24"  // amber — flow below design OR L2 confidence > 0.4
    : "#34d399"; // green — nominal
  ```
- **MIRROR:** LED_COLOR_TIER pattern — preserve the three-tier ladder, widen only the middle predicate
- **IMPORTS:** `import { isImpaired } from "../../lib/impairment"`
- **GOTCHA:** Red tier MUST stay top of ladder — an impaired valve that also triggered Layer 1 must show red, not amber.
- **VALIDATE:** Watch B2 during fault ramp. LED green → amber BEFORE L1 dP rule fires, then amber → red when L1 fires.

### Task 5: Rewire ValveTable LED color the same way
- **ACTION:** Identical change to `ValveTable.jsx:58-60`.
- **IMPLEMENT:**
  ```javascript
  // BEFORE:
  const isAnomaly = v.anomaly_detected;
  const isFault = v.safety_override_active;
  const stateColor = isFault ? "#f87171" : isAnomaly ? "#fbbf24" : "#34d399";
  // AFTER:
  const isAnomaly = isImpaired(v);
  const isFault = v.safety_override_active;
  const stateColor = isFault ? "#f87171" : isAnomaly ? "#fbbf24" : "#34d399";
  ```
- **MIRROR:** Same as Task 4
- **IMPORTS:** `import { isImpaired } from "../../lib/impairment"`
- **GOTCHA:** `isAnomaly` is used twice in ValveTable — LED color AND row's text color/style. Confirm both update by grepping for `isAnomaly` after the edit.
- **VALIDATE:** Dot in table row matches schematic LED color per valve, every tick.

### Task 6: Remove orphan `BELIMO_REFERENCE_KW` from valveConfig
- **ACTION:** Delete `BELIMO_REFERENCE_KW` export + its block comment from `valveConfig.js`.
- **IMPLEMENT:** Delete `valveConfig.js:18-23` (block comment + export line).
- **MIRROR:** N/A (deletion)
- **IMPORTS:** Verify zero remaining consumers: `grep -rn "BELIMO_REFERENCE_KW" frontend/src`. Should return zero after Task 2.
- **GOTCHA:** If any other file surfaces a Belimo savings number, find + remove. Demo's only Belimo comparison lives in slide deck + `--mode compare` CLI.
- **VALIDATE:** `npm run build` passes with no warnings.

### Task 7: Add unit tests for `isImpaired`
- **ACTION:** Create `frontend/src/lib/__tests__/impairment.test.js` mirroring the existing `useDashboardStore.test.js` shape.
- **IMPLEMENT:** 6 cases per Testing Strategy table below. Use Vitest's `describe`/`it`/`expect` API.
- **MIRROR:** Look at `frontend/src/store/__tests__/useDashboardStore.test.js` for setup pattern.
- **IMPORTS:** `import { describe, it, expect } from "vitest"; import { isImpaired } from "../impairment";`
- **GOTCHA:** Test with both a known valve_id ("B2" → 150 design) AND an unknown one ("X9" → default 50 design) to confirm fallback path.
- **VALIDATE:** `npm test -- --run` shows 6 new passes alongside existing 12.

---

## Testing Strategy

### Unit Tests

| Test | Input | Expected | Edge Case? |
|---|---|---|---|
| `isImpaired` low flow on branch B | `{valve_id: "B2", flow_gpm: 68, anomaly_confidence: 0.1}` (45% of 150) | `true` | No |
| `isImpaired` high confidence | `{valve_id: "A2", flow_gpm: 48, anomaly_confidence: 0.5}` (96% of 50) | `true` | No |
| `isImpaired` both triggers | `{valve_id: "B2", flow_gpm: 30, anomaly_confidence: 0.6}` | `true` | No |
| `isImpaired` neither | `{valve_id: "A1", flow_gpm: 48, anomaly_confidence: 0.1}` | `false` | No |
| `isImpaired` null | `null` | `false` | Yes |
| `isImpaired` unknown id falls back to 50 design | `{valve_id: "X9", flow_gpm: 10, anomaly_confidence: 0}` | `true` (10 < 0.6×50) | Yes |

### Edge Cases Checklist
- [x] Empty input → null test
- [x] Invalid types → null test
- [ ] Concurrent access → N/A (pure function)
- [ ] Network failure → N/A
- [ ] Permission denied → N/A

---

## Validation Commands

### Static Analysis
```bash
cd /Users/limjiale/SCA-ChillValve/frontend && npm run build
```
EXPECT: Build succeeds, no unused-export or unresolved-import warnings.

### Unit Tests
```bash
cd /Users/limjiale/SCA-ChillValve/frontend && npm test -- --run
```
EXPECT: All existing tests pass + new `impairment.test.js` adds 6 passing cases (total 18).

### Manual Validation (Demo Run)
- [ ] Start backend + frontend, run `demo_full_run` scenario
- [ ] t ≈ 0–10s (pre-fault): KPI shows ACTIVE ANOMALIES 0/6, all LEDs green, PUMP POWER card shows a percentage of nameplate
- [ ] t ≈ 20–40s (fault ramping): B2 LED green → amber BEFORE L1 dP rule fires
- [ ] t ≈ 40s+ (L1 trip): B2 LED amber → red
- [ ] At any L3 debate firing: every valve labeled IMPAIRED in L3 panel has amber-or-red LED in schematic AND non-green dot in table
- [ ] At no point: ACTIVE ANOMALIES KPI says "0/6" while any L3 panel shows IMPAIRED
- [ ] At no point: any card on the dashboard says "Belimo" or "+71.8%" or any percent-savings claim

### Cross-document Validation
- [ ] `grep -rn "BELIMO_REFERENCE_KW\|+71.8\|vs Belimo\|vs BELIMO" frontend/src` → zero hits
- [ ] `grep -rn "71.8\|savings" frontend/src` → zero hits (or only inside unrelated test fixtures)
- [ ] PRD v2 §6 reads consistently with the new dashboard (PRD: +0.3% measured under steady state via `--mode compare`; dashboard: no comparison claim at all — pump utilization gauge only).

---

## Acceptance Criteria
- [ ] Tasks 1–7 completed
- [ ] All validation commands pass
- [ ] New `impairment.test.js` covers all 6 cases
- [ ] No type errors / build warnings
- [ ] Demo run shows no contradictions between KPI counter, L3 panel, and LED color
- [ ] Dashboard contains zero references to "Belimo" or any savings percentage

## Completion Checklist
- [ ] Code follows discovered patterns (KPI_CARD_STRUCTURE, LED_COLOR_TIER preserved)
- [ ] Single source of truth for "impaired" lives in `impairment.js`
- [ ] No duplicated heuristic logic across KpiTrio, Schematic, ValveTable
- [ ] No hardcoded design-flow values in `impairment.js` — reads from VALVE_BY_ID
- [ ] No backend changes (preserves stable `anomaly_detected` semantics for L3 trigger code)
- [ ] PRD §6 narrative still defensible — slide deck remains the place for controller comparison

## Risks
| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Backend `anomaly_detected` later changed to also use 0.4 | Low | Frontend logic becomes redundant but still correct | Doc in `impairment.js` says frontend intentionally mirrors backend; revisit if backend changes |
| Judge asks "why no Belimo comparison?" during Q&A | Medium | Brief explanation needed | Prepared answer: "the live dashboard is honest about what it can measure in real time; controller comparison lives in our `--mode compare` benchmark (PRD §6) where we have a controlled apples-to-apples run, not a datasheet ratio" |
| `designFlowGpm` per-valve config drifts from backend `sim/system.py` | Low | KPI / LED slightly wrong | Already an existing risk; `valveConfig.js` already has a "keep in sync" comment |
| Demo recorder captures KPI flipping 0→3→0 quickly during recovery | Medium | Visual noise | Acceptable — flipping count IS the autonomous-recovery story |

## Notes

The audit's three problems collapse cleanly into two changes:

1. **Energy card** — independent, replace it.
2. **Anomaly counter + LED color** — same root cause (frontend used `anomaly_detected` boolean; L3 panel uses the lower-threshold "impaired" heuristic from `debate.py`). One shared module fixes both.

Audit suggested 3 separate fixes (~75 min total). This plan does it in ~60 min thanks to the shared module.

The audit's "Reading B" (math right, framing wrong) for the energy card is correct: even if the constant were accurate, comparing a live-instant simulator power against a static datasheet number is methodologically indefensible. Removing it entirely is the right call.
