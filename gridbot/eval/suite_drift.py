from __future__ import annotations

from dataclasses import dataclass
from typing import List

from gridbot.eval.drift import compare_runs, DriftMetrics
from gridbot.eval.record import ScenarioRunRecord


@dataclass(frozen=True)
class SuiteDriftResult:
    regressions: int
    new_collisions: int
    event_changes: int
    total_scenarios: int


def compare_suites(
    previous: List[ScenarioRunRecord],
    current: List[ScenarioRunRecord],
) -> SuiteDriftResult:
    assert len(previous) == len(current), "Suite sizes must match"

    regressions = 0
    new_collisions = 0
    event_changes = 0

    for prev, curr in zip(previous, current):
        drift: DriftMetrics = compare_runs(prev, curr)

        if drift.regression:
            regressions += 1

        if drift.new_collision:
            new_collisions += 1

        if drift.event_changed:
            event_changes += 1

    return SuiteDriftResult(
        regressions=regressions,
        new_collisions=new_collisions,
        event_changes=event_changes,
        total_scenarios=len(previous),
    )
