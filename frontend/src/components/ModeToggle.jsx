import { api } from "../lib/api";
import { useDashboardStore } from "../store/useDashboardStore";

export default function ModeToggle() {
  const engineStatus = useDashboardStore((s) => s.engineStatus);
  const addEvent = useDashboardStore((s) => s.addEvent);
  const mode = engineStatus.mode ?? "—";

  const swap = async (m) => {
    try {
      await api.setMode(m);
      addEvent("ctrl", `swap mode → ${m}`);
    } catch (e) {
      addEvent("error", e.message);
    }
  };

  return (
    <div className="flex gap-1 text-xs">
      {["belimo", "chillvalve"].map((m) => (
        <button
          key={m}
          onClick={() => swap(m)}
          className={`px-2 py-1 rounded ${mode === m ? "bg-cyan-500 text-slate-900" : "bg-slate-700 text-slate-300"}`}
        >
          {m}
        </button>
      ))}
    </div>
  );
}
