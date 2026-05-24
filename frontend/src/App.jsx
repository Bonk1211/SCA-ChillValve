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

function ConnectionBadge({ connection }) {
  const cls =
    { connected: "bg-emerald-500", connecting: "bg-amber-500", disconnected: "bg-rose-500" }[
      connection
    ] ?? "bg-slate-500";
  return (
    <span className="flex items-center gap-1 text-xs">
      <span className={`w-2 h-2 rounded-full ${cls}`} />
      {connection}
    </span>
  );
}

export default function App() {
  useWebSocket("ws://localhost:8000/ws");
  const connection = useDashboardStore((s) => s.connection);
  const engineStatus = useDashboardStore((s) => s.engineStatus);
  const setEngineStatus = useDashboardStore((s) => s.setEngineStatus);

  useEffect(() => {
    const tick = async () => {
      try {
        setEngineStatus(await api.health());
      } catch {
        /* backend down — ignore */
      }
    };
    tick();
    const id = setInterval(tick, POLL_HEALTH_MS);
    return () => clearInterval(id);
  }, [setEngineStatus]);

  return (
    <div className={`min-h-screen ${colors.bg} ${colors.textPrim} p-4`}>
      <header className="flex items-center justify-between mb-4 gap-4 flex-wrap">
        <div className="flex items-center gap-4">
          <h1 className="text-lg font-bold">ChillValve Dashboard</h1>
          <ConnectionBadge connection={connection} />
          <span className={`text-xs ${colors.textSec}`}>
            engine: {engineStatus.engine}
            {engineStatus.tick > 0 && ` · tick ${engineStatus.tick}`}
            {engineStatus.mode && ` · ${engineStatus.mode}`}
          </span>
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          <ScenarioControls />
          <ModeToggle />
        </div>
      </header>
      <main className="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-4">
        <DashboardGrid />
        <aside className="flex flex-col gap-3">
          <h3 className={`text-xs uppercase ${colors.textSec}`}>Event log</h3>
          <EventLog />
        </aside>
      </main>
    </div>
  );
}
