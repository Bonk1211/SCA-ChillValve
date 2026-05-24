import { motion } from "framer-motion";
import { colors } from "../lib/colors";
import LayerIndicator from "./LayerIndicator";
import MiniChart from "./MiniChart";

function Metric({ label, value, unit }) {
  return (
    <div className="flex flex-col">
      <span className={`text-[10px] ${colors.textSec}`}>{label}</span>
      <span className={colors.textPrim}>
        {value}
        <span className={`ml-0.5 text-[10px] ${colors.textSec}`}>{unit}</span>
      </span>
    </div>
  );
}

export default function ValveTile({ valve, history = [] }) {
  return (
    <div className={`p-3 rounded-lg ${colors.surface} border ${colors.border} flex flex-col gap-2`}>
      <div className="flex items-center justify-between">
        <span className={`font-mono text-sm ${colors.textPrim}`}>{valve.valve_id}</span>
        {valve.is_leader && (
          <motion.span
            layoutId={`leader-${valve.branch_id}`}
            className={`text-[10px] px-1.5 py-0.5 rounded ${colors.leader} font-bold`}
          >
            LEADER
          </motion.span>
        )}
      </div>
      <div className="grid grid-cols-3 gap-1 text-xs">
        <Metric label="flow" value={`${valve.flow_gpm.toFixed(0)}`} unit="GPM" />
        <Metric label="ΔT" value={valve.dT_C.toFixed(1)} unit="°C" />
        <Metric label="pos" value={`${valve.position_pct.toFixed(0)}`} unit="%" />
      </div>
      <div className="flex gap-3 justify-center">
        <LayerIndicator layer="L1" active={!!valve.rule_fired} label={valve.rule_fired || "Layer 1 — rules"} />
        <LayerIndicator
          layer="L2"
          active={valve.anomaly_detected}
          intensity={valve.anomaly_confidence}
          label="Layer 2 — ML"
        />
        <LayerIndicator layer="L3" active={true} label="Layer 3 — coordination" />
      </div>
      <MiniChart data={history} dataKey="flow_gpm" />
    </div>
  );
}
