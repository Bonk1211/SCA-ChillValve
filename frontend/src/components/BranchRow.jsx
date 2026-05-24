import { colors } from "../lib/colors";
import ValveTile from "./ValveTile";
import { useDashboardStore } from "../store/useDashboardStore";

function Placeholder() {
  return <div className={`p-3 rounded-lg ${colors.surface} border ${colors.border} h-40 opacity-50`} />;
}

export default function BranchRow({ branchId, label }) {
  const latest = useDashboardStore((s) => s.latest);
  const history = useDashboardStore((s) => s.history);
  const valves = latest?.valves?.filter((v) => v.branch_id === branchId) ?? [];
  return (
    <section className="mb-4">
      <h2 className={`text-sm uppercase tracking-wide mb-2 ${colors.textSec}`}>
        Branch {branchId} — {label}
      </h2>
      <div className="grid grid-cols-3 gap-3">
        {valves.length === 0
          ? Array.from({ length: 3 }).map((_, i) => <Placeholder key={i} />)
          : valves.map((v) => (
              <ValveTile key={v.valve_id} valve={v} history={history[v.valve_id]} />
            ))}
      </div>
    </section>
  );
}
