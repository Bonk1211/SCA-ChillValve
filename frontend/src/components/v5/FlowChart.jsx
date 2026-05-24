import { useDashboardStore } from "../../store/useDashboardStore";
import { VALVES } from "../../lib/valveConfig";

const VALVE_COLOR = {
  A1: "#67e8f9",
  A2: "#22d3ee",
  A3: "#0891b2",
  B1: "#fde68a",
  B2: "#fbbf24",
  B3: "#d97706",
};

const CARD_W = 200;
const CARD_H = 36;
const Y_MAX = 220;   // GPM ceiling; DN100 design=150, leave headroom

function buildPath(arr, tickMin, tickMax) {
  if (arr.length < 2) return "";
  const span = Math.max(1, tickMax - tickMin);
  return arr
    .map((p, i) => {
      const x = ((p.tick - tickMin) / span) * CARD_W;
      const y = CARD_H - (Math.min(Y_MAX, p.flow_gpm) / Y_MAX) * CARD_H;
      return `${i === 0 ? "M" : "L"} ${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
}

function ValveCard({ id, color, history, latest, selected, onSelect }) {
  const v = latest?.valves?.find((x) => x.valve_id === id);
  const flow = v?.flow_gpm ?? 0;
  const isAnom = v?.anomaly_detected;
  const isFault = v?.safety_override_active;
  const isLeader = v?.is_leader;
  const stateColor = isFault ? "#f87171" : isAnom ? "#fbbf24" : "#34d399";

  const arr = history[id] || [];
  let tickMin = Infinity;
  let tickMax = -Infinity;
  for (const p of arr) {
    if (p.tick < tickMin) tickMin = p.tick;
    if (p.tick > tickMax) tickMax = p.tick;
  }
  if (!isFinite(tickMin)) {
    tickMin = 0;
    tickMax = 1;
  }
  const path = buildPath(arr, tickMin, tickMax);
  const span = Math.max(1, tickMax - tickMin);
  const lastX = arr.length > 0 ? ((arr[arr.length - 1].tick - tickMin) / span) * CARD_W : 0;
  const lastY =
    arr.length > 0
      ? CARD_H - (Math.min(Y_MAX, arr[arr.length - 1].flow_gpm) / Y_MAX) * CARD_H
      : CARD_H;

  return (
    <div
      onClick={() => onSelect?.(id)}
      style={{
        background: selected ? "#202d49" : "#131f37",
        border: `1px solid ${selected ? "#22d3ee" : "#2d3d5e"}`,
        borderRadius: 4,
        padding: "5px 7px",
        cursor: "pointer",
        transition: "background 0.12s, border 0.12s",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: 3,
        }}
      >
        <span style={{ display: "flex", alignItems: "center", gap: 5 }}>
          <span
            style={{
              width: 8,
              height: 8,
              borderRadius: 1,
              background: color,
              boxShadow: selected ? `0 0 4px ${color}` : "none",
            }}
          />
          <span
            className="mono"
            style={{ fontSize: 10, fontWeight: 700, color: "#fff", letterSpacing: "0.04em" }}
          >
            {id}
          </span>
          {isLeader && (
            <span
              className="mono"
              style={{
                fontSize: 7,
                fontWeight: 700,
                color: "#0a1224",
                background: "#22d3ee",
                padding: "1px 3px",
                borderRadius: 2,
                letterSpacing: "0.08em",
              }}
            >
              LEAD
            </span>
          )}
        </span>
        <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
          <span
            className="mono"
            style={{ fontSize: 10, color: "#d1dcec", fontWeight: 600 }}
          >
            {flow.toFixed(0)}
            <span style={{ color: "#9aacc8", fontSize: 8, marginLeft: 2 }}>GPM</span>
          </span>
          <span
            style={{
              width: 6,
              height: 6,
              borderRadius: "50%",
              background: stateColor,
              boxShadow: `0 0 4px ${stateColor}`,
              animation: isFault ? "ledPulse 1.2s ease-in-out infinite" : "none",
            }}
          />
        </span>
      </div>
      <svg
        viewBox={`0 0 ${CARD_W} ${CARD_H}`}
        preserveAspectRatio="none"
        style={{ width: "100%", height: CARD_H, display: "block" }}
      >
        <line x1="0" y1={CARD_H} x2={CARD_W} y2={CARD_H} stroke="#2d3d5e" strokeWidth="0.5" />
        <line
          x1="0"
          y1={CARD_H - (150 / Y_MAX) * CARD_H}
          x2={CARD_W}
          y2={CARD_H - (150 / Y_MAX) * CARD_H}
          stroke="#2d3d5e"
          strokeWidth="0.3"
          strokeDasharray="2 3"
        />
        {arr.length >= 2 && (
          <>
            <path
              d={`${path} L ${CARD_W},${CARD_H} L 0,${CARD_H} Z`}
              fill={color}
              opacity="0.18"
            />
            <path
              d={path}
              fill="none"
              stroke={color}
              strokeWidth="1.4"
              strokeLinejoin="round"
              strokeLinecap="round"
            />
            <circle cx={lastX} cy={lastY} r="2" fill={color} />
          </>
        )}
      </svg>
    </div>
  );
}

export default function FlowChart({ selectedValveId, onSelectValve }) {
  const history = useDashboardStore((s) => s.history);
  const latest = useDashboardStore((s) => s.latest);
  return (
    <div
      style={{
        background: "#0f1a30",
        border: "1px solid #2d3d5e",
        borderRadius: 6,
        padding: 8,
        display: "flex",
        flexDirection: "column",
        gap: 5,
        minWidth: 0,
      }}
    >
      <div
        className="mono"
        style={{
          fontSize: 10,
          color: "#fff",
          fontWeight: 700,
          letterSpacing: "0.1em",
          marginBottom: 2,
        }}
      >
        PER-VALVE FLOW · LIVE
      </div>
      {VALVES.map((v) => (
        <ValveCard
          key={v.id}
          id={v.id}
          color={VALVE_COLOR[v.id] || "#9aacc8"}
          history={history}
          latest={latest}
          selected={selectedValveId === v.id}
          onSelect={onSelectValve}
        />
      ))}
      <style>{`@keyframes ledPulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }`}</style>
    </div>
  );
}
