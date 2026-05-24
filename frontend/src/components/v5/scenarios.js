// Single demo scenario — full L1+L2+L3 run with an obvious flow spike.
// Engine runs autonomously to duration_seconds; no manual stepping.
import { api } from "../../lib/api";

export const SCENARIOS = [
  {
    id: "full_run",
    label: "FULL RUN · L1+L2+L3",
    headline: "AHU-02 valve spike — full 3-layer response",
    detail:
      "B2 chokes from 100% → 8% capacity over 28 seconds (starts t=12s). At base load 0.95 the pump tries to maintain flow, dP across B2 spikes past the 600 kPa failsafe → L1 emergency-closes B2. L2 ML rises through uncertain band [0.30, 0.85] over ~10s → L3 debate fires. Peers (B1 + B3) self-calibrate to absorb B2's load.",
    backendName: "demo_full_run",
    expectedLayers: ["L1", "L2", "L3"],
    durationS: 240,
    accent: "#22d3ee",
    watchFor: [
      "t=12-40s : B2 sparkline plunges — biggest spike on screen",
      "t≈20-30s : L2 anomaly confidence climbs into uncertain band",
      "t≈25-35s : L3 debate fires — LLM transcript streams into the stage",
      "t≈35-45s : L1 dP rule trips red on B2 → safety override forces close",
      "t≈40s+ : B1 + B3 sparklines climb as peers pick up B2's load",
      "t≈90s+ : ΔT compliance KPI recovers without operator action",
      "t≈100s+ : LLM recovery decision restores B2 flow autonomously",
    ],
  },
];

export const SCENARIO_BY_ID = Object.fromEntries(SCENARIOS.map((s) => [s.id, s]));

const _BY_BACKEND_NAME = Object.fromEntries(SCENARIOS.map((s) => [s.backendName, s.id]));

/** Map a backend scenario `name` (as returned by /health) back to a UI id.
 *  Returns null if the running backend scenario isn't one we know about. */
export function reverseScenarioLookup(backendName) {
  return _BY_BACKEND_NAME[backendName] || null;
}

/** Start the scenario in chillvalve mode. Engine auto-runs to duration. */
export async function runScenario(id) {
  const s = SCENARIO_BY_ID[id];
  if (!s) throw new Error(`unknown scenario: ${id}`);
  // Log reset failures rather than silently swallowing them — startScenario
  // can succeed on a half-reset backend and produce a corrupted demo run.
  await api.reset().catch((e) => {
    console.warn("[scenarios] api.reset failed before startScenario:", e);
  });
  await api.startScenario(s.backendName, "chillvalve");
  return s;
}
