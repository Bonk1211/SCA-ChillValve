import { useState } from "react";
import { api } from "../lib/api";
import { useDashboardStore } from "../store/useDashboardStore";

function Button({ children, ...props }) {
  return (
    <button
      className="bg-cyan-600 hover:bg-cyan-500 text-slate-900 text-xs font-bold px-2 py-1 rounded"
      {...props}
    >
      {children}
    </button>
  );
}

export default function ScenarioControls() {
  const [scenario] = useState("steady_state");
  const [mode, setMode] = useState("chillvalve");
  const addEvent = useDashboardStore((s) => s.addEvent);
  const reset = useDashboardStore((s) => s.reset);

  const action = async (fn, label) => {
    try {
      await fn();
      addEvent("ctrl", label);
    } catch (e) {
      addEvent("error", `${label} failed: ${e.message}`);
    }
  };

  return (
    <div className="flex items-center gap-2">
      <select className="bg-slate-700 px-2 py-1 rounded text-xs" value={scenario} disabled>
        <option value="steady_state">steady_state</option>
      </select>
      <select
        className="bg-slate-700 px-2 py-1 rounded text-xs"
        value={mode}
        onChange={(e) => setMode(e.target.value)}
      >
        <option value="belimo">Belimo</option>
        <option value="chillvalve">ChillValve</option>
      </select>
      <Button onClick={() => action(() => api.startScenario(scenario, mode), `start ${scenario}/${mode}`)}>
        Start
      </Button>
      <Button onClick={() => action(api.pause, "pause")}>Pause</Button>
      <Button onClick={() => action(api.resume, "resume")}>Resume</Button>
      <Button
        onClick={() => {
          reset();
          action(api.reset, "reset");
        }}
      >
        Reset
      </Button>
    </div>
  );
}
