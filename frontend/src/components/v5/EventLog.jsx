import { useDashboardStore } from "../../store/useDashboardStore";

function kindColor(k) {
  return (
    {
      rule: "#f87171",
      anomaly: "#fbbf24",
      leader: "#22d3ee",
      election: "#a78bfa",
      ctrl: "#34d399",
      fault: "#fbbf24",
      story: "#22d3ee",
      debate: "#a78bfa",
    }[k] || "#d1dcec"
  );
}

function fmtTime(ts) {
  if (!ts) return "--:--:--";
  return new Date(ts).toTimeString().slice(0, 8);
}

export default function EventLog() {
  const events = useDashboardStore((s) => s.events);
  return (
    <div
      style={{
        background: "#1a2640",
        border: "1px solid #2d3d5e",
        borderRadius: 6,
        padding: 8,
        flex: 1,
        minHeight: 0,
        display: "flex",
        flexDirection: "column",
      }}
    >
      <div
        className="mono"
        style={{
          fontSize: 10,
          color: "#fff",
          fontWeight: 700,
          letterSpacing: "0.1em",
          marginBottom: 5,
        }}
      >
        EVENT LOG
      </div>
      <div
        className="mono"
        style={{
          background: "#0a1224",
          border: "1px solid #2d3d5e",
          borderRadius: 4,
          padding: 7,
          fontSize: 10,
          flex: 1,
          minHeight: 120,
          maxHeight: 320,
          overflowY: "auto",
          display: "flex",
          flexDirection: "column-reverse",
          lineHeight: 1.5,
        }}
      >
        {events.length === 0 ? (
          <div style={{ color: "#9aacc8", fontStyle: "italic" }}>no events yet</div>
        ) : (
          events
            .slice()
            .reverse()
            .map((e, i) => (
              <div key={i} style={{ color: "#d1dcec", marginBottom: 2 }}>
                <span style={{ color: "#9aacc8" }}>{fmtTime(e.ts)}</span>{" "}
                <span style={{ color: kindColor(e.kind), fontWeight: 600 }}>[{e.kind}]</span>{" "}
                <span style={{ color: "#fff" }}>{e.text}</span>
                {e.explanation && (
                  <div
                    style={{
                      marginLeft: 14,
                      marginTop: 2,
                      color: "#9aacc8",
                      fontStyle: "italic",
                    }}
                  >
                    ↳ {e.explanation}
                  </div>
                )}
              </div>
            ))
        )}
      </div>
    </div>
  );
}
