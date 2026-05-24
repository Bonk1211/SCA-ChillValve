import { STORYBOARD } from "./storyboard";

export default function StoryStrip({ stepIdx, onJump }) {
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: `repeat(${STORYBOARD.length}, 1fr)`,
        gap: 4,
        padding: "6px 14px",
        background: "#0f1a30",
        borderBottom: "1px solid #2d3d5e",
      }}
    >
      {STORYBOARD.map((step, i) => {
        const done = i < stepIdx;
        const active = i === stepIdx;
        const color = active ? "#22d3ee" : done ? "#34d399" : "#445574";
        return (
          <div
            key={i}
            onClick={() => onJump(i)}
            style={{
              display: "flex",
              flexDirection: "column",
              gap: 4,
              padding: "4px 8px",
              background: active ? "rgba(34, 211, 238, 0.08)" : "transparent",
              border: `1px solid ${active ? "#22d3ee" : "#2d3d5e"}`,
              borderRadius: 4,
              opacity: done || active ? 1 : 0.55,
              cursor: "pointer",
              transition: "all 0.15s",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <span
                className="mono"
                style={{
                  width: 16,
                  height: 16,
                  borderRadius: "50%",
                  background: done ? color : "#1a2640",
                  border: `1.5px solid ${color}`,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: 9,
                  color: done ? "#0a1224" : color,
                  fontWeight: 700,
                }}
              >
                {done ? "✓" : i + 1}
              </span>
              <span
                className="mono"
                style={{
                  fontSize: 9,
                  color: "#9aacc8",
                  letterSpacing: "0.06em",
                  fontWeight: 600,
                }}
              >
                STEP {i + 1}
              </span>
            </div>
            <div
              className="mono"
              style={{
                fontSize: 11,
                fontWeight: 700,
                color: active ? "#fff" : "#d1dcec",
                letterSpacing: "0.06em",
              }}
            >
              {step.label}
            </div>
          </div>
        );
      })}
    </div>
  );
}
