import { create } from "zustand";

const HISTORY_LIMIT = 120;   // ~6s at 20Hz — enough to see a fault ramp on the live chart
const EVENT_LIMIT = 100;

export const useDashboardStore = create((set, get) => ({
  connection: "disconnected",
  latest: null,
  history: {},
  events: [],
  debates: [],
  engineStatus: { engine: "idle", tick: 0, scenario: null, mode: null },
  latestRemediation: null,
  latestSummary: null,
  // User-controlled visibility for the SummaryBanner modal. Set true by the
  // "SHOW RESULT" button in ControlBar; cleared by close/ESC/backdrop and by
  // reset() so REPLAY hides any stale modal.
  summaryVisible: false,

  setConnection: (c) => set({ connection: c }),
  setEngineStatus: (s) => set({ engineStatus: s }),
  showSummary: () => set({ summaryVisible: true }),
  hideSummary: () => set({ summaryVisible: false }),

  pushSnapshot: (snap) => {
    const state = get();
    const history = { ...state.history };
    for (const v of snap.valves) {
      const arr = history[v.valve_id] || [];
      const next = [...arr, { tick: snap.tick, flow_gpm: v.flow_gpm, dT_C: v.dT_C }];
      history[v.valve_id] = next.slice(-HISTORY_LIMIT);
    }
    const events = [...state.events];
    if (state.latest) {
      for (const v of snap.valves) {
        const prev = state.latest.valves.find((p) => p.valve_id === v.valve_id);
        if (v.rule_fired && (!prev || prev.rule_fired !== v.rule_fired)) {
          events.push({
            ts: Date.now(),
            kind: "rule",
            text: `${v.valve_id} rule fired: ${v.rule_fired}`,
          });
        }
        if (v.anomaly_detected && (!prev || !prev.anomaly_detected)) {
          events.push({
            ts: Date.now(),
            kind: "anomaly",
            text: `${v.valve_id} Layer-2 anomaly · conf ${(v.anomaly_confidence * 100).toFixed(0)}%`,
          });
        }
        if (prev && prev.is_leader !== v.is_leader) {
          const txt = v.is_leader ? `leader → ${v.valve_id}` : `${v.valve_id} stepped down`;
          events.push({
            ts: Date.now(),
            kind: "leader",
            branch_id: v.branch_id,
            new_leader: v.is_leader ? v.valve_id : null,
            text: `branch ${v.branch_id}: ${txt}`,
          });
        }
      }
    }
    while (events.length > EVENT_LIMIT) events.shift();
    set({ latest: snap, history, events });
  },

  pushExplanation: (msg) => {
    // Attach to the most recent matching leader event in the log.
    const events = [...get().events];
    for (let i = events.length - 1; i >= 0; i--) {
      const e = events[i];
      if (
        e.kind === "leader" &&
        e.branch_id === msg.branch_id &&
        e.new_leader === msg.new_leader &&
        !e.explanation
      ) {
        events[i] = { ...e, explanation: msg.text };
        set({ events });
        return;
      }
    }
    // No matching event — append a standalone explanation entry.
    events.push({
      ts: Date.now(),
      kind: "leader",
      branch_id: msg.branch_id,
      new_leader: msg.new_leader,
      text: `branch ${msg.branch_id}: ${msg.previous_leader ?? "(none)"} → ${msg.new_leader} (${msg.cause})`,
      explanation: msg.text,
    });
    while (events.length > EVENT_LIMIT) events.shift();
    set({ events });
  },

  addEvent: (kind, text) => {
    const events = [...get().events, { ts: Date.now(), kind, text }];
    while (events.length > EVENT_LIMIT) events.shift();
    set({ events });
  },

  pushDebate: (msg) => {
    const debates = [...get().debates, msg];
    while (debates.length > 30) debates.shift();   // keep last 30 transcripts
    const allocSummary = Object.entries(msg.allocations || {})
      .map(([vid, pos]) => `${vid}=${Number(pos).toFixed(0)}%`)
      .join(", ");
    const events = [...get().events, {
      ts: Date.now(),
      kind: "debate",
      text: `branch ${msg.branch_id} debate (${msg.leader_id} leader): ${allocSummary} — ${msg.rationale}`,
    }];
    while (events.length > EVENT_LIMIT) events.shift();
    set({ debates, events });
  },

  pushSummary: (msg) => {
    // End-of-run energy summary — measured pump-kW per phase + recovery
    // savings. Stored separately from events so the SummaryBanner can show
    // it indefinitely after engine goes idle.
    const events = [...get().events, {
      ts: Date.now(),
      kind: "story",
      text: `scenario complete · ${msg.total_kwh.toFixed(3)} kWh total · L3 recovery saved ${msg.recovery_savings_kwh.toFixed(3)} kWh`,
    }];
    while (events.length > EVENT_LIMIT) events.shift();
    set({ events, latestSummary: msg });
  },

  pushRemediation: (msg) => {
    const actionLabel = (msg.action || "").replaceAll("_", " ").toUpperCase();
    const events = [...get().events, {
      ts: Date.now(),
      kind: "remediation",
      text: `${msg.target_valve_id} · LEADER → ${actionLabel}${msg.executed ? "" : " (recorded only)"} — ${msg.rationale}`,
    }];
    while (events.length > EVENT_LIMIT) events.shift();
    set({ events, latestRemediation: msg });
  },

  reset: () =>
    set({
      latest: null,
      history: {},
      events: [],
      debates: [],
      latestRemediation: null,
      latestSummary: null,
      summaryVisible: false,
    }),
}));
