import { useDashboardStore } from "../../store/useDashboardStore";
import { VALVE_BY_ID, VALVES } from "../../lib/valveConfig";

const EMPTY_VALVES = VALVES.map((v) => ({
  valve_id: v.id,
  branch_id: v.branch,
  flow_gpm: 0,
  dT_C: 0,
  position_pct: 50,
  is_leader: false,
  anomaly_detected: false,
  anomaly_confidence: 0,
  rule_fired: null,
  safety_override_active: false,
}));

function FlowPath({ d, flow, hot, thick = 6 }) {
  const speed = Math.max(0.15, flow * 3);
  const duration = `${(2 / speed).toFixed(2)}s`;
  const baseColor = hot ? "#f97316" : "#2dd4ff";
  const glowColor = hot ? "rgba(249, 115, 22, 0.4)" : "rgba(45, 212, 255, 0.5)";
  return (
    <g>
      <path d={d} stroke="#2d3d5e" strokeWidth={thick + 6} fill="none" strokeLinecap="round" strokeLinejoin="round" />
      <path d={d} stroke="#131f37" strokeWidth={thick + 2} fill="none" strokeLinecap="round" strokeLinejoin="round" />
      <path
        d={d}
        stroke={baseColor}
        strokeWidth={thick}
        fill="none"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeDasharray="8 14"
        opacity={0.85}
        style={{
          animation: `flowDash ${duration} linear infinite`,
          filter: `drop-shadow(0 0 4px ${glowColor})`,
        }}
      />
    </g>
  );
}

function Valve({ x, y, valve, onClick, selected }) {
  const pos = valve.position_pct / 100;
  const angle = 90 - pos * 90;
  const stateColor = valve.safety_override_active
    ? "#f87171"
    : valve.anomaly_detected
    ? "#fbbf24"
    : "#34d399";
  const leaderGlow = valve.is_leader ? "drop-shadow(0 0 6px rgba(34, 211, 238, 0.7))" : "none";
  return (
    <g transform={`translate(${x}, ${y})`} style={{ cursor: "pointer" }} onClick={onClick}>
      {selected && (
        <circle r="28" fill="none" stroke="#22d3ee" strokeWidth="1.5" strokeDasharray="3 3" opacity="0.7">
          <animateTransform attributeName="transform" type="rotate" from="0" to="360" dur="8s" repeatCount="indefinite" />
        </circle>
      )}
      <g style={{ filter: leaderGlow }}>
        <polygon points="-16,-12 -16,12 0,0 16,12 16,-12 0,0" fill="#1a2640" stroke={stateColor} strokeWidth="1.5" strokeLinejoin="round" />
        <line x1="0" y1="-18" x2="0" y2="-12" stroke={stateColor} strokeWidth="1.5" />
        <rect x="-4" y="-22" width="8" height="4" fill={stateColor} rx="1" />
        <line x1="0" y1="-7" x2="0" y2="7" stroke={stateColor} strokeWidth="2.5" strokeLinecap="round" transform={`rotate(${angle})`} />
      </g>
      {valve.is_leader && (
        <g transform="translate(0, -34)">
          <rect x="-16" y="-7" width="32" height="11" rx="2" fill="#22d3ee" />
          <text x="0" y="1" textAnchor="middle" fontFamily="JetBrains Mono, monospace" fontSize="8" fontWeight="700" fill="#0a1224">LEADER</text>
        </g>
      )}
      <text x="0" y="38" textAnchor="middle" fontFamily="JetBrains Mono, monospace" fontSize="11" fontWeight="600" fill="#ffffff">{valve.valve_id}</text>
      <text x="0" y="52" textAnchor="middle" fontFamily="JetBrains Mono, monospace" fontSize="9" fill="#d1dcec">{valve.flow_gpm.toFixed(0)} GPM</text>
      <g transform="translate(-18, 60)">
        <rect width="36" height="3" rx="1.5" fill="#2d3d5e" />
        <rect width={36 * pos} height="3" rx="1.5" fill={stateColor} opacity="0.8" />
      </g>
    </g>
  );
}

function Pump({ x, y, kW, totalFlow }) {
  const rpmPct = Math.min(100, (totalFlow / 600) * 100);
  const dur = `${(1.2 - (rpmPct / 100) * 1.0).toFixed(2)}s`;
  return (
    <g transform={`translate(${x}, ${y})`}>
      <circle r="28" fill="#1a2640" stroke="#445574" strokeWidth="1.5" />
      <circle r="22" fill="none" stroke="#2d3d5e" strokeWidth="1" />
      <g style={{ animation: `pumpSpin ${dur} linear infinite`, transformOrigin: "0 0" }}>
        <path d="M 0,0 L 18,4 L 14,-2 Z" fill="#2dd4ff" opacity="0.85" />
        <path d="M 0,0 L -4,18 L 2,14 Z" fill="#2dd4ff" opacity="0.85" />
        <path d="M 0,0 L -18,-4 L -14,2 Z" fill="#2dd4ff" opacity="0.85" />
        <path d="M 0,0 L 4,-18 L -2,-14 Z" fill="#2dd4ff" opacity="0.85" />
        <circle r="3" fill="#2dd4ff" />
      </g>
      <text x="0" y="50" textAnchor="middle" fontFamily="JetBrains Mono, monospace" fontSize="10" fontWeight="600" fill="#ffffff">PUMP P-01</text>
      <text x="0" y="62" textAnchor="middle" fontFamily="JetBrains Mono, monospace" fontSize="9" fill="#2dd4ff">{kW.toFixed(2)} kW</text>
    </g>
  );
}

function Coil({ x, y, label, sub, dT }) {
  const dev = Math.abs(dT - 5.0);
  const color = dev <= 0.7 ? "#34d399" : dev <= 1.5 ? "#fbbf24" : "#f87171";
  return (
    <g transform={`translate(${x}, ${y})`}>
      <rect x="-30" y="-18" width="60" height="36" rx="3" fill="#1a2640" stroke="#445574" strokeWidth="1" />
      <path
        d="M -22,-10 L 22,-10 M 22,-10 Q 26,-10 26,-6 Q 26,-2 22,-2 L -22,-2 Q -26,-2 -26,2 Q -26,6 -22,6 L 22,6 Q 26,6 26,10 Q 26,14 22,14 L -22,14"
        stroke={color}
        strokeWidth="1.4"
        fill="none"
        opacity="0.9"
      />
      <text x="0" y="32" textAnchor="middle" fontFamily="JetBrains Mono, monospace" fontSize="9" fontWeight="600" fill="#ffffff">{label}</text>
      {sub && <text x="0" y="42" textAnchor="middle" fontFamily="JetBrains Mono, monospace" fontSize="8" fill="#9aacc8">{sub}</text>}
    </g>
  );
}

export default function Schematic({ selectedValveId, onSelectValve }) {
  const latest = useDashboardStore((s) => s.latest);
  const valves = latest?.valves ?? EMPTY_VALVES;
  const pump_kw = latest?.pump_kw ?? 0;
  const pump_head_kpa = latest?.pump_head_kpa ?? 0;
  const total_flow_gpm = latest?.total_flow_gpm ?? 0;

  const W = 1140;
  const H = 460;
  const valvesById = Object.fromEntries(valves.map((v) => [v.valve_id, v]));
  const xA = [310, 430, 550];
  const xB = [720, 850, 980];
  const xOf = (v) => (v.branch_id === "A" ? xA : xB)[parseInt(v.valve_id[1], 10) - 1];
  const supplyY = 95;
  const valveY = 175;
  const coilY = 250;
  const returnY = 360;
  const pumpX = 175;
  const pumpY = 230;
  const chillerX = 70;

  const totalFlowNorm = total_flow_gpm / 600;
  const flowA = ["A1", "A2", "A3"].reduce((s, id) => s + (valvesById[id]?.flow_gpm ?? 0), 0);
  const flowB = ["B1", "B2", "B3"].reduce((s, id) => s + (valvesById[id]?.flow_gpm ?? 0), 0);
  const avgReturnTemp =
    7.0 + valves.reduce((s, v) => s + v.dT_C * v.flow_gpm, 0) / Math.max(1, total_flow_gpm);

  return (
    <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="xMidYMid meet" style={{ width: "100%", height: "100%", maxHeight: "100%", display: "block" }}>
      <g fontFamily="JetBrains Mono, monospace" fontSize="9" fill="#9aacc8">
        <text x="20" y="24">// CHILLED WATER LOOP · 5MW TIER 3</text>
        <text x={W - 20} y="24" textAnchor="end">P&amp;ID · LIVE</text>
      </g>

      <g transform={`translate(${chillerX}, ${pumpY})`}>
        <rect x="-46" y="-46" width="92" height="92" rx="4" fill="#1a2640" stroke="#445574" />
        <text x="0" y="-24" textAnchor="middle" fontFamily="JetBrains Mono, monospace" fontSize="9" fontWeight="600" fill="#d1dcec">CHILLER</text>
        <g transform="translate(0, -6)">
          <text x="0" y="0" textAnchor="middle" fontFamily="JetBrains Mono, monospace" fontSize="7" fill="#9aacc8">supply</text>
          <text x="0" y="12" textAnchor="middle" fontFamily="JetBrains Mono, monospace" fontSize="14" fontWeight="700" fill="#2dd4ff">7.0°C</text>
        </g>
        <g transform="translate(0, 28)">
          <text x="0" y="0" textAnchor="middle" fontFamily="JetBrains Mono, monospace" fontSize="7" fill="#9aacc8">return</text>
          <text x="0" y="11" textAnchor="middle" fontFamily="JetBrains Mono, monospace" fontSize="11" fontWeight="700" fill="#f97316">
            {avgReturnTemp.toFixed(1)}°C
          </text>
        </g>
      </g>

      <FlowPath d={`M ${chillerX + 46},${pumpY - 18} L ${pumpX - 28},${pumpY - 18} L ${pumpX - 28},${pumpY - 6} L ${pumpX - 20},${pumpY}`} flow={totalFlowNorm} thick={5} />
      <FlowPath d={`M ${pumpX - 20},${pumpY + 8} L ${pumpX - 28},${pumpY + 14} L ${pumpX - 28},${pumpY + 18} L ${chillerX + 46},${pumpY + 18}`} flow={totalFlowNorm} thick={5} hot />

      <Pump x={pumpX} y={pumpY} kW={pump_kw} totalFlow={total_flow_gpm} />

      <FlowPath d={`M ${pumpX + 28},${pumpY - 6} L ${pumpX + 60},${pumpY - 6} L ${pumpX + 60},${supplyY}`} flow={totalFlowNorm} thick={6} />
      <FlowPath d={`M ${pumpX + 60},${returnY} L ${pumpX + 60},${pumpY + 8} L ${pumpX + 28},${pumpY + 8}`} flow={totalFlowNorm} thick={6} hot />
      <FlowPath d={`M ${pumpX + 60},${supplyY} L ${xB[2] + 30},${supplyY}`} flow={totalFlowNorm} thick={6} />
      <FlowPath d={`M ${pumpX + 60},${returnY} L ${xB[2] + 30},${returnY}`} flow={totalFlowNorm} thick={6} hot />

      <line x1={(xA[2] + xB[0]) / 2} y1={supplyY - 20} x2={(xA[2] + xB[0]) / 2} y2={returnY + 20} stroke="#2d3d5e" strokeWidth="1" strokeDasharray="4 4" />
      <g fontFamily="JetBrains Mono, monospace" fontWeight="700">
        <text x={(xA[0] + xA[2]) / 2} y={supplyY - 18} textAnchor="middle" fontSize="10" fill="#d1dcec" letterSpacing="0.1em">BRANCH A · CRAH · DN65</text>
        <text x={(xB[0] + xB[2]) / 2} y={supplyY - 18} textAnchor="middle" fontSize="10" fill="#d1dcec" letterSpacing="0.1em">BRANCH B · AHU · DN100</text>
      </g>

      <g transform={`translate(${(xA[0] + xA[2]) / 2}, ${returnY + 28})`}>
        <rect x="-58" y="-12" width="116" height="22" rx="3" fill="#131f37" stroke="#2d3d5e" />
        <text x="-46" y="3" fontFamily="JetBrains Mono, monospace" fontSize="8" fill="#9aacc8">Q_A</text>
        <text x="-30" y="4" fontFamily="JetBrains Mono, monospace" fontSize="12" fontWeight="700" fill="#22d3ee">{flowA.toFixed(0)}</text>
        <text x="22" y="3" fontFamily="JetBrains Mono, monospace" fontSize="8" fill="#9aacc8">GPM</text>
      </g>
      <g transform={`translate(${(xB[0] + xB[2]) / 2}, ${returnY + 28})`}>
        <rect x="-58" y="-12" width="116" height="22" rx="3" fill="#131f37" stroke="#2d3d5e" />
        <text x="-46" y="3" fontFamily="JetBrains Mono, monospace" fontSize="8" fill="#9aacc8">Q_B</text>
        <text x="-30" y="4" fontFamily="JetBrains Mono, monospace" fontSize="12" fontWeight="700" fill="#22d3ee">{flowB.toFixed(0)}</text>
        <text x="22" y="3" fontFamily="JetBrains Mono, monospace" fontSize="8" fill="#9aacc8">GPM</text>
      </g>

      {valves.map((v) => {
        const x = xOf(v);
        const cfg = VALVE_BY_ID[v.valve_id] || {};
        const rFlow = v.flow_gpm / (cfg.designFlowGpm || 100);
        return (
          <g key={v.valve_id}>
            <FlowPath d={`M ${x},${supplyY} L ${x},${valveY - 22}`} flow={rFlow} thick={4} />
            <FlowPath d={`M ${x},${valveY + 22} L ${x},${coilY - 18}`} flow={rFlow} thick={4} />
            <FlowPath d={`M ${x},${coilY + 18} L ${x},${returnY}`} flow={rFlow} thick={4} hot />
            <Valve x={x} y={valveY} valve={v} onClick={() => onSelectValve?.(v.valve_id)} selected={selectedValveId === v.valve_id} />
            <Coil x={x} y={coilY} label={cfg.label || v.valve_id} sub={cfg.size} dT={v.dT_C} />
          </g>
        );
      })}

      <g transform={`translate(${W - 20}, 56)`} fontFamily="JetBrains Mono, monospace">
        <text x="0" y="0" textAnchor="end" fontSize="9" fill="#9aacc8">SYSTEM HEAD</text>
        <text x="0" y="16" textAnchor="end" fontSize="16" fontWeight="700" fill="#2dd4ff">{pump_head_kpa.toFixed(0)}<tspan fontSize="9" fill="#9aacc8" dx="2">kPa</tspan></text>
      </g>
      <g transform={`translate(20, 56)`} fontFamily="JetBrains Mono, monospace">
        <text x="0" y="0" fontSize="9" fill="#9aacc8">PUMP POWER</text>
        <text x="0" y="16" fontSize="16" fontWeight="700" fill="#ffffff">{pump_kw.toFixed(2)}<tspan fontSize="9" fill="#9aacc8" dx="2">kW</tspan></text>
      </g>

      <style>{`
        @keyframes flowDash { from { stroke-dashoffset: 0; } to { stroke-dashoffset: -44; } }
        @keyframes pumpSpin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </svg>
  );
}
