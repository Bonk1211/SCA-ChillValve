import { useDashboardStore } from "../../store/useDashboardStore";

const KIND_COLOR = {
  rule: "#f87171",
  anomaly: "#fbbf24",
  leader: "#22d3ee",
  election: "#a78bfa",
  ctrl: "#34d399",
  fault: "#fbbf24",
  story: "#22d3ee",
  debate: "#a78bfa",
  remediation: "#34d399",
};

function fmtTime(ts) {
  if (!ts) return "--:--:--";
  return new Date(ts).toTimeString().slice(0, 8);
}

export default function EventLog({
  title = "EVENT LOG",
  accent = "#9aacc8",
  kinds,            // optional string[]; if set, only events whose .kind is in this list show
  emptyText = "no events yet",
  layerBadge,       // optional small chip text (e.g., "L1")
}) {
  const allEvents = useDashboardStore((s) => s.events);
  const events = kinds ? allEvents.filter((e) => kinds.includes(e.kind)) : allEvents;
  return (
    <div
      style={{
        background: "#1a2640",
        border: `1px solid ${accent}33`,
        borderLeft: `3px solid ${accent}`,
        borderRadius: 4,
        padding: 6,
        minHeight: 0,
        minWidth: 0,
        display: "flex",
        flexDirection: "column",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 6,
          marginBottom: 4,
          flexShrink: 0,
        }}
      >
        {layerBadge && (
          <span
            className="mono"
            style={{
              fontSize: 8,
              color: "#0a1224",
              background: accent,
              padding: "1px 4px",
              borderRadius: 2,
              fontWeight: 700,
              letterSpacing: "0.08em",
            }}
          >
            {layerBadge}
          </span>
        )}
        <span
          className="mono"
          style={{
            fontSize: 10,
            color: accent,
            fontWeight: 700,
            letterSpacing: "0.1em",
            flex: 1,
          }}
        >
          {title}
        </span>
        <span
          className="mono"
          style={{ fontSize: 9, color: "#9aacc8", fontWeight: 600 }}
        >
          {events.length}
        </span>
      </div>
      <div
        className="mono"
        style={{
          background: "#0a1224",
          border: "1px solid #2d3d5e",
          borderRadius: 3,
          padding: 6,
          fontSize: 10,
          flex: 1,
          minHeight: 60,
          overflowY: "auto",
          display: "flex",
          flexDirection: "column-reverse",
          lineHeight: 1.45,
        }}
      >
        {events.length === 0 ? (
          <div style={{ color: "#9aacc8", fontStyle: "italic", fontSize: 10 }}>
            {emptyText}
          </div>
        ) : (
          events
            .slice()
            .reverse()
            .map((e, i) => (
              <div key={i} style={{ color: "#d1dcec", marginBottom: 2 }}>
                <span style={{ color: "#6b7c98" }}>{fmtTime(e.ts)}</span>{" "}
                <span style={{ color: KIND_COLOR[e.kind] || "#d1dcec", fontWeight: 600 }}>
                  [{e.kind}]
                </span>{" "}
                <span style={{ color: "#fff" }}>{e.text}</span>
                {e.explanation && (
                  <div
                    style={{
                      marginLeft: 10,
                      marginTop: 1,
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
