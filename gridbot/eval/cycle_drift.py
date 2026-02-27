from __future__ import annotations

from dataclasses import dataclass

from gridbot.eval.cycle import CycleResult
from gridbot.eval.suite_drift import compare_suites


@dataclass(frozen=True)
class CycleDrift:
    from_cycle: int
    to_cycle: int
    regressions: int
    event_changes: int
    total_scenarios: int


def compare_cycles(prev: CycleResult, curr: CycleResult) -> CycleDrift:
    suite_drift = compare_suites(prev.records, curr.records)

    return CycleDrift(
        from_cycle=prev.cycle_id,
        to_cycle=curr.cycle_id,
        regressions=suite_drift.regressions,
        event_changes=suite_drift.event_changes,
        total_scenarios=suite_drift.total_scenarios,
    )