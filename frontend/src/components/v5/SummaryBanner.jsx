import { useEffect, useState } from "react";
import { useDashboardStore } from "../../store/useDashboardStore";

function Cell({ label, value, unit, accent }) {
  return (
    <div
      style={{
        flex: 1,
        minWidth: 0,
        background: "#0f1a30",
        border: `1.5px solid ${accent ? `${accent}55` : "#2d3d5e"}`,
        borderRadius: 5,
        padding: "10px 14px",
      }}
    >
      <div
        className="mono"
        style={{
          fontSize: 11,
          color: "#9aacc8",
          letterSpacing: "0.1em",
          fontWeight: 600,
          marginBottom: 5,
        }}
      >
        {label}
      </div>
      <div style={{ display: "flex", alignItems: "baseline", gap: 5 }}>
        <span
          className="mono"
          style={{
            fontSize: 26,
            fontWeight: 700,
            color: accent ?? "#fff",
            lineHeight: 1,
          }}
        >
          {value}
        </span>
        <span className="mono" style={{ fontSize: 12, color: "#9aacc8" }}>
          {unit}
        </span>
      </div>
    </div>
  );
}

// End-of-run energy summary, rendered as a modal overlay that pops out when
// the engine sends a `summary` WS message (orchestrator._emit_summary on
// natural scenario completion). Numbers are MEASURED per-phase pump_kW —
// no Belimo comparison, no marketing factor.
export default function SummaryBanner() {
  const s = useDashboardStore((st) => st.latestSummary);
  const [dismissed, setDismissed] = useState(null);

  // Auto-show when a NEW summary arrives. Track by scenario+duration so
  // hitting REPLAY resets the dismiss state for the next run.
  const summaryKey = s ? `${s.scenario}|${s.duration_s}` : null;
  useEffect(() => {
    if (summaryKey && summaryKey !== dismissed) {
      // ESC closes
      const onKey = (e) => e.key === "Escape" && setDismissed(summaryKey);
      window.addEventListener("keydown", onKey);
      return () => window.removeEventListener("keydown", onKey);
    }
  }, [summaryKey, dismissed]);

  if (!s) return null;
  if (summaryKey === dismissed) return null;

  return (
    <div
      onClick={() => setDismissed(summaryKey)}
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(10, 18, 36, 0.85)",
        backdropFilter: "blur(4px)",
        WebkitBackdropFilter: "blur(4px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1000,
        animation: "summaryFadeIn 0.3s ease-out",
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          background: "#0a1224",
          border: "2px solid #34d399",
          borderRadius: 8,
          padding: 24,
          display: "flex",
          flexDirection: "column",
          gap: 14,
          boxShadow: "0 0 60px rgba(52, 211, 153, 0.4)",
          maxWidth: 900,
          width: "92vw",
          maxHeight: "90vh",
          overflowY: "auto",
          animation: "summaryPopIn 0.4s cubic-bezier(0.34, 1.56, 0.64, 1)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span
            className="mono"
            style={{
              fontSize: 12,
              color: "#0a1224",
              background: "#34d399",
              padding: "3px 10px",
              borderRadius: 3,
              fontWeight: 700,
              letterSpacing: "0.14em",
            }}
          >
            SCENARIO COMPLETE
          </span>
          <span
            className="mono"
            style={{
              fontSize: 16,
              color: "#34d399",
              fontWeight: 700,
              letterSpacing: "0.05em",
            }}
          >
            {s.scenario} · {s.duration_s}s
          </span>
          <button
            onClick={() => setDismissed(summaryKey)}
            style={{
              marginLeft: "auto",
              background: "transparent",
              border: "1px solid #2d3d5e",
              color: "#9aacc8",
              padding: "4px 12px",
              borderRadius: 4,
              fontSize: 11,
              fontFamily: "monospace",
              cursor: "pointer",
              letterSpacing: "0.1em",
            }}
            aria-label="Close summary"
          >
            CLOSE · ESC
          </button>
        </div>

        <div
          className="mono"
          style={{ fontSize: 11, color: "#9aacc8", fontStyle: "italic" }}
        >
          all numbers measured during this run · no controller comparison
        </div>

        <div style={{ display: "flex", gap: 8 }}>
          <Cell
            label="L3 RECOVERY SAVED"
            value={s.recovery_fired ? s.recovery_savings_kwh.toFixed(3) : "—"}
            unit={s.recovery_fired ? "kWh" : "no recovery fired"}
            accent={s.recovery_fired ? "#34d399" : "#9aacc8"}
          />
          <Cell
            label="TOTAL PUMP ENERGY"
            value={s.total_kwh.toFixed(3)}
            unit="kWh"
          />
          <Cell
            label="ΔT COMPLIANCE"
            value={s.dt_compliance_pct.toFixed(0)}
            unit="%"
            accent={s.dt_compliance_pct >= 90 ? "#34d399" : "#fbbf24"}
          />
        </div>

        <div style={{ display: "flex", gap: 8 }}>
          <Cell
            label="MEAN kW · PRE-FAULT"
            value={s.mean_kw_pre_fault.toFixed(2)}
            unit="kW"
          />
          <Cell
            label="MEAN kW · DURING FAULT"
            value={s.mean_kw_during_fault.toFixed(2)}
            unit="kW"
            accent="#f87171"
          />
          <Cell
            label="MEAN kW · POST-RECOVERY"
            value={s.recovery_fired ? s.mean_kw_post_recovery.toFixed(2) : "—"}
            unit={s.recovery_fired ? "kW" : "n/a"}
            accent={s.recovery_fired ? "#34d399" : "#9aacc8"}
          />
        </div>

        {s.recovery_fired && s.recovery_savings_kw > 0 && (
          <div
            style={{
              fontSize: 13,
              color: "#d1dcec",
              fontStyle: "italic",
              background: "#34d39912",
              padding: "10px 14px",
              borderRadius: 5,
              border: "1px solid #34d39933",
              lineHeight: 1.5,
            }}
          >
            Pump load during fault was{" "}
            <span style={{ color: "#f87171", fontWeight: 700 }}>
              {(
                ((s.mean_kw_during_fault - s.mean_kw_post_recovery) /
                  Math.max(s.mean_kw_post_recovery, 0.01)) *
                100
              ).toFixed(0)}
              %
            </span>{" "}
            higher than post-recovery. Autonomous L3 reset eliminated this
            overhead — measured savings:{" "}
            <span style={{ color: "#34d399", fontWeight: 700 }}>
              {s.recovery_savings_kwh.toFixed(3)} kWh
            </span>
            .
          </div>
        )}

        {s.framework && (
          <div
            style={{
              marginTop: 4,
              paddingTop: 14,
              borderTop: "1px dashed #2d3d5e",
              display: "flex",
              flexDirection: "column",
              gap: 10,
            }}
          >
            <div
              style={{
                display: "flex",
                alignItems: "baseline",
                gap: 10,
                flexWrap: "wrap",
              }}
            >
              <span
                className="mono"
                style={{
                  fontSize: 11,
                  color: "#0a1224",
                  background: "#60a5fa",
                  padding: "3px 10px",
                  borderRadius: 3,
                  fontWeight: 700,
                  letterSpacing: "0.14em",
                }}
              >
                FRAMEWORK · PROJECTED ANNUAL
              </span>
              <span
                className="mono"
                style={{ fontSize: 11, color: "#9aacc8", fontStyle: "italic" }}
              >
                step 1–6, confidence-weighted, low/mid/high band
              </span>
            </div>

            <div style={{ display: "flex", gap: 8 }}>
              <Cell
                label="NET % vs BASELINE"
                value={s.framework.net_pct_vs_baseline.toFixed(2)}
                unit="%"
                accent={
                  s.framework.net_pct_vs_baseline >= 4 &&
                  s.framework.net_pct_vs_baseline <= 7
                    ? "#34d399"
                    : "#fbbf24"
                }
              />
              <Cell
                label="BAND L · M · H"
                value={`${s.framework.band_low_pct.toFixed(1)} · ${s.framework.band_mid_pct.toFixed(1)} · ${s.framework.band_high_pct.toFixed(1)}`}
                unit="%"
              />
              <Cell
                label="CONFIDENCE-WEIGHTED"
                value={s.framework.confidence_weighted_kwh.toFixed(0)}
                unit={`kWh · w=${s.framework.confidence_weight.toFixed(2)}`}
                accent="#60a5fa"
              />
            </div>

            <div style={{ display: "flex", gap: 8 }}>
              <Cell
                label="BASELINE (PUMP, ANNUAL)"
                value={s.framework.baseline_kwh_annual.toFixed(0)}
                unit="kWh"
              />
              <Cell
                label="FAULT SAVINGS"
                value={s.framework.fault_savings_kwh.toFixed(0)}
                unit="kWh"
              />
              <Cell
                label="DRIFT AVOIDED"
                value={s.framework.drift_avoided_kwh.toFixed(0)}
                unit={`kWh · c=${s.framework.drift_confidence.toFixed(2)}`}
              />
              <Cell
                label="OVERHEAD"
                value={s.framework.overhead_kwh.toFixed(0)}
                unit="kWh"
                accent="#f87171"
              />
            </div>

            {(s.ai_detect_latency_s != null ||
              s.belimo_counterfactual_latency_s != null) && (
              <div
                style={{
                  fontSize: 12,
                  color: "#d1dcec",
                  background: "#60a5fa12",
                  border: "1px solid #60a5fa33",
                  borderRadius: 5,
                  padding: "8px 12px",
                  lineHeight: 1.5,
                }}
              >
                Measured detection latency this run · AI:{" "}
                <span style={{ color: "#34d399", fontWeight: 700 }}>
                  {s.ai_detect_latency_s != null
                    ? `${s.ai_detect_latency_s.toFixed(0)} s`
                    : "—"}
                </span>{" "}
                · Belimo counterfactual (ΔT&lt;4 °C for 5 min):{" "}
                <span style={{ color: "#f87171", fontWeight: 700 }}>
                  {s.belimo_counterfactual_latency_s != null
                    ? `${s.belimo_counterfactual_latency_s.toFixed(0)} s`
                    : "did not fire"}
                </span>
                . The framework substitutes these into its{" "}
                <span className="mono">low_dT</span> row instead of catalog
                defaults. Confidence weight {" "}
                {s.framework.confidence_weight.toFixed(2)} = mean
                anomaly_confidence × (1 − assumed FP rate).
              </div>
            )}

            <div
              style={{
                display: "flex",
                flexDirection: "column",
                gap: 4,
                background: "#0f1a30",
                border: "1px solid #2d3d5e",
                borderRadius: 5,
                padding: "10px 12px",
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
                PER-FAULT BREAKDOWN
              </div>
              {s.framework.per_fault.map((f) => (
                <div
                  key={f.name}
                  className="mono"
                  style={{
                    display: "grid",
                    gridTemplateColumns: "160px 90px 80px 90px 1fr",
                    fontSize: 11,
                    color: f.measured ? "#34d399" : "#d1dcec",
                    gap: 8,
                  }}
                >
                  <span>
                    {f.name}
                    {f.measured ? " ·measured" : ""}
                  </span>
                  <span>Δt {f.detect_advantage_s.toFixed(0)} s</span>
                  <span>{f.power_penalty_kw.toFixed(1)} kW</span>
                  <span>{f.events_per_year.toFixed(0)} /yr</span>
                  <span style={{ textAlign: "right" }}>
                    {f.e_saved_kwh.toFixed(0)} kWh
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        <div
          className="mono"
          style={{
            fontSize: 10,
            color: "#445574",
            textAlign: "center",
            marginTop: 4,
            letterSpacing: "0.05em",
          }}
        >
          click outside or press ESC to dismiss · REPLAY to run again
        </div>
      </div>

      <style>{`
        @keyframes summaryFadeIn {
          from { opacity: 0; }
          to   { opacity: 1; }
        }
        @keyframes summaryPopIn {
          from { opacity: 0; transform: scale(0.85) translateY(20px); }
          to   { opacity: 1; transform: scale(1)    translateY(0);    }
        }
      `}</style>
    </div>
  );
}
