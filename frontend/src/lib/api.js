const BASE = "http://localhost:8000";

async function post(path, params = {}) {
  const q = new URLSearchParams(params).toString();
  const url = q ? `${BASE}${path}?${q}` : `${BASE}${path}`;
  const r = await fetch(url, { method: "POST" });
  if (!r.ok) throw new Error(`${path}: ${r.status} ${await r.text()}`);
  return r.json();
}

async function get(path) {
  const r = await fetch(`${BASE}${path}`);
  if (!r.ok) throw new Error(`${path}: ${r.status}`);
  return r.json();
}

export const api = {
  startScenario: (name, mode) => post("/scenario/start", { name, mode }),
  pause: () => post("/scenario/pause"),
  resume: () => post("/scenario/resume"),
  reset: () => post("/scenario/reset"),
  setMode: (mode) => post(`/mode/${mode}`),
  killLeader: (vid) => post(`/agent/${vid}/kill_leader`),
  health: () => get("/health"),
};
