# Plan: Landing Page — Product Intro Before Simulator

## Summary
Add a first-impression landing page that frames what ChillValve is, the
problem it solves, and the defensible claim (4–7 % net annual savings,
band 2.7 / 4.7 / 6.8 %) before a judge or visitor is dropped into the
live `v5` simulator dashboard. A primary CTA enters the simulator; the
simulator mounts WebSocket + health polling only after entry, not on
landing.

## User Story
As a first-time visitor or hackathon judge,
I want a concise page that explains what the product is and how to read
the simulator,
so that the dashboard's six panels, debate transcripts, and energy
summary have context instead of looking like raw telemetry.

## Problem → Solution
**Current**: `App.jsx` renders the live v5 dashboard at "/" with no
preamble. The WebSocket opens immediately, health polling starts, and a
judge sees `B1 47 GPM 5.0 °C 23.7 %` with no idea what they're looking
at.

**Desired**: A landing route presents the product story, the framework
result, and a single "Open the simulator" CTA. Clicking the CTA mounts
the existing dashboard untouched. Browser back returns to landing.

## Metadata
- **Complexity**: Medium
- **Source PRD**: N/A — free-form feature request
- **PRD Phase**: standalone
- **Estimated Files**: 4 new, 1 modified

---

## UX Design

### Before
```
┌──────────────────────────────────────────────┐
│ TitleBar · LIVE · ws://…              [conn] │
│ ScenarioPicker [STEADY] [LOAD…] [FAULT…]     │
├──────────┬─────────────────────┬─────────────┤
│ KPI trio │ Schematic           │ Event log   │
│ FlowChart│ Valve table         │ Debate log  │
└──────────┴─────────────────────┴─────────────┘
   ↑ user is dropped into raw simulator immediately
```

### After
```
┌──────────────────────────────────────────────┐
│           ChillValve                         │
│  Agentic chilled-water control               │
│                                              │
│  Belimo Δ-T Manager waits for the threshold  │
│  to break. ChillValve sees the pattern that  │
│  leads to the break — minutes earlier, with  │
│  a confidence signal you can audit.          │
│                                              │
│  ┌── 3-LAYER STACK ──┐ ┌── DEFENSIBLE ──┐    │
│  │ L1 deterministic  │ │ +4.7 % net /yr │    │
│  │ L2 ML anomaly     │ │ band 2.7–6.8 % │    │
│  │ L3 LLM debate     │ │ confidence wt  │    │
│  └───────────────────┘ └────────────────┘    │
│                                              │
│         ▶  OPEN THE SIMULATOR                │
│                                              │
│  what you'll see · how to read it · stack    │
└──────────────────────────────────────────────┘
   ↑ landing first; CTA enters simulator
```

### Interaction Changes

| Touchpoint | Before | After | Notes |
|---|---|---|---|
| App mount | Dashboard renders, WS opens, health polls | Landing renders, no WS, no polling | Effects move into `SimulatorApp` |
| Entering simulator | Default route | Click "Open the simulator" CTA | Sets `view="simulator"` |
| Returning to landing | n/a | Small "← back" link in TitleBar | Optional but cheap |
| Direct deep-link | n/a | `#/simulator` skips landing | Lets judges share a URL into the live view |
| Browser refresh on simulator | Stays on dashboard | Stays on dashboard (hash preserved) | `#/simulator` survives reload |

---

## Mandatory Reading

| Priority | File | Lines | Why |
|---|---|---|---|
| P0 | `frontend/src/App.jsx` | 1-393 | Entire current root — needs to be split into landing-router + simulator |
| P0 | `frontend/src/main.jsx` | 1-11 | Where root renders; should stay unchanged |
| P0 | `frontend/src/components/v5/TitleBar.jsx` | 1-80 | Color palette + inline-style convention to mirror |
| P0 | `frontend/src/components/v5/SummaryBanner.jsx` | 1-90 | `Cell` component pattern (module-scope function, inline styles) — mirror for landing's KPI cards |
| P1 | `frontend/src/hooks/useWebSocket.js` | all | Confirm WS is opened from inside the hook — moving the hook call into SimulatorApp delays connection until entry |
| P1 | `frontend/src/lib/api.js` | health/start | Confirm `api.health` runs only on demand — landing must not poll |
| P2 | `frontend/src/components/v5/SummaryBanner.jsx` | 200-330 | Framework block markup — landing can reuse the "4.7 % / band 2.7–6.8 %" numbers as static intro content |
| P2 | `frontend/src/index.css` | 1-12 | Global font + bg color so landing matches dashboard |

## External Documentation

| Topic | Source | Key Takeaway |
|---|---|---|
| framer-motion v12 | already installed (`package.json`) | Available for entry animations — use `motion.div` for hero fade-in if desired; keep optional |

No external research needed — feature uses established internal patterns.

---

## Patterns to Mirror

### COLOR_PALETTE
// SOURCE: frontend/src/components/v5/TitleBar.jsx:13–24, SummaryBanner.jsx:88–115
```
bg page         #0a1224
bg panel        #131f37  (gradient 180deg → #0a1224)
border          #2d3d5e
accent cyan     #22d3ee
accent green    #34d399
warn amber      #fbbf24
alarm red       #f87171
text primary    #fff
text secondary  #d1dcec
text muted      #9aacc8
```

### INLINE_STYLE_CONVENTION
// SOURCE: frontend/src/components/v5/TitleBar.jsx:6–24
```jsx
<div
  style={{
    display: "flex",
    padding: "6px 14px",
    borderBottom: "1px solid #2d3d5e",
    background: "linear-gradient(180deg, #131f37 0%, #0a1224 100%)",
  }}
>
```
No Tailwind utilities for layout in v5 components — everything inline.
`className="mono"` is the only className you'll see; it marks text that
should render in monospace (the rule itself is currently undefined in
`index.css`, inherited as system mono — keep using it for consistency).

### MODULE_SCOPE_CELL
// SOURCE: frontend/src/components/v5/SummaryBanner.jsx:4–46
```jsx
function Cell({ label, value, unit, accent }) {
  return (
    <div style={{ background: "#0f1a30", border: `1.5px solid ${accent ? `${accent}55` : "#2d3d5e"}`, borderRadius: 5, padding: "10px 14px" }}>
      <div className="mono" style={{ fontSize: 11, color: "#9aacc8", letterSpacing: "0.1em", fontWeight: 600 }}>{label}</div>
      <div style={{ display: "flex", alignItems: "baseline", gap: 5 }}>
        <span className="mono" style={{ fontSize: 26, fontWeight: 700, color: accent ?? "#fff" }}>{value}</span>
        <span className="mono" style={{ fontSize: 12, color: "#9aacc8" }}>{unit}</span>
      </div>
    </div>
  );
}
```
**Critical**: subcomponents go at module scope. Declaring them inside
`SummaryBanner`'s render previously tripped `react-hooks/static-components`
ESLint and was fixed last session. Do not re-introduce.

### NAMING
// SOURCE: frontend/src/components/v5/
```
components/v5/PascalCase.jsx           (UI components, default-export)
components/v5/camelCase.js             (config/data: scenarios.js, storyboard.js)
hooks/useCamelCase.js                  (custom hooks)
lib/api.js, lib/valveConfig.js         (helpers)
store/useDashboardStore.js             (zustand store)
```
Landing components live under `frontend/src/components/landing/` to keep
the v5 simulator surface clean.

---

## Files to Change

| File | Action | Justification |
|---|---|---|
| `frontend/src/App.jsx` | UPDATE | Split into top-level router (`view` state) and extracted `SimulatorApp` that holds the current effects/state |
| `frontend/src/components/landing/Landing.jsx` | CREATE | Top-level landing component — hero, product story, framework KPI strip, CTA |
| `frontend/src/components/landing/Hero.jsx` | CREATE | Product name + tagline + sub-tagline |
| `frontend/src/components/landing/StackCard.jsx` | CREATE | Three-layer (L1/L2/L3) explainer card |
| `frontend/src/components/landing/ClaimCard.jsx` | CREATE | "+4.7 % net / yr · band 2.7–6.8 % · confidence-weighted" card — reuses framework wording so it matches what the simulator emits |
| `frontend/src/components/landing/HowToRead.jsx` | CREATE | Small "what you'll see in the dashboard" guide (KPIs, debate, summary) |

## NOT Building

- **Not** introducing `react-router-dom`. Single hash-based switch in
  App.jsx is enough; adding a router for one transition is over-design.
- **Not** moving the simulator into a separate route file. Just extract
  the existing 393-line App body into a `SimulatorApp` function in the
  same file (or `frontend/src/components/v5/SimulatorApp.jsx`).
- **Not** persisting "user saw landing" across sessions. Every fresh
  load should default to landing so judges see the story — except when
  the URL already contains `#/simulator`.
- **Not** redesigning the dashboard. CTA opens it unchanged.
- **Not** adding a backend endpoint. Landing is pure frontend.
- **Not** internationalizing copy. English only.
- **Not** adding marketing analytics, signup forms, or contact CTAs.

---

## Step-by-Step Tasks

### Task 1: Extract SimulatorApp from App.jsx
- **ACTION**: Move the existing `App` body (state, effects, return) into a new function `SimulatorApp` at the bottom of `frontend/src/App.jsx`. Leave imports at the top.
- **IMPLEMENT**:
  - Rename current `App` → `SimulatorApp`. Keep it as a non-default named export inside the same file (no separate file yet).
  - Add a new default export `App` that reads the URL hash (`window.location.hash`) and renders either `<Landing onEnter={…}/>` or `<SimulatorApp />`.
  - `onEnter` sets `window.location.hash = "#/simulator"` and updates a `useState` so the swap is instant (the hashchange listener is the fallback for direct deep-links).
- **MIRROR**: existing App.jsx structure — keep inline styles, do not introduce CSS modules.
- **IMPORTS**: add `import Landing from "./components/landing/Landing";`
- **GOTCHA**: `useWebSocket("ws://localhost:8000/ws")` and the `useEffect` health-polling loop both live inside `App`. After extraction they must live inside `SimulatorApp` so the WS does NOT open while the landing page is showing. Verify in DevTools Network → WS that no connection appears until CTA is clicked.
- **VALIDATE**: `npx eslint src/App.jsx` clean. `npx vite build` succeeds.

### Task 2: Create Landing.jsx (composition root)
- **ACTION**: Create `frontend/src/components/landing/Landing.jsx`.
- **IMPLEMENT**:
  ```jsx
  import Hero from "./Hero";
  import StackCard from "./StackCard";
  import ClaimCard from "./ClaimCard";
  import HowToRead from "./HowToRead";

  export default function Landing({ onEnter }) {
    return (
      <div style={{
        minHeight: "100vh",
        background: "radial-gradient(circle at 50% -10%, #1a2640 0%, #0a1224 60%)",
        color: "#fff",
        fontFamily: "Inter, system-ui, sans-serif",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "48px 24px",
        gap: 32,
      }}>
        <Hero />
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, width: "100%", maxWidth: 880 }}>
          <StackCard />
          <ClaimCard />
        </div>
        <button
          onClick={onEnter}
          className="mono"
          style={{
            background: "#22d3ee",
            color: "#0a1224",
            border: "none",
            padding: "14px 40px",
            borderRadius: 6,
            fontSize: 16,
            fontWeight: 700,
            letterSpacing: "0.14em",
            cursor: "pointer",
            boxShadow: "0 0 40px rgba(34, 211, 238, 0.4)",
          }}
        >
          ▶  OPEN THE SIMULATOR
        </button>
        <HowToRead />
      </div>
    );
  }
  ```
- **MIRROR**: COLOR_PALETTE; CTA accent matches TitleBar's cyan.
- **IMPORTS**: React 19 — no need for explicit `React` import in JSX.
- **GOTCHA**: On narrow viewports the 2-col grid stacks awkwardly. Add `@media (max-width: 720px)` style or accept the demo target is desktop.
- **VALIDATE**: page renders at `/` when hash is empty. CTA click sets `#/simulator` and SimulatorApp mounts.

### Task 3: Hero.jsx
- **ACTION**: Create `frontend/src/components/landing/Hero.jsx`.
- **IMPLEMENT**: Product name (ChillValve, 48 px, accent cyan on "Valve"), tagline ("Agentic chilled-water control"), sub-tagline ("Belimo Δ-T Manager waits for the threshold to break. ChillValve sees the pattern that leads to the break — minutes earlier, with a confidence signal you can audit."). Centered text, max-width 720 px.
- **MIRROR**: TitleBar.jsx:21–24 for the "Chill" / "Valve" two-tone treatment.
- **GOTCHA**: avoid quoting unverifiable savings numbers in the hero — the auditable numbers belong in `ClaimCard` where they're explicitly framed as "framework-derived, band 2.7–6.8 %".
- **VALIDATE**: visual review only.

### Task 4: StackCard.jsx
- **ACTION**: Create `frontend/src/components/landing/StackCard.jsx`.
- **IMPLEMENT**: A single panel with header "3-LAYER STACK" and three rows: `L1 · deterministic safety rules`, `L2 · ML anomaly detection`, `L3 · LLM peer debate + recovery`. Each row gets a small color dot (cyan/green/amber) and a one-line description.
- **MIRROR**: MODULE_SCOPE_CELL — wrap a panel with `background:"#131f37"`, `border:"1px solid #2d3d5e"`, `borderRadius:6`, `padding:"16px 18px"`.
- **GOTCHA**: keep copy under 80 chars per row — landing must read in <10 seconds.
- **VALIDATE**: visual review only.

### Task 5: ClaimCard.jsx
- **ACTION**: Create `frontend/src/components/landing/ClaimCard.jsx`.
- **IMPLEMENT**: Mirror the simulator's framework block visually. Header "DEFENSIBLE ENERGY CLAIM". Three numbers using the same `Cell`-style markup (label + value + unit). Use **static** numbers tied to the worked example so landing and SummaryBanner agree:
  - `NET vs BASELINE` → `4.71 %`
  - `BAND L · M · H` → `2.7 · 4.7 · 6.8 %`
  - `CONFIDENCE-WEIGHTED` → `1,954 kWh / yr · w=0.79`
  Footnote: "computed by `sim/energy_framework.py` · run a scenario to see this updated with measured detection latency".
- **MIRROR**: SummaryBanner.jsx Cell function — copy the style verbatim so landing visually pre-echoes what judges see at end of run.
- **GOTCHA**: do NOT fetch live framework numbers via API on landing — that defeats the "no WS / no polling until CTA" rule. Numbers are static, sourced from the worked example. The simulator will surface the real measured numbers in the SummaryBanner once a scenario runs.
- **VALIDATE**: numbers on landing match those produced by `uv run python -c "from sim.energy_framework import compute, MeasuredRun; ..."` worked example.

### Task 6: HowToRead.jsx
- **ACTION**: Create `frontend/src/components/landing/HowToRead.jsx`.
- **IMPLEMENT**: A short three-column strip under the CTA describing what to look for in the dashboard:
  1. **KPIs (left)** — pump kW, ΔT compliance, flow per valve.
  2. **Schematic + Debate (center)** — agents reallocate flow under uncertainty.
  3. **Summary (end-of-run)** — measured per-phase pump_kW + framework projection.
- **MIRROR**: TitleBar's secondary text — `mono` className, `#9aacc8` muted color, small caps via `letterSpacing: "0.1em"`.
- **GOTCHA**: this section is informational, not a CTA. No buttons.
- **VALIDATE**: visual review only.

### Task 7: Wire hash routing in App default export
- **ACTION**: Inside `frontend/src/App.jsx`, write the default `App` to listen for `hashchange` and switch between `Landing` and `SimulatorApp`.
- **IMPLEMENT**:
  ```jsx
  function readView() {
    return window.location.hash === "#/simulator" ? "simulator" : "landing";
  }
  export default function App() {
    const [view, setView] = useState(readView);
    useEffect(() => {
      const onHash = () => setView(readView());
      window.addEventListener("hashchange", onHash);
      return () => window.removeEventListener("hashchange", onHash);
    }, []);
    const enterSimulator = () => {
      window.location.hash = "#/simulator";
      setView("simulator");
    };
    return view === "simulator"
      ? <SimulatorApp />
      : <Landing onEnter={enterSimulator} />;
  }
  ```
- **MIRROR**: existing useState/useEffect convention in App.jsx.
- **GOTCHA**: do NOT call `useWebSocket` or `api.health` outside `SimulatorApp`. If you forget this, the landing page silently opens a WS — verify in DevTools.
- **VALIDATE**: first visit to `/` shows landing, no WS in Network tab; `/#/simulator` shows dashboard; clicking CTA on landing switches to dashboard without reload; refreshing on `/#/simulator` stays on dashboard.

### Task 8: Add "← back to intro" hook (optional, lightweight)
- **ACTION**: In `TitleBar.jsx`, add a small `← intro` link before the product name that clears the hash.
- **IMPLEMENT**:
  ```jsx
  <a
    href="#"
    onClick={(e) => { e.preventDefault(); window.location.hash = ""; }}
    className="mono"
    style={{ fontSize: 10, color: "#9aacc8", letterSpacing: "0.1em", marginRight: 8, textDecoration: "none" }}
  >
    ← intro
  </a>
  ```
- **MIRROR**: TitleBar's existing `className="mono"` + muted color.
- **GOTCHA**: clearing the hash should trigger `hashchange` so App swaps back to `Landing`. If it doesn't, dispatch `window.dispatchEvent(new HashChangeEvent("hashchange"))` after the assignment.
- **VALIDATE**: in simulator, click "← intro" — landing returns, WS closes (Network tab shows WS gone). Re-entering opens a fresh WS.

---

## Testing Strategy

### Unit Tests

| Test | Input | Expected Output | Edge Case? |
|---|---|---|---|
| Landing renders hero, stack, claim, CTA | `<Landing onEnter={fn} />` | All four child components in DOM | No |
| CTA click calls onEnter | RTL click on button | `onEnter` mock called once | No |
| ClaimCard shows worked-example numbers | `<ClaimCard />` | Text contains "4.71 %" and "2.7 · 4.7 · 6.8" | Yes — must match framework output |
| App default starts on landing | empty hash | Landing in DOM, SimulatorApp absent | No |
| App route follows `#/simulator` | `window.location.hash = "#/simulator"` then mount | SimulatorApp in DOM | Yes — direct deep link |
| Hash change triggers swap | fire `hashchange` event | view switches | No |

Test file location: `frontend/src/components/landing/__tests__/Landing.test.jsx`
(mirror existing pattern: vitest + @testing-library/react are already in
devDependencies; no setup needed).

### Edge Cases Checklist
- [ ] Refresh on `#/simulator` stays on dashboard
- [ ] Empty hash defaults to landing
- [ ] Click CTA twice — no double mount, no WS leak
- [ ] Browser back from simulator → landing reachable
- [ ] Narrow viewport (≤720 px) — 2-col grid stacks; CTA still tappable
- [ ] Landing produces zero network traffic (no WS, no `/health`)

---

## Validation Commands

### Static Analysis
```bash
npx eslint src/components/landing src/App.jsx
```
EXPECT: zero errors. Watch for `react-hooks/static-components` —
subcomponents must be at module scope (see SummaryBanner regression
from prior session).

### Unit Tests
```bash
npx vitest run src/components/landing
```
EXPECT: all landing tests pass.

### Full Test Suite
```bash
npx vitest run && (cd /Users/limjiale/SCA-ChillValve && uv run pytest -q)
```
EXPECT: frontend vitest + backend pytest (124 existing) both pass — no
regressions; backend untouched but worth confirming.

### Browser Validation
```bash
# backend
cd /Users/limjiale/SCA-ChillValve && uv run uvicorn backend.main:app --reload
# frontend (separate terminal)
cd /Users/limjiale/SCA-ChillValve/frontend && npx vite
```
EXPECT:
1. Open http://localhost:5173/ → landing page shows, no WS in Network tab.
2. Click "OPEN THE SIMULATOR" → dashboard mounts, WS connects, health
   polling starts.
3. Click "← intro" → return to landing, WS closes.
4. Open http://localhost:5173/#/simulator directly → dashboard mounts
   without landing flash.

### Manual Validation
- [ ] Landing copy reads in under 10 s
- [ ] Worked-example numbers on `ClaimCard` match
      `sim/energy_framework.compute()` output (4.71 % / band 2.7·4.7·6.8 /
      1,954 kWh)
- [ ] No console errors / warnings in either view
- [ ] CTA button has visible focus ring (keyboard-accessible)
- [ ] Refreshing the simulator URL keeps you on simulator

---

## Acceptance Criteria
- [ ] First load at `/` shows landing, not dashboard
- [ ] Landing produces no WebSocket or `/health` traffic
- [ ] CTA enters simulator; WS opens then
- [ ] `#/simulator` deep link bypasses landing
- [ ] `← intro` link returns to landing, closes WS
- [ ] All validation commands pass
- [ ] Worked-example numbers match framework module output
- [ ] No lint errors

## Completion Checklist
- [ ] Code follows v5 inline-style convention
- [ ] Subcomponents declared at module scope
- [ ] `className="mono"` used for monospaced text consistent with v5
- [ ] Color palette respected (no new hex codes introduced)
- [ ] No new dependencies added
- [ ] No backend changes
- [ ] No persistence — every fresh session starts on landing (unless hash present)
- [ ] Self-contained — no questions needed during implementation

## Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| WebSocket opens on landing (effect leaked outside SimulatorApp) | Medium | Defeats the "clean intro" goal, may confuse demos with reconnect spam | DevTools Network → WS check is part of validation; useWebSocket call MUST live inside SimulatorApp only |
| Subcomponent declared inside parent function trips ESLint | Medium | Build fails on CI | MIRROR pattern from SummaryBanner.jsx:4–46 explicitly; lint command in validation |
| Static claim numbers drift from framework output | Low | Landing and SummaryBanner show different "headline" numbers | Validation step compares to `sim/energy_framework.compute()` worked example. If `DEFAULT_CATALOG` is retuned, landing copy must update — add comment in `ClaimCard.jsx` pointing at the framework file |
| Mobile viewport breaks 2-col grid | Low | Demo target is desktop / projector | Acceptable for hackathon scope; documented in NOT Building |
| Hash-routing collides with future real router | Low | Refactor cost later | Single point of switch in App default export — easy to replace |

## Notes
- Last session standardized "what is defensible" around the 4.7 % net /
  2.7–6.8 % band figures. Landing is the place to plant that flag before
  judges see the live numbers, so the simulator's SummaryBanner can
  reinforce ("see, the numbers match") rather than introduce.
- `framer-motion` is already in dependencies. If time permits a 200 ms
  fade-in on Hero is nice, but plain CSS `@keyframes fadeIn` is enough.
- Backend is untouched. If a future "live numbers on landing" feature
  is wanted, add a `GET /api/framework/defaults` endpoint returning the
  worked-example dict — but that is OUT OF SCOPE here.
