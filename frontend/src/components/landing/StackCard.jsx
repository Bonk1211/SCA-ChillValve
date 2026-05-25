const ROWS = [
  { tag: "L1", dot: "#f87171", text: "deterministic safety rules · clamp, close, last-known-good" },
  { tag: "L2", dot: "#fbbf24", text: "ML anomaly detection · confidence-scored, never silent" },
  { tag: "L3", dot: "#a78bfa", text: "LLM peer debate + autonomous recovery" },
];

export default function StackCard() {
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
        3-LAYER STACK
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {ROWS.map((r) => (
          <div
            key={r.tag}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 12,
              fontSize: 13,
              color: "#d1dcec",
              lineHeight: 1.4,
            }}
          >
            <span
              style={{
                width: 9,
                height: 9,
                borderRadius: "50%",
                background: r.dot,
                boxShadow: `0 0 6px ${r.dot}66`,
                flexShrink: 0,
              }}
            />
            <span
              className="mono"
              style={{
                color: "#fff",
                fontWeight: 700,
                fontSize: 12,
                letterSpacing: "0.08em",
                minWidth: 22,
              }}
            >
              {r.tag}
            </span>
            <span>{r.text}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
