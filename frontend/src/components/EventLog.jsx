import { useEffect, useRef } from "react";
import { useDashboardStore } from "../store/useDashboardStore";
import { colors } from "../lib/colors";

function KindBadge({ kind }) {
  const map = {
    rule: "text-rose-400",
    leader: "text-cyan-400",
    ctrl: "text-emerald-400",
    error: "text-amber-400",
  };
  return <span className={map[kind] ?? "text-slate-400"}>[{kind}]</span>;
}

export default function EventLog() {
  const events = useDashboardStore((s) => s.events);
  const ref = useRef(null);
  useEffect(() => {
    ref.current?.scrollTo({ top: ref.current.scrollHeight });
  }, [events]);
  return (
    <div className={`p-2 rounded-lg ${colors.surface} border ${colors.border} h-64 overflow-y-auto`} ref={ref}>
      {events.length === 0 ? (
        <div className={`text-xs ${colors.textSec}`}>(no events yet)</div>
      ) : (
        events.map((e, i) => (
          <div key={i} className="text-xs font-mono">
            <span className={colors.textSec}>{new Date(e.ts).toLocaleTimeString()}</span>{" "}
            <KindBadge kind={e.kind} />{" "}
            <span className={colors.textPrim}>{e.text}</span>
          </div>
        ))
      )}
    </div>
  );
}
