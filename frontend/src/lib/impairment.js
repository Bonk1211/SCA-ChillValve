import { VALVE_BY_ID } from "./valveConfig";

// Mirror of backend/debate.py:_peer_speech's impaired check.
// Frontend single source of truth for "is this valve in trouble" — used by
// both the ACTIVE ANOMALIES KPI counter and the schematic/table LED color.
//
// Reason: the L3 debate panel labels valves IMPAIRED on a lower confidence
// threshold (>0.4) than the backend's anomaly_detected boolean (>0.5). The
// dashboard would contradict itself if the KPI counter used anomaly_detected
// while the L3 panel used the lower-threshold heuristic. Mirror the L3
// definition so every panel agrees on what "impaired" means.
export function isImpaired(valve) {
  if (!valve) return false;
  const cfg = VALVE_BY_ID[valve.valve_id];
  const designFlow = cfg?.designFlowGpm ?? 50;
  return valve.flow_gpm < 0.6 * designFlow || valve.anomaly_confidence > 0.4;
}
