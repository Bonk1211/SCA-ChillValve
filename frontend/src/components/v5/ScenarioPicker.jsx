import { SCENARIOS } from "./scenarios";

export default function ScenarioPicker({ currentId, onPick, busy }) {
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: `repeat(${SCENARIOS.length}, 1fr)`,
        gap: 6,
        padding: "6px 14px",
        background: "#0f1a30",
        borderBottom: "1px solid #2d3d5e",
      }}
    >
      {SCENARIOS.map((s, i) => {
        const active = currentId === s.id;
        return (
          <button
            key={s.id}
            onClick={() => !busy && onPick(s.id)}
            disabled={busy}
            className="mono"
            style={{
              display: "flex",
              flexDirection: "column",
              gap: 3,
              padding: "6px 10px",
              background: active ? `${s.accent}1c` : "transparent",
              border: `1px solid ${active ? s.accent : "#2d3d5e"}`,
              borderRadius: 4,
              cursor: busy ? "wait" : "pointer",
              textAlign: "left",
              transition: "all 0.15s",
              opacity: busy && !active ? 0.4 : 1,
              color: "inherit",
              fontFamily: "inherit",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <span
                className="mono"
                style={{
                  fontSize: 9,
                  fontWeight: 700,
                  color: "#9aacc8",
                  letterSpacing: "0.1em",
                }}
              >
                SCENARIO {i + 1}
              </span>
              <span
                className="mono"
                style={{
                  fontSize: 11,
                  fontWeight: 700,
                  color: active ? "#fff" : "#d1dcec",
                  letterSpacing: "0.08em",
                }}
              >
                {s.label}
              </span>
              {active && (
                <span
                  className="mono"
                  style={{
                    marginLeft: "auto",
                    fontSize: 8,
                    fontWeight: 700,
                    color: "#0a1224",
                    background: s.accent,
                    padding: "1px 5px",
                    borderRadius: 2,
                    letterSpacing: "0.1em",
                  }}
                >
                  RUNNING
                </span>
              )}
              <span
                style={{
                  marginLeft: active ? 0 : "auto",
                  display: "flex",
                  gap: 3,
                }}
              >
                {s.expectedLayers.map((l) => (
                  <span
                    key={l}
                    className="mono"
                    style={{
                      fontSize: 7,
                      fontWeight: 700,
                      color:
                        l === "L1" ? "#f87171" : l === "L2" ? "#fbbf24" : "#a78bfa",
                      border: `1px solid ${
                        l === "L1" ? "#f87171" : l === "L2" ? "#fbbf24" : "#a78bfa"
                      }`,
                      padding: "0px 3px",
                      borderRadius: 2,
                      letterSpacing: "0.1em",
                    }}
                  >
                    {l}
                  </span>
                ))}
              </span>
            </div>
            <div
              style={{
                fontSize: 10,
                color: active ? "#d1dcec" : "#9aacc8",
                fontFamily: "Inter, system-ui, sans-serif",
                lineHeight: 1.3,
              }}
            >
              {s.headline}
            </div>
          </button>
        );
      })}
    </div>
  );
}
