"""Main simulation loop. PRD §10 Phases 2 + 3.

Usage:
    uv run python -m sim.engine --scenario steady_state --mode belimo
    uv run python -m sim.engine --scenario steady_state --mode chillvalve
    uv run python -m sim.engine --scenario steady_state --mode compare
"""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

from sim.coil import Coil
from sim.controllers.belimo_baseline import BelimoController
from sim.controllers.chillvalve import ChillValveController
from sim.io import write_jsonl
from sim.scenarios import Scenario
from sim.system import HydraulicSystem

SCENARIOS_DIR = Path(__file__).resolve().parent.parent / "data" / "scenarios"
RUNS_DIR = Path(__file__).resolve().parent.parent / "data" / "runs"


def _summarize(records: List[dict]) -> Dict[str, float]:
    n = len(records)
    n_valves = len(records[0]["valves"])
    total_kwh = sum(r["pump_kw"] for r in records) / 3600.0
    mean_dT = sum(st["dT_C"] for r in records for st in r["valves"]) / (n * n_valves)
    l1_fires = sum(1 for r in records for st in r["valves"] if st.get("rule_fired"))
    leader_changes = sum(
        1
        for r0, r1 in zip(records, records[1:], strict=False)
        for s0, s1 in zip(r0["valves"], r1["valves"], strict=False)
        if s0.get("is_leader") != s1.get("is_leader")
    )
    return {
        "pump_kwh": total_kwh,
        "mean_dT": mean_dT,
        "layer1_fires": float(l1_fires),
        "leader_changes": float(leader_changes),
    }


def _run_single(
    scenario_name: str, mode: str, log_every: int
) -> Tuple[Path, Dict[str, float]]:
    scenario = Scenario.load(SCENARIOS_DIR / f"{scenario_name}.json")
    system = HydraulicSystem.build_default()
    if not scenario.valve_ids:
        scenario.valve_ids = list(system.valves.keys())

    controller: object
    if mode == "belimo":
        controller = BelimoController()
    elif mode == "chillvalve":
        controller = ChillValveController()
        flow_max = {
            vid: rec.coil.design_flow_gpm * 1.5 for vid, rec in system.valves.items()
        }
        controller.initialize(list(system.valves.keys()), flow_max, t_seconds=0.0)
    else:
        raise ValueError(f"unsupported mode: {mode!r}")

    records: List[dict] = []

    print(
        f"[engine] '{scenario.name}' mode={mode} ticks={scenario.duration_seconds}"
    )
    for t in range(scenario.duration_seconds):
        for rec in system.valves.values():
            rec.coil = Coil(
                design_flow_gpm=rec.coil.design_flow_gpm,
                design_dT_C=rec.coil.design_dT_C,
                load_fraction=scenario.load_fraction(rec.valve_id, t),
            )

        # 1. Observe current state.
        states = system.tick(t)

        # 2. Controller decides commands (mutates states with layer outputs).
        if mode == "belimo":
            commands = controller.step(states)  # type: ignore[attr-defined]
        else:
            commands = controller.step(states, t_seconds=float(t))  # type: ignore[attr-defined]

        # 3. Apply commands for next tick.
        system.set_positions(commands)

        # 4. Record what we observed + controller's decisions.
        total_flow = system.solve_network()
        head = system.pump.head_kpa(total_flow)
        pump_kw = system.pump.power_kw(total_flow, head)
        records.append({
            "tick": t,
            "pump_kw": pump_kw,
            "pump_head_kpa": head,
            "total_flow_gpm": total_flow,
            "valves": [
                {
                    "valve_id": st.valve_id,
                    "branch_id": st.branch_id,
                    "flow_gpm": st.flow_gpm,
                    "dT_C": st.dT_C,
                    "position_pct": st.position_pct,
                    "rule_fired": st.rule_fired,
                    "safety_override_active": st.safety_override_active,
                    "anomaly_detected": st.anomaly_detected,
                    "anomaly_confidence": st.anomaly_confidence,
                    "is_leader": st.is_leader,
                }
                for st in states
            ],
        })

        if t % log_every == 0:
            print(
                f"[engine] tick {t:4d}  pump_kw={pump_kw:.2f}  flow={total_flow:.0f} GPM"
            )

    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    out = RUNS_DIR / f"{scenario_name}_{mode}_{ts}.jsonl"
    write_jsonl(out, records)
    summary = _summarize(records)
    print(
        f"[summary] pump_kwh={summary['pump_kwh']:.2f}  "
        f"mean_dT={summary['mean_dT']:.2f}  "
        f"layer1_fires={int(summary['layer1_fires'])}  "
        f"leader_changes={int(summary['leader_changes'])}"
    )
    return out, summary


def run(scenario_name: str, mode: str, log_every: int = 300) -> Path:
    if mode in ("belimo", "chillvalve"):
        path, _ = _run_single(scenario_name, mode, log_every)
        return path
    if mode == "compare":
        _, belimo = _run_single(scenario_name, "belimo", log_every)
        _, cv = _run_single(scenario_name, "chillvalve", log_every)
        delta = cv["pump_kwh"] - belimo["pump_kwh"]
        pct = (delta / belimo["pump_kwh"]) * 100.0 if belimo["pump_kwh"] else 0.0
        print(
            f"[compare] belimo:     pump_kwh={belimo['pump_kwh']:.2f}  "
            f"mean_dT={belimo['mean_dT']:.2f}"
        )
        print(
            f"[compare] chillvalve: pump_kwh={cv['pump_kwh']:.2f}  "
            f"mean_dT={cv['mean_dT']:.2f}"
        )
        print(f"[compare] delta:      {delta:+.2f} kWh   ({pct:+.1f} %)")
        return Path("compare")
    raise ValueError(f"unsupported mode: {mode!r}")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--scenario", default="steady_state")
    p.add_argument(
        "--mode", default="belimo", choices=["belimo", "chillvalve", "compare"]
    )
    p.add_argument("--log-every", type=int, default=300)
    args = p.parse_args()
    run(args.scenario, args.mode, log_every=args.log_every)


if __name__ == "__main__":
    main()
