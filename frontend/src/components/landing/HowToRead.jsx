const COLS = [
  {
    badge: "LEFT · KPIs",
    text: "pump kW, ΔT compliance %, per-valve flow — read these to see the system stay in spec while the fault is active",
  },
  {
    badge: "CENTER · CONTROL",
    text: "schematic + agent debate — watch peers reallocate flow under uncertainty and the elected leader trigger recovery",
  },
  {
    badge: "END · SUMMARY",
    text: "measured per-phase pump_kW + framework projection (4.7 % net, band 2.7–6.8 %) appears when the scenario completes",
  },
];

export default function HowToRead() {
  return (
    <div
      style={{
        width: "100%",
        maxWidth: 880,
        display: "grid",
        gridTemplateColumns: "1fr 1fr 1fr",
        gap: 16,
        marginTop: 8,
      }}
    >
      {COLS.map((c) => (
        <div
          key={c.badge}
          style={{
            display: "flex",
            flexDirection: "column",
            gap: 6,
            paddingTop: 12,
            borderTop: "1px solid #2d3d5e",
          }}
        >
          <div
            className="mono"
            style={{
              fontSize: 10,
              color: "#22d3ee",
              letterSpacing: "0.14em",
              fontWeight: 700,
            }}
          >
            {c.badge}
          </div>
          <div style={{ fontSize: 12, color: "#9aacc8", lineHeight: 1.55 }}>
            {c.text}
          </div>
        </div>
      ))}
    </div>
  );
}
