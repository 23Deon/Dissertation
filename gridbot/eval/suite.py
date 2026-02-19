from __future__ import annotations

from dataclasses import dataclass
from typing import List

from gridbot.controller import Controller
from gridbot.eval.harness import run_scenario
from gridbot.eval.scenario import Scenario
from gridbot.sim.types import Event


@dataclass(frozen=True)
class ScenarioResult:
    event: Event
    steps: int
    trace_len: int


@dataclass
class SuiteResult:
    results: List[ScenarioResult]

    @property
    def success_count(self) -> int:
        return sum(1 for r in self.results if r.event == Event.GOAL_REACHED)

    @property
    def collision_count(self) -> int:
        return sum(1 for r in self.results if r.event == Event.COLLISION)


def run_suite(scenarios: List[Scenario], controller: Controller) -> SuiteResult:
    results = []

    for scenario in scenarios:
        episode_result = run_scenario(scenario, controller)
        results.append(
            ScenarioResult(
                event=episode_result.event,
                steps=episode_result.steps,
                trace_len=episode_result.trace_len,
            )
        )

    return SuiteResult(results=results)
