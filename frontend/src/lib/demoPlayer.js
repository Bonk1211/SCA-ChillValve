// Hardcoded demo runner. Schedules scripted WS-shaped messages into the
// dashboard store via setTimeout. Used when the UI is in DEMO mode so the
// demo flow is bulletproof for D-Day (no backend or LLM needed).
//
// Lifecycle:
//   start() — clears store, runs the timeline
//   stop()  — cancels pending timers, marks engine idle
//   reset() — stop + clear store
//
// Player is a module-level singleton because App.jsx remounts on hot-reload
// and we want to cancel old timers from the previous instance.
import { useDashboardStore } from "../store/useDashboardStore";
import {
  buildDemoTimeline,
  DEMO_DURATION_S,
  DEMO_SCENARIO_NAME,
} from "./demoTimeline";

class DemoPlayer {
  constructor() {
    this.timers = [];
    this.running = false;
  }

  start() {
    if (this.running) return;
    this.running = true;
    const store = useDashboardStore.getState();
    store.reset();
    store.setEngineStatus({
      engine: "running",
      tick: 0,
      scenario: DEMO_SCENARIO_NAME,
      mode: "chillvalve",
    });
    if (typeof store.addEvent === "function") {
      store.addEvent("story", `DEMO mode started · ${DEMO_SCENARIO_NAME}`);
    }
    const events = buildDemoTimeline();
    for (const { at_ms, message } of events) {
      const id = setTimeout(() => this._dispatch(message), at_ms);
      this.timers.push(id);
    }
    const endId = setTimeout(() => {
      const s = useDashboardStore.getState();
      s.setEngineStatus({
        engine: "idle",
        tick: DEMO_DURATION_S,
        scenario: DEMO_SCENARIO_NAME,
        mode: "chillvalve",
      });
      this.running = false;
    }, (DEMO_DURATION_S + 1) * 1000);
    this.timers.push(endId);
  }

  _dispatch(msg) {
    const store = useDashboardStore.getState();
    if (msg.type === "debate") store.pushDebate(msg);
    else if (msg.type === "remediation") store.pushRemediation(msg);
    else if (msg.type === "summary") store.pushSummary(msg);
    else {
      store.pushSnapshot(msg);
      store.setEngineStatus({
        engine: "running",
        tick: msg.tick,
        scenario: DEMO_SCENARIO_NAME,
        mode: "chillvalve",
      });
    }
  }

  stop() {
    for (const id of this.timers) clearTimeout(id);
    this.timers = [];
    this.running = false;
    const store = useDashboardStore.getState();
    store.setEngineStatus({
      engine: "idle",
      tick: 0,
      scenario: null,
      mode: null,
    });
  }

  reset() {
    this.stop();
    useDashboardStore.getState().reset();
  }
}

export const demoPlayer = new DemoPlayer();
