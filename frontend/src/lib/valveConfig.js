// Static per-valve config the backend doesn't emit (labels, zone, design flow).
// Mirrors sim/system.py defaults — keep in sync if the hydraulic config changes.
export const VALVES = [
  { id: "A1", branch: "A", label: "CRAH-01", zone: "DC-HALL-N",  size: "DN65",  designFlowGpm: 50 },
  { id: "A2", branch: "A", label: "CRAH-02", zone: "DC-HALL-M",  size: "DN65",  designFlowGpm: 50 },
  { id: "A3", branch: "A", label: "CRAH-03", zone: "DC-HALL-S",  size: "DN65",  designFlowGpm: 50 },
  { id: "B1", branch: "B", label: "AHU-01",  zone: "MEP-WEST",   size: "DN100", designFlowGpm: 150 },
  { id: "B2", branch: "B", label: "AHU-02",  zone: "MEP-EAST",   size: "DN100", designFlowGpm: 150 },
  { id: "B3", branch: "B", label: "AHU-03",  zone: "OFFICE-N",   size: "DN100", designFlowGpm: 150 },
];

export const VALVE_BY_ID = Object.fromEntries(VALVES.map((v) => [v.id, v]));

export const TARGET_DT_C = 5.0;
export const DT_TOLERANCE_C = 0.7;

// Market-reference pump power for a Belimo PICV / Energy Valve-controlled
// loop at the same design conditions (≈460 GPM, ≈165 kPa head). Derived from
// Belimo EV/EPIV product datasheet typical pump-power figures for a 5 MW DC
// chilled-water loop with conventional valve coordination. Used only as a
// static reference for the ENERGY SAVINGS KPI — adjust if you cite a
// different Belimo product line in the demo.
export const BELIMO_REFERENCE_KW = 20.5;

