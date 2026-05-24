import { motion } from "framer-motion";
import { colors } from "../lib/colors";
import { api } from "../lib/api";
import LayerIndicator from "./LayerIndicator";
import MiniChart from "./MiniChart";
import { useDashboardStore } from "../store/useDashboardStore";

function bandColor(value, healthy, warning) {
  const [lo, hi] = healthy;
  if (value >= lo && value <= hi) return colors.healthy;
  const [wlo, whi] = warning;
  if (value >= wlo && value <= whi) return colors.warning;
  return colors.critical;
}

function Metric({ label, value, unit, color }) {
  return (
    <div className="flex flex-col">
      <span className={`text-[10px] ${colors.textSec}`}>{label}</span>
      <span className={color || colors.textPrim}>
        {value}
        <span className={`ml-0.5 text-[10px] ${colors.textSec}`}>{unit}</span>
      </span>
    </div>
  );
}

export default function ValveTile({ valve, history = [] }) {
  const addEvent = useDashboardStore((s) => s.addEvent);

  const onKillLeader = async () => {
    try {
      await api.killLeader(valve.valve_id);
      addEvent("ctrl", `kill leader → ${valve.valve_id}`);
    } catch (e) {
      addEvent("error", `kill leader failed: ${e.message}`);
    }
  };

  // Status bands tuned to design ΔT = 5°C and per-spec valve flow.
  const dtColor = bandColor(valve.dT_C, [4.0, 6.0], [3.0, 7.0]);
  const posColor = bandColor(valve.position_pct, [20, 80], [10, 95]);
  // Anomaly-aware border: rose if rule fired, amber if Layer 2 hot.
  const borderClass = valve.safety_override_active
    ? "border-rose-500"
    : valve.anomaly_detected
      ? "border-amber-500"
      : colors.border;

  return (
    <motion.div
      layout
      className={`p-3 rounded-lg ${colors.surface} border ${borderClass} flex flex-col gap-2 transition-colors`}
    >
      <div className="flex items-center justify-between">
        <span className={`font-mono text-sm ${colors.textPrim}`}>{valve.valve_id}</span>
        {valve.is_leader && (
          <div className="flex items-center gap-1">
            <motion.span
              layoutId={`leader-${valve.branch_id}`}
              className={`text-[10px] px-1.5 py-0.5 rounded ${colors.leader} font-bold`}
            >
              LEADER
            </motion.span>
            <button
              onClick={onKillLeader}
              title="Kill leader (test failover)"
              className="text-[10px] text-rose-400 hover:text-rose-300 px-1"
            >
              ✕
            </button>
          </div>
        )}
      </div>
      <div className="grid grid-cols-3 gap-1 text-xs">
        <Metric label="flow" value={`${valve.flow_gpm.toFixed(0)}`} unit="GPM" />
        <Metric label="ΔT" value={valve.dT_C.toFixed(1)} unit="°C" color={dtColor} />
        <Metric label="pos" value={`${valve.position_pct.toFixed(0)}`} unit="%" color={posColor} />
      </div>
      <div className="flex gap-3 justify-center">
        <LayerIndicator
          layer="L1"
          active={!!valve.rule_fired}
          label={valve.rule_fired || "Layer 1 — rules"}
        />
        <LayerIndicator
          layer="L2"
          active={valve.anomaly_detected}
          intensity={valve.anomaly_confidence}
          label={`Layer 2 — anomaly conf ${(valve.anomaly_confidence * 100).toFixed(0)}%`}
        />
        <LayerIndicator layer="L3" active={true} label="Layer 3 — coordination" />
      </div>
      <MiniChart data={history} dataKey="flow_gpm" />
    </motion.div>
  );
}
