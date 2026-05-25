export default function Hero() {
  return (
    <div
      style={{
        textAlign: "center",
        maxWidth: 720,
        display: "flex",
        flexDirection: "column",
        gap: 14,
        animation: "heroFadeIn 0.5s ease-out",
      }}
    >
      <div
        style={{
          fontSize: 48,
          fontWeight: 800,
          letterSpacing: "-0.02em",
          color: "#fff",
          lineHeight: 1,
        }}
      >
        Chill<span style={{ color: "#22d3ee" }}>Valve</span>
      </div>
      <div
        className="mono"
        style={{
          fontSize: 12,
          color: "#9aacc8",
          letterSpacing: "0.18em",
          textTransform: "uppercase",
        }}
      >
        Agentic chilled-water control
      </div>
      <div
        style={{
          fontSize: 16,
          color: "#d1dcec",
          lineHeight: 1.55,
          maxWidth: 640,
          margin: "8px auto 0",
        }}
      >
        Belimo Δ-T Manager waits for the threshold to break. ChillValve sees the
        pattern that leads to the break — minutes earlier, with a confidence
        signal you can audit.
      </div>
      <style>{`
        @keyframes heroFadeIn {
          from { opacity: 0; transform: translateY(8px); }
          to   { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  );
}
