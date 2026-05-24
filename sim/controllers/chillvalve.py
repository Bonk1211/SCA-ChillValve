"""ChillValve controller. PRD §6.

Orchestrates Layer 1 (rules), Layer 2 (ML), Layer 3 (multi-agent).
Layer 1 has hard override; Layer 2 is informational; Layer 3 provides
setpoints with fallback to local PID.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from sim.broker import MessageBroker
from sim.layers.layer1_rules import CRITICAL_ACTIONS, Layer1Rules
from sim.layers.layer2_ml import Layer2ML
from sim.layers.layer3_agent import ValveAgent
from sim.types import ValveCommand, ValveState

LOCAL_PID_TARGET_DT = 5.0
LOCAL_PID_GAIN = 1.5   # %/°C error


@dataclass
class ChillValveController:
    layer1: Layer1Rules = field(default_factory=Layer1Rules)
    layer2: Layer2ML = field(default_factory=Layer2ML)
    broker: MessageBroker = field(default_factory=MessageBroker)
    agents: Dict[str, ValveAgent] = field(default_factory=dict)
    _initialized_at: float = -1.0

    def initialize(
        self,
        valve_ids: List[str],
        flow_max_per_valve: Dict[str, float],
        t_seconds: float,
    ) -> None:
        self.layer1.flow_max_gpm_per_valve = dict(flow_max_per_valve)
        for vid in valve_ids:
            branch_id = vid[0]
            self.agents[vid] = ValveAgent(valve_id=vid, branch_id=branch_id, broker=self.broker)
        # Deterministic boot: lowest id per branch is leader.
        branches = {vid[0] for vid in valve_ids}
        for branch_id in branches:
            members = sorted(vid for vid in valve_ids if vid.startswith(branch_id))
            if members:
                self.agents[members[0]].is_leader = True
                self.agents[members[0]].last_leader_heartbeat = t_seconds
        self._initialized_at = t_seconds

    def step(
        self, states: List[ValveState], t_seconds: float
    ) -> Dict[str, ValveCommand]:
        all_ids = [s.valve_id for s in states]
        commands: Dict[str, ValveCommand] = {}

        # Layer 2: enrich each state with anomaly info.
        for s in states:
            ar = self.layer2.evaluate(s, tick_seconds=int(t_seconds))
            s.anomaly_detected = ar.anomaly_detected
            s.anomaly_confidence = ar.confidence

        # Layer 3: two-phase tick.
        for s in states:
            self.agents[s.valve_id].broadcast_state(s, t_seconds)
        for s in states:
            agent = self.agents[s.valve_id]
            agent.process(all_ids, t_seconds)
            s.is_leader = agent.is_leader

        # Per-valve decision: Layer 1 override → Layer 3 setpoint → local PID → Layer 1 validate.
        for s in states:
            rule_action = self.layer1.evaluate(s, t_seconds)
            if rule_action is not None and rule_action.action in CRITICAL_ACTIONS:
                s.rule_fired = rule_action.reason
                s.safety_override_active = True
                pos = rule_action.value if rule_action.value is not None else 0.0
                commands[s.valve_id] = ValveCommand(position_pct=pos, override=True)
                self.layer1.record_command(s.valve_id, pos / 100.0, t_seconds)
                continue

            if rule_action is not None:
                s.rule_fired = rule_action.reason

            agent = self.agents[s.valve_id]
            setpoint = agent.consume_setpoint()
            if setpoint is not None:
                pos = setpoint
            else:
                err = s.dT_C - LOCAL_PID_TARGET_DT
                pos = s.position_pct + err * LOCAL_PID_GAIN

            pos = self.layer1.validate_command(pos, s)
            commands[s.valve_id] = ValveCommand(position_pct=pos, override=False)
            self.layer1.record_command(s.valve_id, pos / 100.0, t_seconds)

        return commands
