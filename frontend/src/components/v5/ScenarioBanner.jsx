export default function ScenarioBanner({ scenario, engineState, tick }) {
  if (!scenario) {
    return (
      <div
        style={{
          padding: "8px 12px",
          background: "#1a2640",
          border: "1px solid #2d3d5e",
          borderRadius: 6,
          color: "#9aacc8",
          fontSize: 12,
          fontStyle: "italic",
        }}
      >
        Pick a scenario above to start.
      </div>
    );
  }
  const accent = scenario.accent || "#22d3ee";
  const isRunning = engineState === "running";
  const isPaused = engineState === "paused";
  return (
    <div
      style={{
        padding: "8px 12px",
        background: `linear-gradient(135deg, ${accent}15, #1a2640)`,
        border: `1px solid ${accent}44`,
        borderLeft: `4px solid ${accent}`,
        borderRadius: 6,
        display: "grid",
        gridTemplateColumns: "1fr auto",
        gap: 10,
        alignItems: "start",
      }}
    >
      <div style={{ display: "flex", flexDirection: "column", gap: 3, minWidth: 0 }}>
        <div style={{ display: "flex", alignItems: "baseline", gap: 8, flexWrap: "wrap" }}>
          <span
            className="mono"
            style={{
              fontSize: 9,
              fontWeight: 700,
              color: accent,
              letterSpacing: "0.14em",
              padding: "2px 6px",
              background: `${accent}1c`,
              borderRadius: 3,
            }}
          >
            {scenario.label}
          </span>
          <span
            style={{
              fontSize: 14,
              fontWeight: 700,
              color: "#fff",
              letterSpacing: "0.01em",
            }}
          >
            {scenario.headline}
          </span>
          <span
            className="mono"
            style={{ fontSize: 9, color: "#9aacc8", fontWeight: 600 }}
          >
            {isRunning ? `LIVE · t=${tick}s / ${scenario.durationS}s` : isPaused ? "PAUSED" : "READY"}
          </span>
        </div>
        <div
          style={{
            fontSize: 10,
            color: "#d1dcec",
            lineHeight: 1.3,
            display: "-webkit-box",
            WebkitLineClamp: 2,
            WebkitBoxOrient: "vertical",
            overflow: "hidden",
          }}
        >
          {scenario.detail}
        </div>
      </div>
      {scenario.watchFor && scenario.watchFor.length > 0 && (
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: 2,
            fontSize: 9,
            color: "#9aacc8",
            fontFamily: "JetBrains Mono, monospace",
            minWidth: 230,
            maxWidth: 320,
          }}
        >
          <span
            className="mono"
            style={{ fontSize: 8, color: accent, fontWeight: 700, letterSpacing: "0.12em" }}
          >
            WATCH FOR
          </span>
          {scenario.watchFor.map((w, i) => (
            <span key={i} style={{ lineHeight: 1.3 }}>
              · {w}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
