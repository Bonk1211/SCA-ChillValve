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
            text: `branch ${v.branch_id}: ${txt}`,
          });
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

  reset: () => set({ latest: null, history: {}, events: [] }),
}));
