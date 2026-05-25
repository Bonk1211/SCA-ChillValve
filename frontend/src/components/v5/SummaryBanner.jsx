import { useEffect, useRef, useState } from "react";
import { useDashboardStore } from "../../store/useDashboardStore";

function FormulaTooltip({ rows, accent, placement }) {
  const pos =
    placement === "below"
      ? { top: "calc(100% + 8px)" }
      : { bottom: "calc(100% + 8px)" };
  return (
    <div
      style={{
        position: "absolute",
        left: 0,
        ...pos,
        minWidth: 260,
        maxWidth: 380,
        background: "#050a18",
        border: `1px solid ${accent ?? "#60a5fa"}88`,
        borderRadius: 5,
        padding: "10px 12px",
        zIndex: 100,
        boxShadow: "0 8px 24px rgba(0,0,0,0.6)",
        pointerEvents: "none",
        display: "flex",
        flexDirection: "column",
        gap: 6,
      }}
    >
      {rows.map((r, i) => (
        <div key={i} style={{ display: "flex", flexDirection: "column", gap: 2 }}>
          <div
            className="mono"
            style={{
              fontSize: 9,
              color: accent ?? "#60a5fa",
              letterSpacing: "0.12em",
              fontWeight: 700,
            }}
          >
            {r.label}
          </div>
          <div
            className="mono"
            style={{
              fontSize: 11,
              color: "#d1dcec",
              lineHeight: 1.45,
              whiteSpace: "pre-wrap",
              wordBreak: "break-word",
            }}
          >
            {r.body}
          </div>
        </div>
      ))}
    </div>
  );
}

function Cell({ label, value, unit, accent, formula }) {
  const [hover, setHover] = useState(false);
  const [placement, setPlacement] = useState("above");
  const ref = useRef(null);
  const handleEnter = () => {
    if (formula && ref.current) {
      // Flip below when there's not enough room above inside the modal.
      // Tooltip ~ 200px tall worst case; check against viewport top of cell.
      const rect = ref.current.getBoundingClientRect();
      setPlacement(rect.top < 240 ? "below" : "above");
    }
    setHover(true);
  };
  return (
    <div
      ref={ref}
      onMouseEnter={handleEnter}
      onMouseLeave={() => setHover(false)}
      style={{
        flex: 1,
        minWidth: 0,
        position: "relative",
        background: "#0f1a30",
        border: `1.5px solid ${accent ? `${accent}55` : "#2d3d5e"}`,
        borderRadius: 5,
        padding: "10px 14px",
        cursor: formula ? "help" : "default",
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
          display: "flex",
          alignItems: "center",
          gap: 6,
        }}
      >
        {label}
        {formula && (
          <span
            style={{
              fontSize: 9,
              color: accent ?? "#60a5fa",
              border: `1px solid ${(accent ?? "#60a5fa")}66`,
              borderRadius: 3,
              padding: "0 4px",
              fontWeight: 700,
              letterSpacing: 0,
            }}
          >
            ƒx
          </span>
        )}
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
      {hover && formula && (
        <FormulaTooltip rows={formula} accent={accent} placement={placement} />
      )}
    </div>
  );
}

// End-of-run energy summary, rendered as a modal overlay. Visibility is
// user-controlled via the "SHOW RESULT" button in ControlBar (store flag
// summaryVisible). Never auto-pops on summary arrival.
export default function SummaryBanner() {
  const s = useDashboardStore((st) => st.latestSummary);
  const visible = useDashboardStore((st) => st.summaryVisible);
  const hideSummary = useDashboardStore((st) => st.hideSummary);

  useEffect(() => {
    if (!visible) return undefined;
    const onKey = (e) => e.key === "Escape" && hideSummary();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [visible, hideSummary]);

  if (!s || !visible) return null;

  return (
    <div
      onClick={hideSummary}
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
            onClick={hideSummary}
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

        {s.recovery_fired && (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              flexWrap: "wrap",
              fontSize: 11,
              fontFamily: "monospace",
              color: "#9aacc8",
            }}
          >
            <span
              style={{
                color: "#0a1224",
                background: "#34d399",
                padding: "2px 8px",
                borderRadius: 3,
                fontWeight: 700,
                letterSpacing: "0.1em",
              }}
            >
              ① AGENTS COMMUNICATED
            </span>
            <span style={{ color: "#445574" }}>→</span>
            <span
              style={{
                color: "#0a1224",
                background: "#34d399",
                padding: "2px 8px",
                borderRadius: 3,
                fontWeight: 700,
                letterSpacing: "0.1em",
              }}
            >
              ② LEADER DECIDED
            </span>
            <span style={{ color: "#445574" }}>→</span>
            <span
              style={{
                color: "#0a1224",
                background:
                  s.self_cal_converged_tick != null ? "#34d399" : "#fbbf24",
                padding: "2px 8px",
                borderRadius: 3,
                fontWeight: 700,
                letterSpacing: "0.1em",
              }}
            >
              ③ SELF-CAL{" "}
              {s.self_cal_converged_tick != null
                ? `@ t=${s.self_cal_converged_tick}s`
                : "INCOMPLETE (grace cap)"}
            </span>
            <span style={{ color: "#445574" }}>→</span>
            <span
              style={{
                color: "#0a1224",
                background: "#34d399",
                padding: "2px 8px",
                borderRadius: 3,
                fontWeight: 700,
                letterSpacing: "0.1em",
              }}
            >
              ④ RESULT
            </span>
            {(s.self_cal_wait_past_duration_s ?? 0) > 0 && (
              <span style={{ color: "#9aacc8", fontStyle: "italic" }}>
                · waited {s.self_cal_wait_past_duration_s.toFixed(1)}s past
                duration for flows to settle
              </span>
            )}
          </div>
        )}

        <div
          className="mono"
          style={{ fontSize: 11, color: "#9aacc8", fontStyle: "italic" }}
        >
          top tiles: measured per-tick pump_kW from this run ·
          framework block: measured run + catalog projections — hover ƒx per cell for source
        </div>

        <div style={{ display: "flex", gap: 8 }}>
          <Cell
            label="L3 RECOVERY SAVED"
            value={s.recovery_fired ? s.recovery_savings_kwh.toFixed(3) : "—"}
            unit={s.recovery_fired ? "kWh" : "no recovery fired"}
            accent={s.recovery_fired ? "#34d399" : "#9aacc8"}
            formula={[
              {
                label: "FORMULA",
                body:
                  "kW_saved = max(0, mean_kW_during − mean_kW_post)\n" +
                  "kWh_saved = kW_saved × T_post_recovery / 3600",
              },
              {
                label: "SUBSTITUTED",
                body:
                  `max(0, ${s.mean_kw_during_fault.toFixed(2)} − ${s.mean_kw_post_recovery.toFixed(2)}) ` +
                  `= ${s.recovery_savings_kw.toFixed(3)} kW`,
              },
              {
                label: "RESULT",
                body: `${s.recovery_savings_kw.toFixed(3)} kW × (T_post/3600) = ${s.recovery_savings_kwh.toFixed(3)} kWh`,
              },
            ]}
          />
          <Cell
            label="TOTAL PUMP ENERGY"
            value={s.total_kwh.toFixed(3)}
            unit="kWh"
            formula={[
              {
                label: "FORMULA",
                body: "Σ pump_kW(t) / 3600  over every sim-tick (1 tick = 1 s)",
              },
              {
                label: "RESULT",
                body: `${s.total_kwh.toFixed(3)} kWh over ${s.duration_s}s of scenario`,
              },
            ]}
          />
          <Cell
            label="ΔT COMPLIANCE"
            value={s.dt_compliance_pct.toFixed(0)}
            unit={s.dt_target_spec ? "% · ASHRAE 90.1" : "%"}
            accent={s.dt_compliance_pct >= 90 ? "#34d399" : "#fbbf24"}
            formula={[
              {
                label: "FORMULA",
                body:
                  "100 × samples_in_band / total_samples\n" +
                  "in-band = |ΔT − 5.0 °C| ≤ 0.7 °C, sampled per valve per tick",
              },
              {
                label: "SPEC",
                body:
                  s.dt_target_spec ??
                  "design 5.0 °C ±0.7 °C (no formal spec linked)",
              },
              {
                label: "RESULT",
                body: `${s.dt_compliance_pct.toFixed(1)} % of valve-tick samples held design ΔT`,
              },
            ]}
          />
        </div>

        <div style={{ display: "flex", gap: 8 }}>
          <Cell
            label="MEAN kW · PRE-FAULT"
            value={s.mean_kw_pre_fault.toFixed(2)}
            unit="kW"
            formula={[
              {
                label: "FORMULA",
                body: "Σ pump_kW(t) / N_ticks  while phase = pre_fault",
              },
              {
                label: "PHASE WINDOW",
                body: "t = 0 → first tick anomaly_detected on any valve",
              },
              {
                label: "RESULT",
                body: `${s.mean_kw_pre_fault.toFixed(3)} kW (steady baseline draw before fault injection)`,
              },
            ]}
          />
          <Cell
            label="MEAN kW · DURING FAULT"
            value={s.mean_kw_during_fault.toFixed(2)}
            unit="kW"
            accent="#f87171"
            formula={[
              {
                label: "FORMULA",
                body: "Σ pump_kW(t) / N_ticks  while phase = during_fault",
              },
              {
                label: "PHASE WINDOW",
                body:
                  "first anomaly_detected → first tick (L3 reset executed AND " +
                  "anomaly cleared on all valves)",
              },
              {
                label: "RESULT",
                body: `${s.mean_kw_during_fault.toFixed(3)} kW — peers compensate for choked branch, head ↑ → pump kW ↑`,
              },
            ]}
          />
          <Cell
            label="MEAN kW · POST-RECOVERY"
            value={s.recovery_fired ? s.mean_kw_post_recovery.toFixed(2) : "—"}
            unit={s.recovery_fired ? "kW" : "n/a"}
            accent={s.recovery_fired ? "#34d399" : "#9aacc8"}
            formula={[
              {
                label: "FORMULA",
                body: "Σ pump_kW(t) / N_ticks  while phase = post_recovery",
              },
              {
                label: "PHASE WINDOW",
                body: "after L3 attempt_actuator_reset executed AND anomaly_detected = false on all valves",
              },
              {
                label: "RESULT",
                body: s.recovery_fired
                  ? `${s.mean_kw_post_recovery.toFixed(3)} kW (system back to nominal)`
                  : "no L3 recovery fired this run → phase never entered",
              },
            ]}
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

        {s.framework && (() => {
          // Drive subtitle + CONDITIONAL ADD-ON label off the fouling row's
          // baseline regime. om_practice / Δt<23d = defensible; otherwise the
          // vendor-only 69-day Belimo catalog default applies.
          const foulingRow = s.framework.per_fault?.find(
            (r) => r.name === "coil_fouling",
          );
          const foulingDefensible =
            foulingRow &&
            (foulingRow.baseline_source === "om_practice" ||
              foulingRow.detect_advantage_s < 2_000_000);
          const headlineSubtitle = foulingDefensible
            ? "fouling row uses O&M-practice baseline (21d catch via pressure-drop + BMS) — held out from headline to keep the conservative number front-and-center"
            : "fouling excluded from headline (catalog-only, unvalidated) · low/mid/high band";
          return (
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
                FRAMEWORK · DEFENSIBLE ANNUAL
              </span>
              <span
                className="mono"
                style={{ fontSize: 11, color: "#9aacc8", fontStyle: "italic" }}
              >
                {headlineSubtitle}
              </span>
            </div>

            <div style={{ display: "flex", gap: 8 }}>
              <Cell
                label="NET % vs BASELINE (excl. fouling)"
                value={(s.framework.net_pct_excl_fouling ?? 0).toFixed(2)}
                unit="%"
                accent={
                  (s.framework.net_pct_excl_fouling ?? 0) >= 1
                    ? "#34d399"
                    : "#fbbf24"
                }
                formula={[
                  {
                    label: "FORMULA",
                    body:
                      "net_excl_fouling = (Σ fault_i − coil_fouling) + drift_avoided − overhead\n" +
                      "net_pct = 100 × net_excl_fouling / baseline_annual",
                  },
                  {
                    label: "WHY EXCLUDED",
                    body:
                      "coil_fouling catalog Δt = 69 days; cannot be validated\n" +
                      "by any reasonable demo run. Included version shown\n" +
                      "below in CONDITIONAL ADD-ON.",
                  },
                  {
                    label: "SUBSTITUTED",
                    body:
                      `((${s.framework.fault_savings_kwh.toFixed(0)} − ${(s.framework.coil_fouling_kwh ?? 0).toFixed(0)}) ` +
                      `+ ${s.framework.drift_avoided_kwh.toFixed(0)} − ${s.framework.overhead_kwh.toFixed(0)}) ` +
                      `= ${(s.framework.net_savings_excl_fouling_kwh ?? 0).toFixed(0)} kWh\n` +
                      `100 × ${(s.framework.net_savings_excl_fouling_kwh ?? 0).toFixed(0)} / ` +
                      `${s.framework.baseline_kwh_annual.toFixed(0)} = ` +
                      `${(s.framework.net_pct_excl_fouling ?? 0).toFixed(2)} %`,
                  },
                ]}
              />
              <Cell
                label="BAND L · M · H (excl. fouling)"
                value={`${(s.framework.band_low_pct_excl_fouling ?? 0).toFixed(2)} · ${(s.framework.band_mid_pct_excl_fouling ?? 0).toFixed(2)} · ${(s.framework.band_high_pct_excl_fouling ?? 0).toFixed(2)}`}
                unit="%"
                formula={[
                  {
                    label: "FORMULA",
                    body:
                      "sensitivity scan: scale each fault's events_per_year by\n" +
                      "  low ×0.5 · mid ×1.0 · high ×1.5\n" +
                      "then recompute net_pct (fouling row dropped)",
                  },
                  {
                    label: "DEFENSIBLE (excl. fouling)",
                    body:
                      `low=${(s.framework.band_low_pct_excl_fouling ?? 0).toFixed(2)} %  ` +
                      `mid=${(s.framework.band_mid_pct_excl_fouling ?? 0).toFixed(2)} %  ` +
                      `high=${(s.framework.band_high_pct_excl_fouling ?? 0).toFixed(2)} %`,
                  },
                  {
                    label: "FULL (incl. fouling, for reference)",
                    body:
                      `low=${s.framework.band_low_pct.toFixed(2)} %  ` +
                      `mid=${s.framework.band_mid_pct.toFixed(2)} %  ` +
                      `high=${s.framework.band_high_pct.toFixed(2)} %`,
                  },
                ]}
              />
              <Cell
                label="CONF-WEIGHTED (excl. fouling)"
                value={(s.framework.confidence_weighted_excl_fouling_kwh ?? 0).toFixed(0)}
                unit={`kWh · w=${s.framework.confidence_weight.toFixed(2)}`}
                accent="#60a5fa"
                formula={(() => {
                  const f = s.framework;
                  const validated = f.confidence_basis === "validated_test_set";
                  if (validated) {
                    return [
                      {
                        label: "SOURCE (not self-reported)",
                        body:
                          `held-out labeled test set · n = ${f.validation_n_samples ?? "?"} fault episodes\n` +
                          `not the model's own anomaly_confidence — independent ground truth`,
                      },
                      {
                        label: "FORMULA",
                        body:
                          "w = F1 × (1 − FP_rate)\n" +
                          "conf_weighted_excl = net_excl_fouling × w",
                      },
                      {
                        label: "SUBSTITUTED",
                        body:
                          `w = ${(f.validation_f1 ?? 0).toFixed(2)} × (1 − ${(f.validation_fp_rate ?? 0).toFixed(2)}) ` +
                          `= ${f.confidence_weight.toFixed(3)}\n` +
                          `${(f.net_savings_excl_fouling_kwh ?? 0).toFixed(0)} × ` +
                          `${f.confidence_weight.toFixed(3)} ` +
                          `= ${(f.confidence_weighted_excl_fouling_kwh ?? 0).toFixed(0)} kWh`,
                      },
                      {
                        label: "FULL (incl. fouling, for reference)",
                        body: `${f.confidence_weighted_kwh.toFixed(0)} kWh`,
                      },
                    ];
                  }
                  return [
                    {
                      label: "FORMULA",
                      body:
                        "w = mean_anomaly_confidence × (1 − FP_rate_assumed)\n" +
                        "FP_rate_assumed = 0.075\n" +
                        "conf_weighted_excl = net_excl_fouling × w",
                    },
                    {
                      label: "CAVEAT",
                      body:
                        "uses model's self-reported anomaly_confidence — circular.\n" +
                        "demo mode replaces this with held-out test-set F1.",
                    },
                    {
                      label: "SUBSTITUTED",
                      body:
                        `w = ${(s.mean_anomaly_confidence ?? 0).toFixed(3)} × (1 − 0.075) ` +
                        `= ${f.confidence_weight.toFixed(3)}\n` +
                        `${(f.net_savings_excl_fouling_kwh ?? 0).toFixed(0)} × ` +
                        `${f.confidence_weight.toFixed(3)} ` +
                        `= ${(f.confidence_weighted_excl_fouling_kwh ?? 0).toFixed(0)} kWh`,
                    },
                  ];
                })()}
              />
            </div>

            <div style={{ display: "flex", gap: 8 }}>
              <Cell
                label="BASELINE (PUMP, ANNUAL)"
                value={s.framework.baseline_kwh_annual.toFixed(0)}
                unit="kWh"
                formula={[
                  {
                    label: "FORMULA",
                    body: "mean_kW_pre_fault × annual_operating_hours\n(default hours = 2500, pump-only — no chiller model)",
                  },
                  {
                    label: "SUBSTITUTED",
                    body: `${s.mean_kw_pre_fault.toFixed(3)} kW × 2500 h = ${s.framework.baseline_kwh_annual.toFixed(0)} kWh/yr`,
                  },
                ]}
              />
              <Cell
                label="FAULT SAVINGS (excl. fouling)"
                value={(s.framework.fault_savings_excl_fouling_kwh ?? 0).toFixed(0)}
                unit="kWh"
                formula={[
                  {
                    label: "FORMULA (per fault row)",
                    body: "E_saved_i = events_per_year × (Δt_detect_advantage / 3600) × power_penalty_kW",
                  },
                  {
                    label: "Δt SOURCE",
                    body:
                      "Δt = belimo_detect_s − ai_detect_s (catalog default)\n" +
                      "for the fault that fired this run AND Belimo " +
                      "counterfactual actually triggered, measured latencies " +
                      "replace catalog defaults (see ·measured tag below)",
                  },
                  {
                    label: "EXCLUDED",
                    body:
                      `coil_fouling = ${(s.framework.coil_fouling_kwh ?? 0).toFixed(0)} kWh ` +
                      `(${(100 * (s.framework.coil_fouling_kwh ?? 0) / Math.max(s.framework.fault_savings_kwh, 1e-9)).toFixed(1)}% of full total) — ` +
                      `gated as unvalidated`,
                  },
                  {
                    label: "TOTAL (defensible)",
                    body: `Σ over ${Math.max(0, s.framework.per_fault.length - 1)} validated catalog rows = ${(s.framework.fault_savings_excl_fouling_kwh ?? 0).toFixed(0)} kWh`,
                  },
                ]}
              />
              <Cell
                label="DRIFT AVOIDED"
                value={s.framework.drift_avoided_kwh.toFixed(0)}
                unit={`kWh · c=${s.framework.drift_confidence.toFixed(2)}`}
                formula={[
                  {
                    label: "FORMULA",
                    body:
                      "fraction = (drift_rate × interval²) / (2 × design_ΔT)\n" +
                      "credit = fraction × baseline × base_conf × mean_anomaly_conf",
                  },
                  {
                    label: "DEFAULTS",
                    body: "drift_rate=0.2 °C/yr · interval=1 yr · design_ΔT=6 °C · base_conf=0.6",
                  },
                  {
                    label: "SUBSTITUTED",
                    body:
                      `fraction = (0.2 × 1²) / (2 × 6) = 0.01667\n` +
                      `confidence = 0.6 × ${(s.mean_anomaly_confidence ?? 0).toFixed(3)} ` +
                      `= ${s.framework.drift_confidence.toFixed(3)}\n` +
                      `0.01667 × ${s.framework.baseline_kwh_annual.toFixed(0)} × ` +
                      `${s.framework.drift_confidence.toFixed(3)} = ${s.framework.drift_avoided_kwh.toFixed(0)} kWh`,
                  },
                ]}
              />
              <Cell
                label="OVERHEAD"
                value={s.framework.overhead_kwh.toFixed(0)}
                unit="kWh"
                accent="#f87171"
                formula={(() => {
                  const f = s.framework;
                  const itemized =
                    f.overhead_sensor_polling_kwh != null ||
                    f.overhead_actuator_cycles_kwh != null;
                  if (itemized) {
                    const lines = [
                      `edge compute      = ${(f.overhead_edge_kwh ?? 0).toFixed(1)} kWh   (5 nodes × 10 W × 2500 h)`,
                      `sensor polling    = ${(f.overhead_sensor_polling_kwh ?? 0).toFixed(1)} kWh   (RS-485 master @ ~3 W avg)`,
                      `actuator cycles   = ${(f.overhead_actuator_cycles_kwh ?? 0).toFixed(1)} kWh   (added wear-cycle energy)`,
                      `false-positive    = ${(f.overhead_false_positive_kwh ?? 0).toFixed(1)} kWh   (3 FP/yr × 0.2 kWh)`,
                      `total             = ${f.overhead_kwh.toFixed(1)} kWh`,
                    ];
                    return [
                      {
                        label: "FORMULA",
                        body: "Σ itemized overhead components (no plug figure)",
                      },
                      {
                        label: "ITEMIZED",
                        body: lines.join("\n"),
                      },
                      {
                        label: "RATIO",
                        body: `overhead / gross = ${f.overhead_kwh.toFixed(1)} / ${f.gross_savings_kwh.toFixed(1)} = ${(100 * f.overhead_kwh / Math.max(f.gross_savings_kwh, 0.01)).toFixed(0)} %`,
                      },
                    ];
                  }
                  return [
                    {
                      label: "FORMULA",
                      body:
                        "edge = (edge_W / 1000) × hours × nodes\n" +
                        "fp = fp_events × fp_penalty_kWh\n" +
                        "overhead = edge + fp",
                    },
                    {
                      label: "DEFAULTS",
                      body: "edge_W=10 · hours=2500 · nodes=5 · fp_events=3/yr · fp_penalty=0.2 kWh",
                    },
                    {
                      label: "SUBSTITUTED",
                      body:
                        `edge = 0.010 × 2500 × 5 = ${f.overhead_edge_kwh.toFixed(1)} kWh\n` +
                        `fp = 3 × 0.2 = ${f.overhead_false_positive_kwh.toFixed(1)} kWh\n` +
                        `total = ${f.overhead_kwh.toFixed(1)} kWh`,
                    },
                  ];
                })()}
              />
            </div>

            {(s.framework.coil_fouling_kwh ?? 0) > 0 && (
              <div
                style={{
                  marginTop: 6,
                  paddingTop: 12,
                  borderTop: "1px dashed #fbbf2444",
                  display: "flex",
                  flexDirection: "column",
                  gap: 8,
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
                      background: foulingDefensible ? "#60a5fa" : "#fbbf24",
                      padding: "3px 10px",
                      borderRadius: 3,
                      fontWeight: 700,
                      letterSpacing: "0.14em",
                    }}
                  >
                    {foulingDefensible
                      ? "SENSITIVITY · INCL. FOULING"
                      : "CONDITIONAL ADD-ON · UNVALIDATED"}
                  </span>
                  <span
                    className="mono"
                    style={{ fontSize: 11, color: "#9aacc8", fontStyle: "italic" }}
                  >
                    {foulingDefensible
                      ? "fouling row counted against O&M baseline (21d catch via pressure-drop trending + BMS review)"
                      : "catalog assumes 69-day fouling detection advantage — show only with caveat"}
                  </span>
                </div>
                <div style={{ display: "flex", gap: 8 }}>
                  <Cell
                    label="COIL FOULING kWh"
                    value={(s.framework.coil_fouling_kwh ?? 0).toFixed(0)}
                    unit={foulingDefensible ? "kWh · O&M baseline" : "kWh · catalog"}
                    accent={foulingDefensible ? "#60a5fa" : "#fbbf24"}
                    formula={
                      foulingDefensible
                        ? [
                            {
                              label: "BASELINE (O&M PRACTICE)",
                              body:
                                "maintenance catch = ~21 days (pressure-drop trending,\n" +
                                "quarterly BMS coil-effectiveness review)\n" +
                                "AI signature detect = ~7 days\n" +
                                "Δt advantage = 14 days = 1,209,600 s\n" +
                                "events_per_year = 1, power_penalty_kW = 1.2",
                            },
                            {
                              label: "WHY DEFENSIBLE NOW",
                              body:
                                "prior baseline (Belimo ΔT<4°C for 5 min, never fires for\n" +
                                "fouling) was a vendor-only counterfactual. Real-world\n" +
                                "fouling is caught by maintenance practice well before then.",
                            },
                            {
                              label: "SUBSTITUTED",
                              body: `1 × (1,209,600 / 3600) × 1.2 = ${(s.framework.coil_fouling_kwh ?? 0).toFixed(0)} kWh/yr`,
                            },
                            {
                              label: "STILL SENSITIVE TO",
                              body:
                                "the assumed 21-day O&M catch window. If maintenance is\n" +
                                "weekly, fouling savings ≈ 0. If quarterly only, ≈ 1700.",
                            },
                          ]
                        : [
                            {
                              label: "CATALOG ROW",
                              body:
                                "belimo_detect_s = 7776000 (90 days)\n" +
                                "ai_detect_s = 1814400 (21 days)\n" +
                                "Δt advantage = 5961600 s ≈ 69 days\n" +
                                "events_per_year = 1, power_penalty_kW = 1.2",
                            },
                            {
                              label: "WHY UNVALIDATED",
                              body:
                                "no demo run can observe a 69-day detection delta.\n" +
                                "this row is pure catalog; not measured anywhere.",
                            },
                            {
                              label: "SUBSTITUTED",
                              body: `1 × (5961600 / 3600) × 1.2 = ${(s.framework.coil_fouling_kwh ?? 0).toFixed(0)} kWh/yr`,
                            },
                          ]
                    }
                  />
                  <Cell
                    label="NET % IF INCLUDED"
                    value={s.framework.net_pct_vs_baseline.toFixed(2)}
                    unit="%"
                    accent={foulingDefensible ? "#60a5fa" : "#fbbf24"}
                    formula={[
                      {
                        label: "WITH FOULING",
                        body:
                          `(${s.framework.fault_savings_kwh.toFixed(0)} + ${s.framework.drift_avoided_kwh.toFixed(0)} − ` +
                          `${s.framework.overhead_kwh.toFixed(0)}) / ${s.framework.baseline_kwh_annual.toFixed(0)} × 100 ` +
                          `= ${s.framework.net_pct_vs_baseline.toFixed(2)} %`,
                      },
                      {
                        label: "DEFENSIBLE (excl. fouling)",
                        body: `${(s.framework.net_pct_excl_fouling ?? 0).toFixed(2)} %`,
                      },
                      {
                        label: "DELTA",
                        body:
                          `+${(s.framework.net_pct_vs_baseline - (s.framework.net_pct_excl_fouling ?? 0)).toFixed(2)} pp ` +
                          (foulingDefensible
                            ? "from O&M-baseline fouling row (defensible)"
                            : "from one unvalidated catalog row"),
                      },
                    ]}
                  />
                  <Cell
                    label="CONF-WEIGHTED IF INCLUDED"
                    value={s.framework.confidence_weighted_kwh.toFixed(0)}
                    unit={foulingDefensible ? "kWh · O&M baseline" : "kWh · catalog"}
                    accent={foulingDefensible ? "#60a5fa" : "#fbbf24"}
                    formula={[
                      {
                        label: "WITH FOULING",
                        body: `net_full × w = ${s.framework.net_savings_kwh.toFixed(0)} × ${s.framework.confidence_weight.toFixed(3)} = ${s.framework.confidence_weighted_kwh.toFixed(0)} kWh`,
                      },
                      {
                        label: "DEFENSIBLE",
                        body: `${(s.framework.confidence_weighted_excl_fouling_kwh ?? 0).toFixed(0)} kWh`,
                      },
                    ]}
                  />
                </div>
              </div>
            )}

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
                .{" "}
                {s.belimo_counterfactual_latency_s != null ? (
                  <>
                    Measured latencies replace catalog defaults in the{" "}
                    <span className="mono">low_dT</span> row (see ·measured tag).
                  </>
                ) : (
                  <>
                    Without a Belimo trigger this run, the{" "}
                    <span className="mono">low_dT</span> row falls back to
                    catalog defaults (marked ·catalog).
                  </>
                )}{" "}
                Confidence weight {s.framework.confidence_weight.toFixed(2)} ={" "}
                mean anomaly_confidence × (1 − assumed FP rate).
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
              {s.framework.per_fault.map((f) => {
                const isFouling = f.name === "coil_fouling";
                // Fouling now has two regimes:
                //  - "om_practice" baseline (Δt ≈ 14d, defensible)        → blue O&M-baseline tag
                //  - catalog default (Δt ≈ 69d, vendor-only counterfactual) → amber unvalidated tag
                const foulingDefensible =
                  isFouling &&
                  (f.baseline_source === "om_practice" ||
                    f.detect_advantage_s < 2_000_000);
                const tag = f.measured
                  ? " ·measured"
                  : foulingDefensible
                    ? " ·O&M-baseline"
                    : isFouling
                      ? " ·unvalidated"
                      : " ·catalog";
                const color = f.measured
                  ? "#34d399"
                  : foulingDefensible
                    ? "#60a5fa"
                    : isFouling
                      ? "#fbbf24"
                      : "#9aacc8";
                const hasVariance =
                  f.measured &&
                  f.e_saved_kwh_p10 != null &&
                  f.e_saved_kwh_p90 != null;
                return (
                  <div
                    key={f.name}
                    className="mono"
                    style={{
                      display: "grid",
                      gridTemplateColumns: "200px 110px 80px 90px 1fr",
                      fontSize: 11,
                      color,
                      gap: 8,
                      opacity: isFouling && !foulingDefensible ? 0.85 : 1,
                    }}
                  >
                    <span>
                      {f.name}
                      {tag}
                      {f.n_runs != null && (
                        <span style={{ color: "#9aacc8" }}>
                          {" "}· n={f.n_runs}
                        </span>
                      )}
                    </span>
                    <span>Δt {f.detect_advantage_s.toFixed(0)} s</span>
                    <span>{f.power_penalty_kw.toFixed(1)} kW</span>
                    <span>{f.events_per_year.toFixed(0)} /yr</span>
                    <span style={{ textAlign: "right" }}>
                      {f.e_saved_kwh.toFixed(0)} kWh
                      {hasVariance && (
                        <span style={{ color: "#9aacc8" }}>
                          {" "}[{f.e_saved_kwh_p10.toFixed(1)}–{f.e_saved_kwh_p90.toFixed(1)}]
                        </span>
                      )}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
          );
        })()}

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
