const ACCENT_BY_LABEL = {
  BASELINE: "#22d3ee",
  "FAULT INJECT": "#fbbf24",
  "ANOMALY DETECTED": "#a78bfa",
  "MULTI-AGENT DEBATE": "#a78bfa",
  RECOVERY: "#34d399",
  COMPLETE: "#ffffff",
};

export default function ScenarioBanner({ step }) {
  if (!step) return null;
  const accent = ACCENT_BY_LABEL[step.label] || "#22d3ee";
  return (
    <div
      style={{
        padding: "8px 12px",
        background: `linear-gradient(135deg, ${accent}15, #1a2640)`,
        border: `1px solid ${accent}44`,
        borderLeft: `4px solid ${accent}`,
        borderRadius: 6,
        display: "flex",
        flexDirection: "column",
        gap: 4,
      }}
    >
      <div style={{ display: "flex", alignItems: "baseline", gap: 10, flexWrap: "wrap" }}>
        <span
          className="mono"
          style={{
            fontSize: 10,
            fontWeight: 700,
            color: accent,
            letterSpacing: "0.14em",
            padding: "2px 8px",
            background: `${accent}1c`,
            borderRadius: 3,
          }}
        >
          {step.label}
        </span>
        <span style={{ fontSize: 14, fontWeight: 700, color: "#fff", letterSpacing: "0.01em" }}>
          {step.headline}
        </span>
      </div>
      <div
        style={{
          fontSize: 11,
          color: "#d1dcec",
          lineHeight: 1.3,
          display: "-webkit-box",
          WebkitLineClamp: 2,
          WebkitBoxOrient: "vertical",
          overflow: "hidden",
        }}
      >
        {step.detail}
      </div>
    </div>
  );
}
