// Static figures sourced from `sim/energy_framework.py` worked example
// (`compute(MeasuredRun(3600, 21.1, 26.1, 21.1, True, "low_dT", 120, 600,
//  0.85, 2500))`). If DEFAULT_CATALOG is retuned, refresh these.
function Cell({ label, value, unit, accent }) {
  return (
    <div
      style={{
        background: "#0f1a30",
        border: `1.5px solid ${accent ? `${accent}55` : "#2d3d5e"}`,
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
          marginBottom: 5,
        }}
      >
        {label}
      </div>
      <div style={{ display: "flex", alignItems: "baseline", gap: 4, flexWrap: "wrap" }}>
        <span
          className="mono"
          style={{
            fontSize: 22,
            fontWeight: 700,
            color: accent ?? "#fff",
            lineHeight: 1,
          }}
        >
          {value}
        </span>
        <span className="mono" style={{ fontSize: 11, color: "#9aacc8" }}>
          {unit}
        </span>
      </div>
    </div>
  );
}

export default function ClaimCard() {
  return (
    <div
      style={{
        background: "#131f37",
        border: "1px solid #2d3d5e",
        borderRadius: 6,
        padding: "16px 18px",
        display: "flex",
        flexDirection: "column",
        gap: 12,
      }}
    >
      <div
        className="mono"
        style={{
          fontSize: 11,
          color: "#9aacc8",
          letterSpacing: "0.14em",
          fontWeight: 700,
        }}
      >
        DEFENSIBLE ENERGY CLAIM
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
        <Cell label="NET vs BASELINE" value="4.71" unit="%" accent="#34d399" />
        <Cell label="BAND L · M · H" value="2.7 · 4.7 · 6.8" unit="%" />
        <Cell label="CONFIDENCE-WEIGHTED" value="1,954" unit="kWh/yr" accent="#60a5fa" />
        <Cell label="WEIGHT" value="0.79" unit="× run conf · (1−FP)" />
      </div>
      <div
        style={{
          fontSize: 11,
          color: "#9aacc8",
          lineHeight: 1.5,
          fontStyle: "italic",
        }}
      >
        Worked-example output of <span className="mono">sim/energy_framework.py</span>.
        Run a scenario in the simulator to see this recomputed with the run's
        measured detection latency and confidence.
      </div>
    </div>
  );
}
