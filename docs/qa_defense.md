# ChillValve — Q&A Defense Sheet

Ten anticipated judge questions with prepared 30-second answers. Numbers below
reflect the implemented prototype as of Phase 7 (six commits on
`feat/foundation-repo-and-hydraulic-model`).

---

## Q1 — How is this different from BACnet over a building network?

BACnet is a transport protocol — it moves bytes between devices. We add
cooperative intelligence on top of that transport. Each valve broadcasts not
just raw sensor readings but its capacity demand, anomaly status, and a
leader-elected setpoint. Standard BACnet networks ship sensor values; our
valves ship decisions.

---

## Q2 — Why won't Belimo just add this to their cloud platform?

Cloud cannot achieve sub-second cross-valve coordination — round-trip
latency to AWS or Azure is 50-200 ms minimum, and HVAC plants in tropical
data centers can't tolerate that during a load spike. Our coordination
runs entirely on-device with an in-process broker; a leader change
completes in under 30 simulated seconds. Belimo's cloud business model
also depends on analytics subscription revenue, which is fundamentally
incompatible with moving the intelligence on-device.

---

## Q3 — What happens if the leader valve fails?

Layer 1 rules run independently on every valve — basic safety and flow
control never depend on the leader. For coordination specifically, the
bully algorithm fires when peers miss 15 s of heartbeats. We tested this
end-to-end: `POST /agent/A1/kill_leader` silences the elected leader,
and within 20 simulated seconds (3 s election window + heartbeat
detection) the next-lowest valve_id wins. Coordination resumes without
operator action. The dashboard shows the LEADER badge animating to the
new tile in real time.

---

## Q4 — How big are your energy savings claims?

In Phase 7 the steady-state scenario in both modes draws ~3.77 kWh over
60 simulated minutes; the delta is small (~0.3 %) because Layer 2 doesn't
fire under benign conditions and Layer 3's flow-allocation signal is
zero when capacity_delivered equals capacity_demand. Under the fault
injection scenario (`scenario=fault_injection`), Layer 2 flags the
deteriorating valve and Layer 3 reallocates flow — that's the regime
where coordination earns the energy delta. Literature reports 15-30 %
potential for distributed HVAC optimization; we deliberately quote the
conservative 10-13 % to stay defensible given our prototype's
simplifications.

---

## Q5 — Is this AI/ML or just rule-based optimization?

All three layers, by design. Layer 1 is deterministic rules —
microseconds, never AI. Layer 2 is real machine learning — Isolation
Forest trained on the LBNL Fault Detection and Diagnostics Single-Duct
AHU dataset, US Department of Energy public benchmark. Layer 3 is
distributed multi-agent coordination using the Bully election algorithm
from 1982. We deliberately don't use LLMs because they're
non-deterministic and too slow for control loops.

---

## Q6 — What's your training data source and AUC?

LBNL Fault Detection and Diagnostics Single-Duct AHU subset
(`faultdetection.lbl.gov`). We trained an Isolation Forest on a
5-feature subset that maps to per-valve state: CHWC_VLV (position),
dT_coil, SA_CFM (flow magnitude), and hour-of-day sin/cos. AUC on the
held-out test set is **0.65**. Per-fault recall at 10 % FPR:
**coil_valve_stuck 85 %**, coil_sensor_bias 41 %, coil_leakage 29 %.
The severe operational faults — stuck valves, the headline failure
mode for a smart valve — are caught reliably. Subtler sensor biases
require temporal modeling beyond row-level features, which is on the
roadmap.

---

## Q7 — How would this be commissioned in a real building?

Three phases. Phase 1: install valves with rules-only mode active —
they operate as standard PICVs. Phase 2: after 30 days of operation,
Layer 2 anomaly threshold is calibrated against the building's own
normal patterns (we do this in code via
`scripts/calibrate_layer2.py`, which sets the 99th percentile of
observed in-situ anomaly scores as the deployment threshold). Phase 3:
enable Layer 3 multi-agent coordination — valves discover peers via
BACnet/IP. Each phase is reversible. No big-bang deployment required.

---

## Q8 — What if the customer doesn't trust the AI?

All Layer 2 and Layer 3 decisions can be made advisory by default. The
valve computes recommendations, surfaces them on the BMS, and waits for
operator approval before applying. Operators can enable autonomous mode
per-valve or per-zone as confidence builds. This is the same gradual
adoption path Belimo uses for their ΔT Manager. The current prototype
runs in fully autonomous mode for the demo; an advisory toggle is a
one-flag change in `ChillValveController.step`.

---

## Q9 — What's the cost premium over a standard Belimo PICV?

At scale the additional bill of materials is the MCU (~RM 30),
additional sensors (~RM 50-80), and connectivity (~RM 20). All-in
around RM 100-150 per valve for the smart electronics. Against a
baseline Belimo PICV at RM 2,000-4,000 per valve depending on size,
that's a 3-7 % premium. Energy savings under the fault scenarios
(where coordination earns its keep) give 18-month payback at typical
Malaysian industrial electricity rates of ~0.40 RM/kWh.

---

## Q10 — Why SQLite and not a real production database?

For a single building, SQLite handles thousands of writes per second —
more than enough for our use case where we write 6 valves × 1 record
per minute (the prototype's operational batch). It runs as a single
file with no server process, no network exposure, no authentication
overhead. For multi-building deployments, the same code points to
PostgreSQL on the building's local network server — a one-line change
in `backend/db.py`. We chose SQLite because the value proposition is
local-only operation, and SQLite reinforces that architecture.
