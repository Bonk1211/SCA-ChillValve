export default function TitleBar({ connection, engineStatus }) {
  const connColor =
    { connected: "#34d399", connecting: "#fbbf24", disconnected: "#f87171" }[connection] ||
    "#9aacc8";
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "6px 14px",
        borderBottom: "1px solid #2d3d5e",
        background: "linear-gradient(180deg, #131f37 0%, #0a1224 100%)",
        gap: 16,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <a
          href="#"
          onClick={(e) => {
            e.preventDefault();
            // Clearing the hash with `=""` doesn't always dispatch hashchange
            // (browsers may consider "" → "" a no-op). Fire it explicitly.
            const had = window.location.hash !== "";
            window.location.hash = "";
            if (!had) {
              window.dispatchEvent(new HashChangeEvent("hashchange"));
            }
          }}
          className="mono"
          title="back to intro"
          style={{
            fontSize: 10,
            color: "#9aacc8",
            letterSpacing: "0.12em",
            textDecoration: "none",
            padding: "2px 6px",
            borderRadius: 3,
            border: "1px solid #2d3d5e",
          }}
        >
          ← intro
        </a>
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
          <path d="M12 2 L20 7 L20 17 L12 22 L4 17 L4 7 Z" stroke="#22d3ee" strokeWidth="1.5" />
          <circle cx="12" cy="12" r="3.5" fill="#22d3ee" />
        </svg>
        <div>
          <div style={{ fontSize: 14, fontWeight: 700, color: "#fff", letterSpacing: "0.02em" }}>
            ChillValve <span style={{ color: "#22d3ee" }}>Simulator</span>
            <span
              className="mono"
              style={{
                fontSize: 11,
                color: "#9aacc8",
                fontWeight: 600,
                marginLeft: 10,
                letterSpacing: "0.08em",
              }}
            >
              AUTONOMOUS SCENARIO DEMO · v5 · LIVE
            </span>
          </div>
          <div
            className="mono"
            style={{ fontSize: 10, color: "#9aacc8", letterSpacing: "0.06em", marginTop: 2 }}
          >
            SCA · CYBERJAYA-DC-04 · 5MW TIER 3
          </div>
        </div>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
        <span
          className="mono"
          style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11, color: "#d1dcec" }}
        >
          <span
            style={{
              width: 8,
              height: 8,
              borderRadius: "50%",
              background: connColor,
              boxShadow: `0 0 6px ${connColor}`,
            }}
          />
          ws · {connection}
        </span>
        <span className="mono" style={{ fontSize: 11, color: "#9aacc8" }}>
          engine · {engineStatus.engine}
          {engineStatus.tick > 0 && ` · t=${engineStatus.tick}`}
          {engineStatus.mode && ` · ${engineStatus.mode}`}
        </span>
      </div>
    </div>
  );
}
