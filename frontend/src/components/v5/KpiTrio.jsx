import { useDashboardStore } from "../../store/useDashboardStore";
import { TARGET_DT_C, DT_TOLERANCE_C } from "../../lib/valveConfig";
import { isImpaired } from "../../lib/impairment";

// Pump rated draw — used for the PUMP POWER utilization gauge below.
// This is NOT a Belimo comparison. Any controller-vs-controller story lives
// in the slide deck + `--mode compare` CLI (see PRD §6).
const PUMP_NAMEPLATE_KW = 20.5;

function KpiBigCard({ label, value, unit, sub, color }) {
  return (
    <div
      style={{
        background: "#1a2640",
        border: "1px solid #2d3d5e",
        borderRadius: 6,
        padding: "6px 10px",
      }}
    >
      <div
        className="mono"
        style={{
          fontSize: 10,
          color: "#9aacc8",
          letterSpacing: "0.1em",
          fontWeight: 600,
          marginBottom: 4,
        }}
      >
        {label}
      </div>
      <div style={{ display: "flex", alignItems: "baseline", gap: 5 }}>
        <span
          className="mono"
          style={{
            fontSize: 22,
            fontWeight: 700,
            color,
            lineHeight: 1,
            letterSpacing: "-0.02em",
          }}
        >
          {value}
        </span>
        <span className="mono" style={{ fontSize: 11, color: "#9aacc8", fontWeight: 600 }}>
          {unit}
        </span>
      </div>
      <div
        className="mono"
        style={{ fontSize: 9, color: "#9aacc8", marginTop: 3, letterSpacing: "0.02em" }}
      >
        {sub}
      </div>
    </div>
  );
}

export default function KpiTrio() {
  const latest = useDashboardStore((s) => s.latest);
  const valves = latest?.valves ?? [];

  const totalValves = valves.length || 6;
  const compliantCount = valves.filter(
    (v) => Math.abs(v.dT_C - TARGET_DT_C) <= DT_TOLERANCE_C,
  ).length;
  const dtCompliancePct = totalValves > 0 ? (compliantCount / totalValves) * 100 : 0;

  const anomalies = valves.filter(isImpaired).length;

  const currentKw = latest?.pump_kw ?? 0;
  const hasData = latest != null && currentKw > 0;
  const pumpUtilPct = hasData ? (currentKw / PUMP_NAMEPLATE_KW) * 100 : 0;

  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: 6 }}>
      <KpiBigCard
        label="ΔT COMPLIANCE"
        value={dtCompliancePct.toFixed(0)}
        unit="%"
        sub={`of ${totalValves} valves in 5.0±0.7°C band`}
        color={dtCompliancePct >= 80 ? "#34d399" : dtCompliancePct >= 50 ? "#fbbf24" : "#f87171"}
      />
      <KpiBigCard
        label="PUMP POWER"
        value={hasData ? currentKw.toFixed(2) : "—"}
        unit={hasData ? "kW" : ""}
        sub={
          hasData
            ? `${pumpUtilPct.toFixed(0)}% of ${PUMP_NAMEPLATE_KW} kW nameplate`
            : "awaiting data"
        }
        color={
          !hasData
            ? "#9aacc8"
            : pumpUtilPct < 50
            ? "#34d399"
            : pumpUtilPct < 80
            ? "#fbbf24"
            : "#f87171"
        }
      />
      <KpiBigCard
        label="ACTIVE ANOMALIES"
        value={anomalies.toString()}
        unit={`/ ${totalValves}`}
        sub={
          anomalies === 0
            ? "all valves nominal"
            : `${anomalies} valve${anomalies > 1 ? "s" : ""} below design`
        }
        color={anomalies === 0 ? "#34d399" : anomalies <= 2 ? "#fbbf24" : "#f87171"}
      />
    </div>
  );
}
