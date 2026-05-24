"""Main simulation loop. PRD §10 Phase 2 step 6.

Usage:
    uv run python -m sim.engine --scenario steady_state --mode belimo
"""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from typing import List

from sim.coil import Coil
from sim.controllers.belimo_baseline import BelimoController
from sim.io import write_jsonl
from sim.scenarios import Scenario
from sim.system import HydraulicSystem

SCENARIOS_DIR = Path(__file__).resolve().parent.parent / "data" / "scenarios"
RUNS_DIR = Path(__file__).resolve().parent.parent / "data" / "runs"


def run(scenario_name: str, mode: str, log_every: int = 300) -> Path:
    if mode != "belimo":
        raise ValueError(f"Phase 2 only supports mode=belimo, got {mode!r}")
    scenario = Scenario.load(SCENARIOS_DIR / f"{scenario_name}.json")
    system = HydraulicSystem.build_default()
    if not scenario.valve_ids:
        scenario.valve_ids = list(system.valves.keys())

    controller = BelimoController()
    total_energy_kwh = 0.0
    records: List[dict] = []
    states = system.tick(0)

    print(f"[engine] loaded scenario '{scenario.name}' "
          f"({scenario.duration_seconds // 60} min, {len(system.valves)} valves)")
    print(f"[engine] mode={mode}, tick=1s, total_ticks={scenario.duration_seconds}")

    dT_sum = 0.0
    dT_n = 0

    for t in range(scenario.duration_seconds):
        # Update coil load fractions from scenario (Coil is frozen → rebuild).
        for rec in system.valves.values():
            rec.coil = Coil(
                design_flow_gpm=rec.coil.design_flow_gpm,
                design_dT_C=rec.coil.design_dT_C,
                load_fraction=scenario.load_fraction(rec.valve_id, t),
            )

        commands = controller.step(states)
        system.set_positions(commands)
        states = system.tick(t)

        # Cache solver result to avoid 3 calls/tick.
        total_flow = system.solve_network()
        head = system.pump.head_kpa(total_flow)
        pump_kw = system.pump.power_kw(total_flow, head)
        total_energy_kwh += pump_kw * (1.0 / 3600.0)

        for st in states:
            dT_sum += st.dT_C
            dT_n += 1

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
                    "capacity_demand_kW": st.capacity_demand_kW,
                    "capacity_delivered_kW": st.capacity_delivered_kW,
                }
                for st in states
            ],
        })

        if t % log_every == 0:
            print(f"[engine] tick {t:4d}  pump_kw={pump_kw:.2f}  "
                  f"flow={total_flow:.0f} GPM  energy_so_far={total_energy_kwh:.3f} kWh")

    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    out = RUNS_DIR / f"{scenario_name}_{mode}_{ts}.jsonl"
    write_jsonl(out, records)

    mean_dT = dT_sum / dT_n if dT_n else 0.0
    print("[engine] complete")
    print(f"[summary] total_pump_energy = {total_energy_kwh:.2f} kWh")
    print(f"[summary] mean_dT           = {mean_dT:.2f} C")
    print(f"[summary] timeseries        = {out}")
    return out


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--scenario", default="steady_state")
    p.add_argument("--mode", default="belimo", choices=["belimo"])
    p.add_argument("--log-every", type=int, default=300)
    args = p.parse_args()
    run(args.scenario, args.mode, log_every=args.log_every)


if __name__ == "__main__":
    main()
