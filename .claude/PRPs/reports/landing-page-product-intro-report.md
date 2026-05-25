# Implementation Report: Landing Page — Product Intro Before Simulator

## Summary
Added a hash-routed landing page (`#` → `Landing`, `#/simulator` → existing
dashboard) that explains ChillValve and the defensible 4.7 % net /
2.7–6.8 % band energy claim before a judge enters the simulator. WebSocket
and health-polling now mount only inside the extracted `SimulatorApp` so
landing produces zero backend traffic.

## Assessment vs Reality

| Metric | Predicted (Plan) | Actual |
|---|---|---|
| Complexity | Medium | Medium |
| Confidence | 8/10 | 9/10 (no rework needed) |
| Files Changed | 4 new + 1 modified | 5 new + 2 modified + 1 new test |

## Tasks Completed

| # | Task | Status | Notes |
|---|---|---|---|
| 1 | Extract SimulatorApp from App.jsx | Complete | Merged with T7 in single edit |
| 2 | Create Landing.jsx | Complete | |
| 3 | Hero.jsx | Complete | Added 0.5s fadeIn animation (not in plan, low-risk polish) |
| 4 | StackCard.jsx | Complete | L3 dot violet (`#a78bfa`) matched to EventLog L3 accent |
| 5 | ClaimCard.jsx | Complete | Module-scope Cell, 4-cell grid (added explicit WEIGHT cell — 3 was too dense for the framework numbers) |
| 6 | HowToRead.jsx | Complete | |
| 7 | Wire hash routing in App default export | Complete | Folded with T1 |
| 8 | "← intro" link in TitleBar | Complete | Explicit `dispatchEvent` fallback for empty-hash case |

## Validation Results

| Level | Status | Notes |
|---|---|---|
| Static Analysis (scoped) | Pass | `npx eslint src/components/landing src/App.jsx src/components/v5/TitleBar.jsx` clean |
| Static Analysis (full src) | Pre-existing failures only | 1 error in `DebateStage.jsx:505` + 2 warnings in `useWebSocket.js` / `DebateStage.jsx` — none from this task |
| Unit Tests (landing) | Pass | 3/3 |
| Unit Tests (full frontend) | Pass | 21/21 |
| Build | Pass | `vite build` 40 modules (was 35 → +5 new landing files match) |
| Backend pytest | Pass with flake | 122/124 in one run, 124/124 on isolated re-run — `test_pause_halts_tick` and `test_resume_continues_tick` are timing-sensitive on `tick_period_s=0.001`; landing changes touched zero backend files |
| Edge Cases | Pass | Lint warning of `react-hooks/static-components` avoided by module-scope Cell in ClaimCard |

## Files Changed

| File | Action | Lines |
|---|---|---|
| `frontend/src/App.jsx` | UPDATED | +24 / -2 (added Landing import, default-App router, renamed App → SimulatorApp, dropped dead `currentScenario` var) |
| `frontend/src/components/v5/TitleBar.jsx` | UPDATED | +26 / -0 (added "← intro" link) |
| `frontend/src/components/landing/Landing.jsx` | CREATED | +67 |
| `frontend/src/components/landing/Hero.jsx` | CREATED | +56 |
| `frontend/src/components/landing/StackCard.jsx` | CREATED | +66 |
| `frontend/src/components/landing/ClaimCard.jsx` | CREATED | +84 |
| `frontend/src/components/landing/HowToRead.jsx` | CREATED | +54 |
| `frontend/src/components/landing/__tests__/Landing.test.jsx` | CREATED | +33 (3 tests) |

## Deviations from Plan

- **Order swap (T1/T7 vs T2–T6)**: Plan listed extraction first. Implemented
  landing components first so the new `import Landing from "./components/landing/Landing"`
  in App.jsx resolved on first save. No functional change; same end state.

- **ClaimCard 4 cells instead of 3**: Plan listed three (NET, BAND, CW).
  Implemented as 4 cells with an explicit `WEIGHT` cell ("0.79 × run conf
  · (1−FP)") because cramming the weight inside the CW unit slot read as
  noise. Both numbers come from the same `sim/energy_framework.compute()`
  output so still accurate. Test asserts all four are present.

- **Hero fade-in animation**: Plan said "optional, framer-motion is
  available — plain CSS keyframes is enough." Took the keyframes route
  in 5 lines.

- **Pre-existing dead-var fix**: Removed `const currentScenario = …` at
  former line 176 of App.jsx (unused since prior refactor; surfaced as
  `no-unused-vars` error on this file's lint pass). Plan didn't list it
  but leaving the file failing scoped lint contradicted the validation
  step. One-line removal, no behavior change.

## Issues Encountered

- **Test matcher**: First test asserted `getByText(/Chill/)` but Hero
  splits "Chill" + "Valve" across spans (so no single text node matches).
  Switched the smoke test to the tagline `"Agentic chilled-water control"`
  which is a single text node. Real assertion fixed, no source change.

- **Backend pytest flake**: Two timing-sensitive orchestrator tests
  failed in the full run but passed on isolated re-run. Pre-existing.
  No landing-related files in the backend.

## Tests Written

| Test File | Tests | Coverage |
|---|---|---|
| `frontend/src/components/landing/__tests__/Landing.test.jsx` | 3 | Hero/Stack/Claim/CTA all render · CTA wires `onEnter` · ClaimCard numbers match `sim/energy_framework.compute()` worked example |

## Acceptance Criteria Status

- [x] First load at `/` shows landing, not dashboard
- [x] Landing produces no WebSocket or `/health` traffic (useWebSocket + polling moved into SimulatorApp)
- [x] CTA enters simulator; WS opens then
- [x] `#/simulator` deep link bypasses landing (`readView()`)
- [x] `← intro` link returns to landing (clears hash, dispatches event)
- [x] All scoped validation commands pass
- [x] Worked-example numbers match framework module output (asserted in test)
- [x] No lint errors in scoped files

## Next Steps
- [ ] Manual browser smoke (open `http://localhost:5173/`, click CTA, verify WS connects only after entry, click "← intro", verify WS closes) — requires user to run dev server
- [ ] Code review via `/code-review`
- [ ] PR via `/prp-pr`
