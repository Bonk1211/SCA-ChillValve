import { describe, it, expect, beforeEach } from "vitest";
import { useDashboardStore } from "../useDashboardStore";

const valve = (vid, over = {}) => ({
  valve_id: vid,
  branch_id: vid[0],
  flow_gpm: 10,
  dT_C: 5,
  position_pct: 50,
  is_leader: false,
  anomaly_detected: false,
  anomaly_confidence: 0,
  rule_fired: null,
  safety_override_active: false,
  ...over,
});

const snap = (tick, valves) => ({
  type: "state",
  tick,
  pump_kw: 1,
  pump_head_kpa: 1,
  total_flow_gpm: 1,
  valves,
});

describe("dashboard store", () => {
  beforeEach(() =>
    useDashboardStore.setState({ latest: null, history: {}, events: [] }),
  );

  it("captures snapshot and seeds history", () => {
    useDashboardStore.getState().pushSnapshot(snap(0, [valve("A1")]));
    const { latest, history } = useDashboardStore.getState();
    expect(latest.tick).toBe(0);
    expect(history["A1"]).toHaveLength(1);
  });

  it("trims history to 120 ticks per valve", () => {
    for (let t = 0; t < 140; t++) {
      useDashboardStore.getState().pushSnapshot(snap(t, [valve("A1")]));
    }
    expect(useDashboardStore.getState().history["A1"]).toHaveLength(120);
  });

  it("emits a leader-change event when is_leader toggles", () => {
    useDashboardStore.getState().pushSnapshot(snap(0, [valve("A1", { is_leader: false })]));
    useDashboardStore.getState().pushSnapshot(snap(1, [valve("A1", { is_leader: true })]));
    const events = useDashboardStore.getState().events;
    expect(events.some((e) => e.kind === "leader")).toBe(true);
  });

  it("emits a rule-fire event on rule_fired transition", () => {
    useDashboardStore.getState().pushSnapshot(snap(0, [valve("A1")]));
    useDashboardStore
      .getState()
      .pushSnapshot(snap(1, [valve("A1", { rule_fired: "dP_exceeds_600kPa" })]));
    const events = useDashboardStore.getState().events;
    expect(events.some((e) => e.kind === "rule" && e.text.includes("dP_exceeds_600kPa"))).toBe(true);
  });

  it("addEvent appends to event log", () => {
    useDashboardStore.getState().addEvent("ctrl", "test event");
    const events = useDashboardStore.getState().events;
    expect(events).toHaveLength(1);
    expect(events[0].text).toBe("test event");
  });
});
