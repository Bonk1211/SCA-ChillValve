# ChillValve — Algorithm Pseudocode

Reference implementation for the report. Each valve runs all three layers in
parallel every simulation tick. Layer 1 has hard override authority; Layer 2
is informational; Layer 3 generates setpoint recommendations applied by
Layer 1–validated control.

For the runnable code see:
- `sim/layers/layer1_rules.py`
- `sim/layers/layer2_ml.py`
- `sim/layers/layer3_agent.py`
- `sim/controllers/chillvalve.py`
- `sim/broker.py`

---

## Per-valve tick loop

```text
INITIALIZE
  load isolation_forest, feature_scaler from data/models/
  load deployment_threshold from training_metadata.json
  connect to in-process MessageBroker
  determine initial leader: lowest valve_id in branch

EVERY TICK (1 simulated second):

  state = read_sensors(valve_hardware)
  state.dT = state.return_temp - state.supply_temp

  # ---- LAYER 1: deterministic rules (microseconds) ----
  rule_action = evaluate_rules(state)
  if rule_action.severity == CRITICAL:
    apply(rule_action)
    return                                    # bypass layers 2 and 3

  # ---- LAYER 2: ML anomaly detection (every 10 ticks) ----
  if tick % 10 == 0:
    features = [
      state.position_pct / 100,               # CHWC_VLV
      state.dT_C,                             # dT_coil
      state.flow_gpm,                         # SA_CFM (flow magnitude)
      sin(2π * hour_of_day / 24),             # hour_sin
      cos(2π * hour_of_day / 24),             # hour_cos
    ]
    features_scaled = scaler.transform(features)
    raw = isolation_forest.decision_function(features_scaled)
    anomaly_score = -raw                      # higher = more anomalous
    state.anomaly_detected = (anomaly_score >= deployment_threshold)
    state.anomaly_confidence = clamp(
      (anomaly_score - threshold) / window + 0.5, 0, 1
    )

  # ---- LAYER 3: multi-agent coordination (every 5 ticks) ----
  if tick % 5 == 0:
    # Two-phase: broadcast all, then process all.
    broadcast(channel=branch_id+"/state", payload=state)
    peer_states = collect_recent(channel=branch_id+"/state")

    if is_leader:
      if missed_heartbeats > 3:
        step_down()
        broadcast_election()
      else:
        aggregate = sum(peer.capacity_demand for peer in peer_states)
        pump_setpoint = compute_optimal_pump_pressure(aggregate)
        valve_setpoints = allocate_with_priority(peer_states)
        broadcast(channel=branch_id+"/setpoints", payload=valve_setpoints)

    else:
      received = consume_latest_setpoint(channel=branch_id+"/setpoints")
      if received and not stale(received):
        target_position = received
        last_leader_heartbeat = now
      else:
        target_position = local_pid(state)

      if (now - last_leader_heartbeat) > 15s:
        trigger_election()

  # ---- LAYER 1 final validation (always runs) ----
  final = layer1.validate_command(target_position, state)
  actuator.move_to(final)
```

---

## Layer 1 rules (PRD §5.1)

```text
Rule 1: position_out_of_bounds
  if not 0 <= position_pct <= 100:
    return RuleAction(clamp_position, value=clip(position, 0, 100))

Rule 2: flow_exceeds_max_110pct
  if flow_gpm > flow_max_per_valve * 1.10:
    return RuleAction(reduce_position, value=position * 0.9)

Rule 3: dP_exceeds_600kPa                      # CRITICAL
  if dP_kPa > 600:
    return RuleAction(emergency_close, value=0)

Rule 4: sensor_invalid                          # CRITICAL
  if any isnan/inf in (flow, dT, dP):
    return RuleAction(use_last_known_good, value=last_known_good[valve_id])

Rule 5: actuator_unresponsive                   # CRITICAL
  if commanded_position_age > 30s and
     abs(actual - commanded) > 0.05:
    return RuleAction(raise_fault, value=None)

else:
  last_known_good[valve_id] = (flow, dT, dP)
  return None
```

---

## Bully leader election (synchronous adaptation)

```text
ELECTION (on heartbeat timeout, per branch):

  start_election:
    broadcast(channel=branch+"/election", payload={candidate: my_id})
    election.started_at = now

  every subsequent tick during the 3-second election window:
    accumulate peer election broadcasts

  when (now - election.started_at) >= 3s:
    candidates = {self.id} ∪ {msg.payload.candidate for msg in election_msgs
                              if msg.sender in branch_members and not msg.sender.is_dead}
    new_leader = min(candidates)
    self.is_leader = (new_leader == self.id)
    if self.is_leader:
      start_sending_heartbeats()
```

PRD §5.3 expresses election with `await asyncio.sleep(3.0)`. The sync engine
runs election across multiple ticks instead — the state machine straddles the
3-second window naturally and the leader is chosen at the first tick past the
window's end.

---

## ChillValve controller orchestration (PRD §6)

```text
step(states, t_seconds):

  # Layer 2: enrich every state with anomaly info.
  for s in states:
    ar = layer2.evaluate(s, tick_seconds=t_seconds)
    s.anomaly_detected = ar.anomaly_detected
    s.anomaly_confidence = ar.confidence

  # Layer 3: two-phase tick (broadcast all → process all).
  for s in states:
    agents[s.valve_id].broadcast_state(s, t_seconds)
  for s in states:
    agents[s.valve_id].process(all_ids, t_seconds)
    s.is_leader = agents[s.valve_id].is_leader

  # Per-valve decision:
  for s in states:
    rule = layer1.evaluate(s, t_seconds)
    if rule and rule.action in CRITICAL_ACTIONS:
      s.rule_fired = rule.reason
      s.safety_override_active = True
      emit ValveCommand(rule.value, override=True)
      continue

    if rule:
      s.rule_fired = rule.reason

    setpoint = agents[s.valve_id].consume_setpoint()
    if setpoint is not None:
      pos = setpoint
    else:
      err = s.dT_C - TARGET_DT
      pos = s.position_pct + err * GAIN     # local PID fallback

    pos = layer1.validate_command(pos, s)   # final clamp + dP failsafe
    emit ValveCommand(pos, override=False)
```
