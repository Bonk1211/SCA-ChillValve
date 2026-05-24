# Plan: React + Vite Dashboard with WebSocket Live State

## Summary
Build the React + Vite + Tailwind dashboard per PRD §8. The dashboard connects to the Phase 5 FastAPI backend over WebSocket `/ws`, renders 6 valve tiles in 2 branch rows with live metrics, three-layer activity indicators (L1 / L2 / L3 + LEADER badge), an energy comparison chart, an event log, and scenario/mode control buttons that POST to the backend's REST endpoints. After Phase 6, the user can open `http://localhost:5173`, click "Start scenario", and watch the live ChillValve / Belimo simulation in the browser.

## User Story
As the software lead recording the demo video, I want a polished real-time dashboard that visualises the three-layer architecture clearly, so that the 90-second demo storyboard from PRD §12 can be filmed by clicking through the UI rather than narrating a CLI.

## Problem → Solution
**Current state (after Phase 5):** Backend streams live state at 20 Hz over `/ws`; REST controls scenario lifecycle. No UI — viewer must use `websocat` + `curl`. Cannot record a defensible demo.
**Desired state:**
- `npm run dev` starts Vite on `http://localhost:5173`
- Dashboard auto-connects to `ws://localhost:8000/ws`; auto-reconnects on disconnect
- TopBar: scenario selector (steady_state for now), mode toggle (Belimo / ChillValve), Start / Pause / Resume / Reset buttons that fire the matching REST call
- 2 branch rows × 3 valve tiles each — every tile shows valve_id, flow GPM, ΔT °C, position %, three layer indicators (L1 fire pulse, L2 anomaly intensity, L3 emerald + LEADER badge), and a 60-second mini line chart of flow
- SystemSummary card: current pump kW, cumulative kWh, total branch flow
- EventLog: scrolling log of layer-1 fires, leader changes, mode swaps
- Dark slate theme exactly per PRD §8.2 color table

## Metadata
- **Complexity**: Large
- **Source PRD**: `docs/ChillValve_Implementation_PRD_v1.md`
- **PRD Phase**: Phase 6 — Frontend (PRD §10 steps 25–34)
- **Estimated Files**: ~25 (package.json, configs, App, 10 components, hook, store, styles, tests)
- **Stack**: React 18, Vite 5, Tailwind CSS 3, Zustand, Recharts, framer-motion (PRD §8.3 calls these out)

---

## UX Design

### Before
No visual surface. `websocat ws://localhost:8000/ws` prints JSON lines in a terminal.

### After
```
┌─────────────────────────────────────────────────────────────────────┐
│  ChillValve Dashboard                  scenario [steady_state ▾]    │
│                                        mode [Belimo|ChillValve]     │
│                                        [Start] [Pause] [Reset]      │
├─────────────────────────────────────────────────────────────────────┤
│ Branch A — CRAH                                                     │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐                              │
│ │ A1  LEAD │ │ A2       │ │ A3       │                              │
│ │ flow 21  │ │ flow 22  │ │ flow 21  │                              │
│ │ dT  5.0  │ │ dT  5.0  │ │ dT  5.0  │                              │
│ │ pos 52%  │ │ pos 50%  │ │ pos 51%  │                              │
│ │ ● ○ ●    │ │ ○ ○ ●    │ │ ○ ○ ●    │  L1/L2/L3 indicator dots    │
│ │ ╭──╮     │ │ ╭──╮     │ │ ╭──╮     │  60-sec mini flow chart     │
│ └──────────┘ └──────────┘ └──────────┘                              │
│                                                                     │
│ Branch B — AHU                                                      │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐                              │
│ │ B1  LEAD │ │ B2       │ │ B3       │                              │
│ │ ...                                                               │
├─────────────────────────────────────────────────────────────────────┤
│ System    pump  3.86 kW    energy  0.412 kWh    total  431 GPM     │
├─────────────────────────────────────────────────────────────────────┤
│ Event log                                                           │
│  12:01:03  leader change branch A: A2 → A1                          │
│  12:00:58  scenario started: steady_state / chillvalve              │
└─────────────────────────────────────────────────────────────────────┘
```

### Interaction Changes
| Touchpoint | Before | After |
|---|---|---|
| Start scenario | `curl -X POST .../scenario/start?...` | Click "Start" button |
| Watch state | `websocat ws://...` printing JSON | 6 animated valve tiles, mini-charts, indicator dots |
| Mode swap | `curl -X POST .../mode/belimo` | Click mode toggle button |
| See L1 fire | grep JSONL after the run | Sky-blue pulse on the affected valve tile |
| See leader change | grep JSONL | LEADER badge animates to the new tile |

---

## Mandatory Reading

| Priority | File | Lines | Why |
|---|---|---|---|
| P0 | `docs/ChillValve_Implementation_PRD_v1.md` | 797–871 | §8 — full component tree, color palette, layer indicator spec, compare mode |
| P0 | `backend/main.py` | all | REST endpoints + WS payload shape |
| P0 | `backend/models.py` | all | `WSStateMessage` and `ValveSnapshot` exact field names |
| P0 | `backend/orchestrator.py` | `_tick_once` | What lives in each `/ws` message: tick, pump_kw, pump_head_kpa, total_flow_gpm, valves[] with valve_id, flow_gpm, dT_C, position_pct, is_leader, anomaly_detected, anomaly_confidence, rule_fired, safety_override_active |
| P0 | `docs/ChillValve_Implementation_PRD_v1.md` | 1100–1115 | §12 demo storyboard — what the dashboard must support visually |
| P1 | `.claude/PRPs/reports/fastapi-backend-and-websocket-streaming-report.md` | all | CORS origin (localhost:5173), backend port (8000) |

## External Documentation

| Topic | Source | Key Takeaway |
|---|---|---|
| Vite + React template | https://vitejs.dev/guide/ | `npm create vite@latest frontend -- --template react` |
| Tailwind v3 with Vite | https://tailwindcss.com/docs/guides/vite | `npx tailwindcss init -p` then add directives |
| Zustand minimal store | https://github.com/pmndrs/zustand | `import { create } from "zustand"`; persistent ref-equal selectors |
| Recharts ResponsiveContainer | https://recharts.org/ | `<LineChart>` inside `<ResponsiveContainer>` for fluid sizing |
| framer-motion AnimatePresence | https://www.framer.com/motion/ | For LEADER badge transitions |
| WebSocket auto-reconnect pattern | n/a | Exponential backoff on `onclose`; reset on `onopen` |
| Vitest + React Testing Library | https://vitest.dev/ | `npm install -D vitest @testing-library/react jsdom` |

---

## Patterns to Mirror

No prior frontend in this repo — establishing patterns here. Future React work must follow.

### COMPONENT_NAMING
```jsx
// Files: PascalCase.jsx for components, camelCase.js for hooks/utils
// Exports: default-export for primary component, named-export for sub-helpers
// Props: destructured at top of function; types-by-convention (no TypeScript in prototype)
```

### COLOR_PALETTE (PRD §8.2 — must be exact)
```js
// frontend/src/lib/colors.js
export const colors = {
  bg:        "bg-slate-900",
  surface:   "bg-slate-800",
  border:    "border-slate-700",
  textPrim:  "text-slate-100",
  textSec:   "text-slate-400",
  healthy:   "text-emerald-400",
  warning:   "text-amber-400",
  critical:  "text-rose-400",
  leader:    "bg-cyan-500 text-slate-900",
  layer1:    "bg-sky-500",
  layer2:    "bg-violet-500",
  layer3:    "bg-emerald-500",
};
```

### WEBSOCKET_HOOK
```js
// frontend/src/hooks/useWebSocket.js
// Owns a single WebSocket connection. Calls onMessage on every state frame.
// Auto-reconnects with exponential backoff (1s, 2s, 4s, max 10s).
```

### STORE_SLICES
```js
// Zustand store separates connection state, latest snapshot, history buffer (60s),
// event log, scenario/mode/engine status.
```

---

## Files to Change

| File | Action | Justification |
|---|---|---|
| `frontend/package.json` | CREATE | Vite + React + Tailwind + Zustand + Recharts + framer-motion + Vitest |
| `frontend/vite.config.js` | CREATE | Standard Vite React config, port 5173, proxy /api -> localhost:8000 for REST calls |
| `frontend/tailwind.config.js` | CREATE | Content paths, default theme |
| `frontend/postcss.config.js` | CREATE | Tailwind + autoprefixer |
| `frontend/index.html` | CREATE | Mount root |
| `frontend/src/main.jsx` | CREATE | ReactDOM root render |
| `frontend/src/App.jsx` | CREATE | Top-level layout + WebSocket hookup |
| `frontend/src/index.css` | CREATE | Tailwind directives |
| `frontend/src/lib/colors.js` | CREATE | PRD §8.2 palette constants |
| `frontend/src/lib/api.js` | CREATE | Thin REST helpers (fetch wrappers for /scenario/* and /mode/*) |
| `frontend/src/store/useDashboardStore.js` | CREATE | Zustand store: connection state, latest snapshot, 60-s history, event log |
| `frontend/src/hooks/useWebSocket.js` | CREATE | WebSocket client with auto-reconnect |
| `frontend/src/components/TopBar.jsx` | CREATE | Scenario selector + ModeToggle + control buttons |
| `frontend/src/components/ScenarioControls.jsx` | CREATE | Start / Pause / Resume / Reset buttons |
| `frontend/src/components/ModeToggle.jsx` | CREATE | Belimo / ChillValve toggle |
| `frontend/src/components/DashboardGrid.jsx` | CREATE | 2 BranchRow layout + SystemSummary |
| `frontend/src/components/BranchRow.jsx` | CREATE | 3 ValveTiles side by side |
| `frontend/src/components/ValveTile.jsx` | CREATE | Single valve card with metrics, LEADER badge, layer indicators, mini chart |
| `frontend/src/components/LayerIndicator.jsx` | CREATE | L1/L2/L3 small dot with pulse / intensity |
| `frontend/src/components/MiniChart.jsx` | CREATE | 60-sec flow_gpm line, Recharts |
| `frontend/src/components/SystemSummary.jsx` | CREATE | Pump kW, kWh accumulator, total flow |
| `frontend/src/components/EventLog.jsx` | CREATE | Scrolling list of significant events |
| `frontend/src/components/__tests__/ValveTile.test.jsx` | CREATE | Renders with sample state; LEADER badge appears when is_leader=true |
| `frontend/src/components/__tests__/LayerIndicator.test.jsx` | CREATE | Active vs inactive class application |
| `frontend/src/store/__tests__/useDashboardStore.test.js` | CREATE | State updates from snapshot; 60-s buffer trim; event detection |
| `frontend/README.md` | CREATE | dev / build commands |
| `README.md` | UPDATE | "Run the dashboard" section + Phase 6 status |
| `pyproject.toml` | (no change) | Frontend is separate npm project |

## NOT Building

- **Authentication / login** — PRD §16 out of scope
- **Mobile-responsive layout** — desktop-only per PRD §16
- **History view from `/history` REST** — would duplicate live WebSocket data; viewer can still query backend directly
- **Compare mode side-by-side** with both modes running simultaneously — backend doesn't support concurrent modes (single engine, single controller); the toggle swaps between modes on the running engine instead
- **TypeScript** — prototype, plain JSX
- **Storybook** — not needed for 10 components
- **Server-side rendering** — Vite dev + `npm run build` static output is enough
- **Tests for every component** — only the load-bearing logic (ValveTile, LayerIndicator, store)

---

## Step-by-Step Tasks

### Task 1: Initialize Vite React project + install deps
- **ACTION**: `npm create vite@latest frontend -- --template react`, then `cd frontend && npm install` plus the additional libs.
- **IMPLEMENT**:
  ```bash
  cd /Users/limjiale/SCA-ChillValve
  npm create vite@latest frontend -- --template react
  cd frontend
  npm install
  npm install zustand recharts framer-motion
  npm install -D tailwindcss@3 postcss autoprefixer vitest @testing-library/react @testing-library/jest-dom jsdom @vitejs/plugin-react
  ```
- **GOTCHA**:
  - Use Tailwind v3 specifically (`tailwindcss@3`). Tailwind v4 has a different config style — Vite plugin instead of `tailwind.config.js`. We mirror PRD §8 conventions (v3).
  - Vite v5 + React 18 is the stable combo; Vite 6+ may bring breaking changes in JSX runtime.
- **VALIDATE**: `cd frontend && npm run dev -- --port 5173 &` starts the server; `curl localhost:5173/` returns the default Vite page.

### Task 2: Configure Tailwind + Vite proxy
- **ACTION**: Run `npx tailwindcss init -p`; edit `tailwind.config.js` content paths; configure Vite proxy.
- **IMPLEMENT**:
  ```js
  // frontend/tailwind.config.js
  export default {
    content: ["./index.html", "./src/**/*.{js,jsx}"],
    theme: { extend: {} },
    plugins: [],
  };
  ```
  ```js
  // frontend/vite.config.js
  import { defineConfig } from "vite";
  import react from "@vitejs/plugin-react";

  export default defineConfig({
    plugins: [react()],
    server: {
      port: 5173,
      proxy: {
        "/api": { target: "http://localhost:8000", rewrite: p => p.replace(/^\/api/, "") },
      },
    },
    test: { environment: "jsdom", setupFiles: "./src/test-setup.js" },
  });
  ```
  ```css
  /* frontend/src/index.css */
  @tailwind base;
  @tailwind components;
  @tailwind utilities;

  body { @apply bg-slate-900 text-slate-100 antialiased; }
  ```
- **GOTCHA**:
  - `/api` proxy lets components use relative URLs like `fetch("/api/scenario/start")` without hardcoding `localhost:8000`. WebSocket still uses absolute `ws://localhost:8000/ws` because Vite WS proxy is finicky in dev.
  - `test-setup.js` registers `@testing-library/jest-dom` matchers.

### Task 3: Color palette + REST helpers
- **ACTION**: Two small util modules.
- **IMPLEMENT**:
  ```js
  // frontend/src/lib/colors.js — PRD §8.2 verbatim
  export const colors = {
    bg: "bg-slate-900",
    surface: "bg-slate-800",
    border: "border-slate-700",
    textPrim: "text-slate-100",
    textSec: "text-slate-400",
    healthy: "text-emerald-400",
    warning: "text-amber-400",
    critical: "text-rose-400",
    leader: "bg-cyan-500 text-slate-900",
    layer1: "bg-sky-500",
    layer2: "bg-violet-500",
    layer3: "bg-emerald-500",
  };

  // frontend/src/lib/api.js
  const BASE = "http://localhost:8000";
  async function post(path, params = {}) {
    const q = new URLSearchParams(params).toString();
    const url = q ? `${BASE}${path}?${q}` : `${BASE}${path}`;
    const r = await fetch(url, { method: "POST" });
    if (!r.ok) throw new Error(`${path}: ${r.status} ${await r.text()}`);
    return r.json();
  }
  export const api = {
    startScenario: (name, mode) => post("/scenario/start", { name, mode }),
    pause:  () => post("/scenario/pause"),
    resume: () => post("/scenario/resume"),
    reset:  () => post("/scenario/reset"),
    setMode: (mode) => post(`/mode/${mode}`),
    health: () => fetch(`${BASE}/health`).then(r => r.json()),
  };
  ```
- **GOTCHA**: Use `http://localhost:8000` directly here (not `/api`) so the same code works when served from `npm run build` static output without a proxy.

### Task 4: Zustand store
- **ACTION**: Single store with separated slices.
- **IMPLEMENT**:
  ```js
  // frontend/src/store/useDashboardStore.js
  import { create } from "zustand";

  const HISTORY_LIMIT = 60;     // last 60 ticks per valve for the mini chart
  const EVENT_LIMIT = 100;      // event log capacity

  export const useDashboardStore = create((set, get) => ({
    connection: "disconnected",
    latest: null,                 // last WSStateMessage
    history: {},                  // { valve_id: [{tick, flow_gpm, dT_C}, ...] }
    events: [],                   // [{ ts, kind, text }, ...]
    engineStatus: { engine: "idle", tick: 0, scenario: null, mode: null },

    setConnection: (c) => set({ connection: c }),
    setEngineStatus: (s) => set({ engineStatus: s }),

    pushSnapshot: (snap) => {
      const state = get();
      // History buffer
      const history = { ...state.history };
      for (const v of snap.valves) {
        const arr = history[v.valve_id] || [];
        const next = [...arr, { tick: snap.tick, flow_gpm: v.flow_gpm, dT_C: v.dT_C }];
        history[v.valve_id] = next.slice(-HISTORY_LIMIT);
      }
      // Event detection: rule fires, leader changes
      const events = [...state.events];
      if (state.latest) {
        for (const v of snap.valves) {
          const prev = state.latest.valves.find(p => p.valve_id === v.valve_id);
          if (v.rule_fired && (!prev || prev.rule_fired !== v.rule_fired)) {
            events.push({ ts: Date.now(), kind: "rule", text: `${v.valve_id} rule fired: ${v.rule_fired}` });
          }
          if (prev && prev.is_leader !== v.is_leader) {
            const txt = v.is_leader ? `leader → ${v.valve_id}` : `${v.valve_id} stepped down`;
            events.push({ ts: Date.now(), kind: "leader", text: `branch ${v.branch_id}: ${txt}` });
          }
        }
      }
      while (events.length > EVENT_LIMIT) events.shift();
      set({ latest: snap, history, events });
    },

    addEvent: (kind, text) => {
      const events = [...get().events, { ts: Date.now(), kind, text }];
      while (events.length > EVENT_LIMIT) events.shift();
      set({ events });
    },
  }));
  ```
- **GOTCHA**:
  - `slice(-HISTORY_LIMIT)` keeps allocations small; do NOT keep all 3600 ticks per valve in memory.
  - Event detection runs on every snapshot — keep predicates cheap. Compare against previous snapshot only.

### Task 5: useWebSocket hook
- **ACTION**: Connection lifecycle with backoff.
- **IMPLEMENT**:
  ```js
  // frontend/src/hooks/useWebSocket.js
  import { useEffect, useRef } from "react";
  import { useDashboardStore } from "../store/useDashboardStore";

  const RECONNECT_DELAYS_MS = [1000, 2000, 4000, 10000];

  export function useWebSocket(url) {
    const wsRef = useRef(null);
    const attemptRef = useRef(0);
    const setConnection = useDashboardStore(s => s.setConnection);
    const pushSnapshot = useDashboardStore(s => s.pushSnapshot);

    useEffect(() => {
      let cancelled = false;
      let timer;
      const connect = () => {
        if (cancelled) return;
        const ws = new WebSocket(url);
        wsRef.current = ws;
        setConnection("connecting");
        ws.onopen = () => { attemptRef.current = 0; setConnection("connected"); };
        ws.onmessage = (e) => {
          try { pushSnapshot(JSON.parse(e.data)); }
          catch { /* malformed, drop */ }
        };
        ws.onclose = () => {
          setConnection("disconnected");
          const delay = RECONNECT_DELAYS_MS[Math.min(attemptRef.current, RECONNECT_DELAYS_MS.length - 1)];
          attemptRef.current += 1;
          timer = setTimeout(connect, delay);
        };
        ws.onerror = () => { /* onclose will fire next */ };
      };
      connect();
      return () => {
        cancelled = true;
        clearTimeout(timer);
        wsRef.current?.close();
      };
    }, [url, setConnection, pushSnapshot]);
  }
  ```
- **GOTCHA**:
  - React 18 StrictMode double-invokes effects in dev → connection opens then closes immediately → reconnect loop. The cleanup function closes the socket and sets `cancelled=true` to break the loop.
  - Backoff caps at 10s so the dashboard recovers reasonably when the backend restarts mid-demo.

### Task 6: Components — ValveTile, LayerIndicator, MiniChart, BranchRow
- **ACTION**: Smallest leaf components first.
- **IMPLEMENT**:
  ```jsx
  // frontend/src/components/LayerIndicator.jsx
  import { colors } from "../lib/colors";

  export default function LayerIndicator({ layer, active, intensity = 1.0, label }) {
    const colorClass = { L1: colors.layer1, L2: colors.layer2, L3: colors.layer3 }[layer];
    const opacity = active ? Math.max(0.4, intensity) : 0.15;
    return (
      <div className="flex flex-col items-center">
        <div
          className={`w-3 h-3 rounded-full ${colorClass}`}
          style={{ opacity }}
          title={label}
        />
        <span className={`text-[10px] mt-1 ${colors.textSec}`}>{layer}</span>
      </div>
    );
  }

  // frontend/src/components/MiniChart.jsx
  import { LineChart, Line, ResponsiveContainer, YAxis } from "recharts";

  export default function MiniChart({ data, dataKey = "flow_gpm", color = "#38bdf8" }) {
    return (
      <div className="h-12 w-full">
        <ResponsiveContainer>
          <LineChart data={data} margin={{ top: 2, right: 2, bottom: 2, left: 2 }}>
            <YAxis hide domain={["auto", "auto"]} />
            <Line type="monotone" dataKey={dataKey} stroke={color} dot={false} strokeWidth={1.5} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    );
  }

  // frontend/src/components/ValveTile.jsx
  import { motion } from "framer-motion";
  import { colors } from "../lib/colors";
  import LayerIndicator from "./LayerIndicator";
  import MiniChart from "./MiniChart";

  export default function ValveTile({ valve, history = [] }) {
    return (
      <div className={`p-3 rounded-lg ${colors.surface} border ${colors.border} flex flex-col gap-2`}>
        <div className="flex items-center justify-between">
          <span className={`font-mono text-sm ${colors.textPrim}`}>{valve.valve_id}</span>
          {valve.is_leader && (
            <motion.span
              layoutId={`leader-${valve.branch_id}`}
              className={`text-[10px] px-1.5 py-0.5 rounded ${colors.leader} font-bold`}
            >
              LEADER
            </motion.span>
          )}
        </div>
        <div className="grid grid-cols-3 gap-1 text-xs">
          <Metric label="flow" value={`${valve.flow_gpm.toFixed(0)}`} unit="GPM" />
          <Metric label="ΔT" value={valve.dT_C.toFixed(1)} unit="°C" />
          <Metric label="pos" value={`${valve.position_pct.toFixed(0)}`} unit="%" />
        </div>
        <div className="flex gap-3 justify-center">
          <LayerIndicator layer="L1" active={!!valve.rule_fired} label={valve.rule_fired || "Layer 1 — rules"} />
          <LayerIndicator layer="L2" active={valve.anomaly_detected} intensity={valve.anomaly_confidence} label="Layer 2 — ML" />
          <LayerIndicator layer="L3" active={true} label="Layer 3 — coordination" />
        </div>
        <MiniChart data={history} dataKey="flow_gpm" />
      </div>
    );
  }

  function Metric({ label, value, unit }) {
    return (
      <div className="flex flex-col">
        <span className={`text-[10px] ${colors.textSec}`}>{label}</span>
        <span className={colors.textPrim}>
          {value}<span className={`ml-0.5 text-[10px] ${colors.textSec}`}>{unit}</span>
        </span>
      </div>
    );
  }

  // frontend/src/components/BranchRow.jsx
  import { colors } from "../lib/colors";
  import ValveTile from "./ValveTile";
  import { useDashboardStore } from "../store/useDashboardStore";

  export default function BranchRow({ branchId, label }) {
    const latest = useDashboardStore(s => s.latest);
    const history = useDashboardStore(s => s.history);
    const valves = latest?.valves?.filter(v => v.branch_id === branchId) ?? [];
    return (
      <section className="mb-4">
        <h2 className={`text-sm uppercase tracking-wide mb-2 ${colors.textSec}`}>
          Branch {branchId} — {label}
        </h2>
        <div className="grid grid-cols-3 gap-3">
          {valves.length === 0
            ? Array.from({ length: 3 }).map((_, i) => <Placeholder key={i} />)
            : valves.map(v => <ValveTile key={v.valve_id} valve={v} history={history[v.valve_id]} />)}
        </div>
      </section>
    );
  }

  function Placeholder() {
    return <div className={`p-3 rounded-lg ${colors.surface} border ${colors.border} h-40 opacity-50`} />;
  }
  ```

### Task 7: TopBar (ScenarioControls + ModeToggle) + SystemSummary + EventLog
- **IMPLEMENT**:
  ```jsx
  // frontend/src/components/ScenarioControls.jsx
  import { useState } from "react";
  import { api } from "../lib/api";
  import { useDashboardStore } from "../store/useDashboardStore";

  export default function ScenarioControls() {
    const [scenario] = useState("steady_state");
    const [mode, setMode] = useState("chillvalve");
    const addEvent = useDashboardStore(s => s.addEvent);
    const action = async (fn, label) => {
      try { await fn(); addEvent("ctrl", label); }
      catch (e) { addEvent("error", `${label} failed: ${e.message}`); }
    };
    return (
      <div className="flex items-center gap-2">
        <select className="bg-slate-700 px-2 py-1 rounded text-xs" value={scenario} disabled>
          <option value="steady_state">steady_state</option>
        </select>
        <select className="bg-slate-700 px-2 py-1 rounded text-xs" value={mode} onChange={e => setMode(e.target.value)}>
          <option value="belimo">Belimo</option>
          <option value="chillvalve">ChillValve</option>
        </select>
        <Button onClick={() => action(() => api.startScenario(scenario, mode), `start ${scenario}/${mode}`)}>Start</Button>
        <Button onClick={() => action(api.pause, "pause")}>Pause</Button>
        <Button onClick={() => action(api.resume, "resume")}>Resume</Button>
        <Button onClick={() => action(api.reset, "reset")}>Reset</Button>
      </div>
    );
  }

  function Button({ children, ...p }) {
    return <button className="bg-cyan-600 hover:bg-cyan-500 text-slate-900 text-xs font-bold px-2 py-1 rounded" {...p}>{children}</button>;
  }

  // frontend/src/components/ModeToggle.jsx
  import { api } from "../lib/api";
  import { useDashboardStore } from "../store/useDashboardStore";

  export default function ModeToggle() {
    const engineStatus = useDashboardStore(s => s.engineStatus);
    const addEvent = useDashboardStore(s => s.addEvent);
    const mode = engineStatus.mode ?? "—";
    const swap = async (m) => {
      try { await api.setMode(m); addEvent("ctrl", `swap mode → ${m}`); }
      catch (e) { addEvent("error", e.message); }
    };
    return (
      <div className="flex gap-1 text-xs">
        {["belimo", "chillvalve"].map(m => (
          <button
            key={m}
            onClick={() => swap(m)}
            className={`px-2 py-1 rounded ${mode === m ? "bg-cyan-500 text-slate-900" : "bg-slate-700 text-slate-300"}`}
          >
            {m}
          </button>
        ))}
      </div>
    );
  }

  // frontend/src/components/SystemSummary.jsx
  import { useDashboardStore } from "../store/useDashboardStore";
  import { colors } from "../lib/colors";

  export default function SystemSummary() {
    const latest = useDashboardStore(s => s.latest);
    if (!latest) return null;
    return (
      <div className={`p-3 rounded-lg ${colors.surface} border ${colors.border} flex items-center justify-around text-sm`}>
        <Stat label="pump" value={`${latest.pump_kw.toFixed(2)} kW`} />
        <Stat label="head" value={`${latest.pump_head_kpa.toFixed(0)} kPa`} />
        <Stat label="total flow" value={`${latest.total_flow_gpm.toFixed(0)} GPM`} />
        <Stat label="tick" value={`${latest.tick}`} />
      </div>
    );
  }

  function Stat({ label, value }) {
    return (
      <div className="flex flex-col items-center">
        <span className={`text-[10px] uppercase ${colors.textSec}`}>{label}</span>
        <span className="font-mono text-slate-100">{value}</span>
      </div>
    );
  }

  // frontend/src/components/EventLog.jsx
  import { useEffect, useRef } from "react";
  import { useDashboardStore } from "../store/useDashboardStore";
  import { colors } from "../lib/colors";

  export default function EventLog() {
    const events = useDashboardStore(s => s.events);
    const ref = useRef(null);
    useEffect(() => { ref.current?.scrollTo({ top: ref.current.scrollHeight }); }, [events]);
    return (
      <div className={`p-2 rounded-lg ${colors.surface} border ${colors.border} h-32 overflow-y-auto`} ref={ref}>
        {events.length === 0
          ? <div className={`text-xs ${colors.textSec}`}>(no events yet)</div>
          : events.map((e, i) => (
            <div key={i} className="text-xs font-mono">
              <span className={colors.textSec}>{new Date(e.ts).toLocaleTimeString()}</span>{" "}
              <KindBadge kind={e.kind} />{" "}
              <span className={colors.textPrim}>{e.text}</span>
            </div>
          ))}
      </div>
    );
  }

  function KindBadge({ kind }) {
    const map = { rule: "text-rose-400", leader: "text-cyan-400", ctrl: "text-emerald-400", error: "text-amber-400" };
    return <span className={map[kind] ?? "text-slate-400"}>[{kind}]</span>;
  }
  ```

### Task 8: App.jsx + DashboardGrid + main.jsx + index.html
- **IMPLEMENT**:
  ```jsx
  // frontend/src/components/DashboardGrid.jsx
  import BranchRow from "./BranchRow";
  import SystemSummary from "./SystemSummary";
  export default function DashboardGrid() {
    return (
      <div>
        <BranchRow branchId="A" label="CRAH" />
        <BranchRow branchId="B" label="AHU" />
        <SystemSummary />
      </div>
    );
  }

  // frontend/src/App.jsx
  import { useEffect } from "react";
  import { useWebSocket } from "./hooks/useWebSocket";
  import { useDashboardStore } from "./store/useDashboardStore";
  import { api } from "./lib/api";
  import DashboardGrid from "./components/DashboardGrid";
  import EventLog from "./components/EventLog";
  import ScenarioControls from "./components/ScenarioControls";
  import ModeToggle from "./components/ModeToggle";
  import { colors } from "./lib/colors";

  const POLL_HEALTH_MS = 2000;

  export default function App() {
    useWebSocket("ws://localhost:8000/ws");
    const connection = useDashboardStore(s => s.connection);
    const engineStatus = useDashboardStore(s => s.engineStatus);
    const setEngineStatus = useDashboardStore(s => s.setEngineStatus);

    useEffect(() => {
      const tick = async () => {
        try { setEngineStatus(await api.health()); } catch { /* ignore */ }
      };
      tick();
      const id = setInterval(tick, POLL_HEALTH_MS);
      return () => clearInterval(id);
    }, [setEngineStatus]);

    return (
      <div className={`min-h-screen ${colors.bg} ${colors.textPrim} p-4`}>
        <header className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-4">
            <h1 className="text-lg font-bold">ChillValve Dashboard</h1>
            <ConnectionBadge connection={connection} />
            <span className={`text-xs ${colors.textSec}`}>
              engine: {engineStatus.engine} {engineStatus.tick > 0 && `· tick ${engineStatus.tick}`}
            </span>
          </div>
          <div className="flex items-center gap-3">
            <ScenarioControls />
            <ModeToggle />
          </div>
        </header>
        <main className="grid grid-cols-[1fr_320px] gap-4">
          <DashboardGrid />
          <aside className="flex flex-col gap-3">
            <h3 className={`text-xs uppercase ${colors.textSec}`}>Event log</h3>
            <EventLog />
          </aside>
        </main>
      </div>
    );
  }

  function ConnectionBadge({ connection }) {
    const cls = { connected: "bg-emerald-500", connecting: "bg-amber-500", disconnected: "bg-rose-500" }[connection];
    return (
      <span className="flex items-center gap-1 text-xs">
        <span className={`w-2 h-2 rounded-full ${cls}`} />
        {connection}
      </span>
    );
  }

  // frontend/src/main.jsx
  import { StrictMode } from "react";
  import { createRoot } from "react-dom/client";
  import App from "./App";
  import "./index.css";
  createRoot(document.getElementById("root")).render(<StrictMode><App /></StrictMode>);

  // frontend/index.html
  <!DOCTYPE html>
  <html lang="en">
    <head>
      <meta charset="UTF-8" />
      <title>ChillValve Dashboard</title>
    </head>
    <body>
      <div id="root"></div>
      <script type="module" src="/src/main.jsx"></script>
    </body>
  </html>
  ```

### Task 9: Tests (Vitest + RTL)
- **ACTION**: Cover the load-bearing pieces.
- **IMPLEMENT**:
  ```js
  // frontend/src/test-setup.js
  import "@testing-library/jest-dom";

  // frontend/src/store/__tests__/useDashboardStore.test.js
  import { describe, it, expect, beforeEach } from "vitest";
  import { useDashboardStore } from "../useDashboardStore";

  const snap = (tick, valves) => ({ type: "state", tick, pump_kw: 1, pump_head_kpa: 1, total_flow_gpm: 1, valves });
  const valve = (vid, over = {}) => ({
    valve_id: vid, branch_id: vid[0], flow_gpm: 10, dT_C: 5, position_pct: 50,
    is_leader: false, anomaly_detected: false, anomaly_confidence: 0,
    rule_fired: null, safety_override_active: false, ...over,
  });

  describe("dashboard store", () => {
    beforeEach(() => useDashboardStore.setState({ latest: null, history: {}, events: [] }));

    it("captures snapshot and seeds history", () => {
      useDashboardStore.getState().pushSnapshot(snap(0, [valve("A1")]));
      const { latest, history } = useDashboardStore.getState();
      expect(latest.tick).toBe(0);
      expect(history["A1"]).toHaveLength(1);
    });

    it("trims history to 60 ticks per valve", () => {
      for (let t = 0; t < 70; t++) useDashboardStore.getState().pushSnapshot(snap(t, [valve("A1")]));
      expect(useDashboardStore.getState().history["A1"]).toHaveLength(60);
    });

    it("emits a leader-change event when is_leader toggles", () => {
      useDashboardStore.getState().pushSnapshot(snap(0, [valve("A1", { is_leader: false })]));
      useDashboardStore.getState().pushSnapshot(snap(1, [valve("A1", { is_leader: true })]));
      const events = useDashboardStore.getState().events;
      expect(events.some(e => e.kind === "leader")).toBe(true);
    });

    it("emits a rule-fire event on rule_fired transition", () => {
      useDashboardStore.getState().pushSnapshot(snap(0, [valve("A1")]));
      useDashboardStore.getState().pushSnapshot(snap(1, [valve("A1", { rule_fired: "dP_exceeds_600kPa" })]));
      const events = useDashboardStore.getState().events;
      expect(events.some(e => e.kind === "rule" && e.text.includes("dP_exceeds_600kPa"))).toBe(true);
    });
  });

  // frontend/src/components/__tests__/ValveTile.test.jsx
  import { describe, it, expect } from "vitest";
  import { render, screen } from "@testing-library/react";
  import ValveTile from "../ValveTile";

  const baseValve = {
    valve_id: "A1", branch_id: "A", flow_gpm: 21.5, dT_C: 5.0, position_pct: 50,
    is_leader: false, anomaly_detected: false, anomaly_confidence: 0,
    rule_fired: null, safety_override_active: false,
  };

  describe("ValveTile", () => {
    it("renders valve id and metrics", () => {
      render(<ValveTile valve={baseValve} />);
      expect(screen.getByText("A1")).toBeInTheDocument();
      expect(screen.getByText("22")).toBeInTheDocument(); // flow_gpm rounded
      expect(screen.getByText("5.0")).toBeInTheDocument();
    });

    it("shows LEADER badge when is_leader=true", () => {
      render(<ValveTile valve={{ ...baseValve, is_leader: true }} />);
      expect(screen.getByText("LEADER")).toBeInTheDocument();
    });

    it("hides LEADER badge when is_leader=false", () => {
      render(<ValveTile valve={baseValve} />);
      expect(screen.queryByText("LEADER")).not.toBeInTheDocument();
    });
  });
  ```

### Task 10: README + final validation
- **ACTION**: Update root README; verify `npm run build` succeeds; quick browser smoke instructions.
- **IMPLEMENT**: Append to root README:
  ```markdown
  ## Run the dashboard

  ```bash
  cd frontend
  npm install   # first time
  npm run dev   # http://localhost:5173
  ```

  Backend must be running on `localhost:8000`. CORS is pre-configured.
  ```
- **VALIDATE**:
  ```bash
  cd frontend
  npm run lint || true   # vite template lint
  npm run test
  npm run build
  ```
  EXPECT: tests pass; build succeeds (writes `dist/`).

---

## Testing Strategy

### Unit tests (Vitest + RTL)
- Store: snapshot capture, 60-tick trim, leader-change event, rule-fire event (4 cases)
- ValveTile: renders metrics, shows/hides LEADER badge (3 cases)
- Total: ~7 frontend tests

### Manual validation
- [ ] Start backend, open dashboard → ConnectionBadge shows "connected"
- [ ] Click "Start" → 6 valve tiles appear with live metrics updating ~20 Hz
- [ ] LEADER badge appears on A1 and B1 (boot leaders for ChillValve mode)
- [ ] Mini chart shows last 60 ticks of flow
- [ ] Click "Pause" → tick counter freezes; "Reset" → tiles clear
- [ ] Click "belimo" toggle → mode swaps; verify via `/health`
- [ ] Kill backend → ConnectionBadge → "disconnected"; restart backend → auto-reconnect within 10s

---

## Validation Commands

```bash
cd frontend
npm install
npm run test        # vitest, ~7 cases
npm run build       # vite production build
```

EXPECT: tests pass; build emits `dist/` with no errors.

Backend integration:
```bash
# Terminal 1
uv run uvicorn backend.main:app --port 8000

# Terminal 2
cd frontend && npm run dev
# Open http://localhost:5173
```

---

## Acceptance Criteria
- [ ] All 10 tasks completed
- [ ] `npm run build` succeeds
- [ ] `npm run test` green
- [ ] Dashboard renders without console errors
- [ ] WebSocket auto-reconnects after backend restart
- [ ] LEADER badge animates between valves on election
- [ ] Mini charts populate with live data
- [ ] Event log captures rule fires and leader changes
- [ ] PRD §8 color palette respected (no off-palette colors)

## Completion Checklist
- [ ] No TypeScript (per PRD §16 prototype scope)
- [ ] No dependencies beyond the listed set
- [ ] CORS works end-to-end (no console CORS errors)
- [ ] StrictMode-safe (no double-connection in dev)
- [ ] All Tailwind classes used appear in `content` glob
- [ ] No hardcoded port numbers in components beyond `api.js` and `App.jsx`

## Risks
| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Tailwind v3 vs v4 config drift | Low | Medium | Pin `tailwindcss@3` explicitly |
| StrictMode double-connect causes reconnect loop | Medium | Low | Hook cleanup closes socket + `cancelled` flag |
| Recharts re-renders on every snapshot (20 Hz) → CPU burn | Medium | Medium | `isAnimationActive={false}` on Line; small 60-point window keeps work bounded |
| Zustand selectors return new references → unnecessary re-renders | Medium | Low | Select primitive slices (`s.latest`, `s.history`) rather than computed arrays |
| CORS allowed only for `localhost:5173` → fails on 127.0.0.1 | Low | Low | Document in README |
| framer-motion `layoutId` cross-branch leader badge looks weird | Low | Low | `layoutId={`leader-${branch_id}`}` scopes per branch |

## Notes
- Vite dev server uses HMR; Tailwind classes added at runtime work without restart.
- The frontend is a separate npm project, NOT a uv-managed Python module. Two install steps are unavoidable (`uv sync` for backend/sim, `npm install` for frontend).
- We could later add a top-level `Makefile` or `justfile` orchestrating both, but per "Don't add abstractions beyond what the task requires" we hold off.
- WebSocket URL is hardcoded to `ws://localhost:8000/ws`. For deployment beyond localhost, this would become an env var; out of scope for prototype.

---

**Confidence Score: 7/10** — Medium-large React work, mostly mechanical. Risk concentrated in the WebSocket reconnect logic interacting with React StrictMode and Recharts re-render budget at 20 Hz. Plan covers both with explicit mitigations.
