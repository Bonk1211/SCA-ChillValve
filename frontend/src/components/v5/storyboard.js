// 6-step demo storyboard. Whole demo runs in ChillValve mode end-to-end.
// Belimo only used as a static market-reference number for the comparison.
import { api } from "../../lib/api";

export const STORYBOARD = [
  {
    label: "BASELINE",
    headline: "ChillValve cooperative control · steady state",
    detail:
      "Six valves running under multi-agent control. Branch leaders coordinate flow setpoints; Layer-1 safety rules and Layer-2 ML anomaly detection both active. Pump kW + total flow streaming live.",
    onEnter: async () => {
      await api.reset().catch(() => {});
      await api.startScenario("steady_state", "chillvalve");
    },
  },
  {
    label: "FAULT INJECT",
    headline: "Coil fouling injected on AHU-02 (B2)",
    detail:
      "Runtime fault override sets B2 flow capacity to ~15%. Watch B2's flow drop and ΔT drift over the next ~30 seconds.",
    onEnter: async () => {
      await api.injectFault("B2", 0.85);
    },
  },
  {
    label: "ANOMALY DETECTED",
    headline: "Layer 2 ML flags B2",
    detail:
      "Isolation-Forest scoring catches the drift before any Layer-1 rule fires. Anomaly confidence ramps; check the event log.",
    onEnter: async () => {},
  },
  {
    label: "MULTI-AGENT DEBATE",
    headline: "Layer 3 LLM agents debate the reallocation",
    detail:
      "When Layer-2 confidence sits in the uncertain band, the branch peer-valves each speak once and the leader synthesises a new allocation. Real LLM call — transcript lands in the event log as a [debate] line.",
    onEnter: async () => {},
  },
  {
    label: "RECOVERY",
    headline: "Healthy peers compensate · ΔT compliance restored",
    detail:
      "B1 and B3 picked up B2's load using the leader's allocation. Pump kW settles below the Belimo market reference — savings widen on the KPI card.",
    onEnter: async () => {},
  },
  {
    label: "COMPLETE",
    headline: "Demo complete · ChillValve vs Belimo on the right",
    detail:
      "Final pump-kW vs the Belimo datasheet reference (20.5 kW). Press REPLAY to reset the engine and run again.",
    onEnter: async () => {},
  },
];
