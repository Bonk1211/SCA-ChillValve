import { useDashboardStore } from "../store/useDashboardStore";
import { colors } from "../lib/colors";

function Stat({ label, value }) {
  return (
    <div className="flex flex-col items-center">
      <span className={`text-[10px] uppercase ${colors.textSec}`}>{label}</span>
      <span className="font-mono text-slate-100">{value}</span>
    </div>
  );
}

export default function SystemSummary() {
  const latest = useDashboardStore((s) => s.latest);
  if (!latest) return null;
  return (
    <div className={`p-3 rounded-lg ${colors.surface} border ${colors.border} flex items-center justify-around text-sm`}>
      <Stat label="pump" value={`${latest.pump_kw.toFixed(2)} kW`} />
      <Stat label="head" value={`${latest.pump_head_kpa.toFixed(0)} kPa`} />
      <Stat label="total flow" value={`${latest.total_flow_gpm.toFixed(0)} GPM`} />
      <Stat label="tick" value={`${latest.tick}`} />
    </div>
  );
}
