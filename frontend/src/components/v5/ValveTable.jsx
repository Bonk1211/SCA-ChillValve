import { useDashboardStore } from "../../store/useDashboardStore";
import { VALVE_BY_ID, TARGET_DT_C, DT_TOLERANCE_C } from "../../lib/valveConfig";
import { isImpaired } from "../../lib/impairment";

const hdrSt = {
  fontSize: 9,
  color: "#9aacc8",
  letterSpacing: "0.1em",
  fontWeight: 600,
  paddingBottom: 4,
  borderBottom: "1px solid #2d3d5e",
};

const rowSt = { fontSize: 11 };

export default function ValveTable({ selectedId, onSelect }) {
  const latest = useDashboardStore((s) => s.latest);
  const valves = latest?.valves ?? [];

  return (
    <div
      style={{
        background: "#1a2640",
        border: "1px solid #2d3d5e",
        borderRadius: 6,
        padding: 8,
      }}
    >
      <div
        className="mono"
        style={{
          fontSize: 10,
          color: "#fff",
          fontWeight: 700,
          letterSpacing: "0.1em",
          marginBottom: 6,
        }}
      >
        VALVE PARAMETERS
      </div>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "32px 1fr 50px 44px 44px 18px",
          columnGap: 6,
          rowGap: 3,
          alignItems: "center",
        }}
      >
        <span className="mono" style={hdrSt}>ID</span>
        <span className="mono" style={hdrSt}>ZONE</span>
        <span className="mono" style={{ ...hdrSt, textAlign: "right" }}>FLOW</span>
        <span className="mono" style={{ ...hdrSt, textAlign: "right" }}>ΔT</span>
        <span className="mono" style={{ ...hdrSt, textAlign: "right" }}>POS</span>
        <span></span>

        {valves.map((v) => {
          const cfg = VALVE_BY_ID[v.valve_id] || {};
          const isAnomaly = isImpaired(v);
          const isFault = v.safety_override_active;
          const dtColor =
            Math.abs(v.dT_C - TARGET_DT_C) <= DT_TOLERANCE_C ? "#34d399" : "#fbbf24";
          const stateColor = isFault ? "#f87171" : isAnomaly ? "#fbbf24" : "#34d399";
          const isSelected = selectedId === v.valve_id;
          return (
            <span key={v.valve_id} style={{ display: "contents" }}>
              <span
                className="mono"
                style={{
                  ...rowSt,
                  color: "#fff",
                  fontWeight: 700,
                  padding: "4px 0 4px 4px",
                  cursor: "pointer",
                  background: isSelected ? "#202d49" : "transparent",
                  borderRadius: 2,
                }}
                onClick={() => onSelect?.(v.valve_id)}
              >
                {v.is_leader && (
                  <span
                    style={{
                      display: "inline-block",
                      width: 4,
                      height: 4,
                      background: "#22d3ee",
                      borderRadius: "50%",
                      marginRight: 4,
                      verticalAlign: "middle",
                      boxShadow: "0 0 4px #22d3ee",
                    }}
                  />
                )}
                {v.valve_id}
              </span>
              <span
                className="mono"
                style={{
                  ...rowSt,
                  color: "#d1dcec",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                }}
              >
                {cfg.zone || cfg.label || v.valve_id}
              </span>
              <span
                className="mono"
                style={{ ...rowSt, textAlign: "right", color: "#fff", fontWeight: 600 }}
              >
                {v.flow_gpm.toFixed(0)}
                <span style={{ color: "#9aacc8", fontSize: 9, marginLeft: 2 }}>g</span>
              </span>
              <span
                className="mono"
                style={{ ...rowSt, textAlign: "right", color: dtColor, fontWeight: 600 }}
              >
                {v.dT_C.toFixed(1)}
              </span>
              <span
                className="mono"
                style={{ ...rowSt, textAlign: "right", color: "#fff", fontWeight: 600 }}
              >
                {v.position_pct.toFixed(0)}
                <span style={{ color: "#9aacc8", fontSize: 9, marginLeft: 1 }}>%</span>
              </span>
              <span style={{ display: "flex", justifyContent: "flex-end" }}>
                <span
                  style={{
                    width: 8,
                    height: 8,
                    borderRadius: "50%",
                    background: stateColor,
                    boxShadow: `0 0 6px ${stateColor}`,
                    animation: isFault ? "ledPulse 1.2s ease-in-out infinite" : "none",
                  }}
                />
              </span>
            </span>
          );
        })}
        {valves.length === 0 && (
          <span
            className="mono"
            style={{
              gridColumn: "1 / -1",
              fontSize: 11,
              color: "#9aacc8",
              fontStyle: "italic",
              padding: "12px 0",
              textAlign: "center",
            }}
          >
            (no valve data yet — click NEXT STEP)
          </span>
        )}
      </div>
      <style>{`@keyframes ledPulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }`}</style>
    </div>
  );
}
