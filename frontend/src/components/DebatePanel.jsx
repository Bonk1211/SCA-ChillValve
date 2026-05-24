import { useEffect, useRef } from "react";
import { useDashboardStore } from "../store/useDashboardStore";
import { colors } from "../lib/colors";

function Speech({ valve_id, text }) {
  return (
    <div className="text-xs">
      <span className="font-mono text-violet-400">{valve_id}:</span>{" "}
      <span className={colors.textPrim}>{text}</span>
    </div>
  );
}

function DebateCard({ debate }) {
  return (
    <div
      className={`p-2 rounded-lg ${colors.surface} border ${colors.border} mb-2 flex flex-col gap-1`}
    >
      <div className="flex items-center justify-between">
        <span className={`text-[10px] uppercase ${colors.textSec}`}>
          tick {debate.tick} · branch {debate.branch_id} · leader {debate.leader_id}
          {debate.cached && <span className="ml-1 text-amber-400">[cached]</span>}
        </span>
        <span className={`text-[10px] ${colors.textSec}`}>
          {debate.wall_clock_s}s
        </span>
      </div>
      <div className="flex flex-col gap-0.5 pl-2 border-l-2 border-violet-700">
        {debate.speeches.map((s, i) => (
          <Speech key={i} {...s} />
        ))}
      </div>
      <div className="text-xs italic text-emerald-300 pl-2 mt-1">
        ↳ {debate.rationale}
      </div>
      <div className="text-[10px] font-mono text-cyan-300 pl-2">
        allocations: {Object.entries(debate.allocations)
          .map(([k, v]) => `${k}=${v.toFixed(0)}%`)
          .join(", ")}
      </div>
    </div>
  );
}

export default function DebatePanel() {
  const debates = useDashboardStore((s) => s.debates);
  const ref = useRef(null);

  useEffect(() => {
    ref.current?.scrollTo({ top: ref.current.scrollHeight });
  }, [debates]);

  return (
    <div className="flex flex-col gap-1">
      <h3 className={`text-xs uppercase ${colors.textSec}`}>
        Debate transcript{" "}
        <span className="text-violet-400 text-[10px]">(LLM Layer 3)</span>
      </h3>
      <div
        ref={ref}
        className={`p-2 rounded-lg ${colors.surface} border ${colors.border} h-64 overflow-y-auto`}
      >
        {debates.length === 0 ? (
          <div className={`text-xs ${colors.textSec}`}>
            (no debates yet — fires when Layer 2 confidence in [0.3, 0.85])
          </div>
        ) : (
          debates.map((d, i) => <DebateCard key={i} debate={d} />)
        )}
      </div>
    </div>
  );
}
