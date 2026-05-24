import { create } from "zustand";

const HISTORY_LIMIT = 60;
const EVENT_LIMIT = 100;

export const useDashboardStore = create((set, get) => ({
  connection: "disconnected",
  latest: null,
  history: {},
  events: [],
  engineStatus: { engine: "idle", tick: 0, scenario: null, mode: null },

  setConnection: (c) => set({ connection: c }),
  setEngineStatus: (s) => set({ engineStatus: s }),

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

  reset: () => set({ latest: null, history: {}, events: [] }),
}));
