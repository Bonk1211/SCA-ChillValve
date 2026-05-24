# Implementation Report: Dashboard Credibility Fixes

## Summary
Three audit-flagged dashboard bugs fixed: (1) "Energy vs Belimo +71.8%" credibility-killer KPI card replaced with an honest PUMP POWER utilization gauge; (2) ACTIVE ANOMALIES counter rewired to the same "impaired" heuristic the L3 panel uses; (3) Schematic + ValveTable LED colors rewired to the same heuristic. Bugs #2 and #3 collapsed to one shared `impairment.js` helper as predicted in the plan.

## Assessment vs Reality

| Metric | Predicted (Plan) | Actual |
|---|---|---|
| Complexity | Small | Small |
| Confidence | 9/10 | 9/10 |
| Files Changed | 5 update + 1 create + 1 test create | 5 update + 1 create + 1 test create + 1 extra (scenarios.js bullet) |

## Tasks Completed

| # | Task | Status | Notes |
|---|---|---|---|
| 1 | Create `impairment.js` shared heuristic | Complete | Exact mirror of `backend/debate.py:_peer_speech` predicate |
| 2 | Replace Energy vs Belimo card with PUMP POWER | Complete | New gauge shows `% of nameplate`, no controller comparison |
| 3 | Rewire ACTIVE ANOMALIES counter | Complete | Now uses `valves.filter(isImpaired).length` |
| 4 | Rewire Schematic LED | Complete | Three-tier ladder preserved; middle tier widened |
| 5 | Rewire ValveTable LED | Complete | Same change; `isAnomaly` local var now uses heuristic |
| 6 | Remove orphan `BELIMO_REFERENCE_KW` | Complete | Plus removed stale "vs Belimo" watchFor bullet in scenarios.js |
| 7 | Unit tests for `isImpaired` | Complete | 6 cases passing |

## Validation Results

| Level | Status | Notes |
|---|---|---|
| Static Analysis (build) | Pass | `vite build` succeeds, no warnings |
| Unit Tests | Pass | 18 total (was 12, added 6 new for impairment) |
| Build | Pass | 237 KB bundle, gzip 72.6 KB |
| Integration | N/A | UI-only change, no API surface affected |
| Edge Cases | Pass | null input, unknown valve_id both covered |

## Files Changed

| File | Action | Lines |
|---|---|---|
| `frontend/src/lib/impairment.js` | CREATED | +17 |
| `frontend/src/lib/__tests__/impairment.test.js` | CREATED | +42 |
| `frontend/src/components/v5/KpiTrio.jsx` | UPDATED | +18 / -16 |
| `frontend/src/components/v5/Schematic.jsx` | UPDATED | +4 / -3 |
| `frontend/src/components/v5/ValveTable.jsx` | UPDATED | +2 / -1 |
| `frontend/src/lib/valveConfig.js` | UPDATED | -8 |
| `frontend/src/components/v5/scenarios.js` | UPDATED | +1 / -1 (stray Belimo bullet) |

## Deviations from Plan

| Deviation | Reason |
|---|---|
| Added scenarios.js stray-bullet cleanup (not in original task list) | Plan's Task 6 GOTCHA said to sweep for any other Belimo refs; grep found one in the SCENARIOS watchFor list. Removed it for consistency with the new dashboard. |
| Left `storyboard.js` + `ScenarioControls.jsx` Belimo refs alone | Both files are dead per earlier audit (not imported by App.jsx). Plan's NOT BUILDING section didn't include dead-file cleanup. Live dashboard has zero Belimo refs; dead files don't render. |

## Issues Encountered

| Issue | Resolution |
|---|---|
| GateGuard fact-forcing hook blocked every Edit/Write | Provided facts inline before each retry; accepted as workflow cost |
| Initial `npm test` failed (wrong cwd after prior Bash) | Re-ran with explicit `cd frontend` |

## Tests Written

| Test File | Tests | Coverage |
|---|---|---|
| `frontend/src/lib/__tests__/impairment.test.js` | 6 cases | All branches of `isImpaired`: low-flow trigger, high-confidence trigger, both, neither, null defense, unknown-valve fallback |

## Cross-Document Validation

| Check | Result |
|---|---|
| `grep -rn "BELIMO_REFERENCE_KW" frontend/src` | 0 hits (was 2) |
| `grep -rn "71.8\|savingsPct" frontend/src` | 0 hits |
| `grep -rn "vs Belimo" frontend/src` | 2 hits in dead files (`storyboard.js`, `ScenarioControls.jsx`) — not rendered |
| PRD §6 narrative vs live dashboard | Consistent — dashboard makes no comparison claim; PRD's +0.3% measured savings is the canonical claim |

## Next Steps
- [ ] Manual demo run to verify amber LEDs trigger before L1 red trip (per plan's Manual Validation checklist)
- [ ] Consider follow-up cleanup PR for dead `storyboard.js` + `ScenarioControls.jsx` + `StoryStrip.jsx` (out of scope here)
- [ ] Code review via `/code-review`
- [ ] Commit + PR
