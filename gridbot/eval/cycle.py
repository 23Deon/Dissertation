from __future__ import annotations

from dataclasses import dataclass
from typing import List

from gridbot.controller import Controller
from gridbot.eval.record import ScenarioRunRecord
from gridbot.eval.scenario import Scenario
from gridbot.eval.harness import run_episode_record
from gridbot.sim.simulator import Simulator
from gridbot.world.grid import Grid


@dataclass
class CycleResult:
    cycle_id: int
    records: List[ScenarioRunRecord]


def run_cycle(
    cycle_id: int,
    scenarios: List[Scenario],
    controller: Controller,
) -> CycleResult:

    records = []

    for scenario in scenarios:
        grid = Grid(
            width=scenario.width,
            height=scenario.height,
            obstacles=scenario.obstacles,
            start=scenario.start,
            goal=scenario.goal,
        )

        sim = Simulator(grid, max_steps=scenario.max_steps)

        record = run_episode_record(sim, controller)
        records.append(record)

    return CycleResult(cycle_id=cycle_id, records=records)