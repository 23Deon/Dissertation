from __future__ import annotations

from dataclasses import dataclass

from gridbot.eval.record import ScenarioRunRecord
from gridbot.sim.types import Event


@dataclass(frozen=True)
class DriftMetrics:
    regression: bool
    new_collision: bool
    event_changed: bool
    step_delta: int
    path_changed: bool
    action_changed: bool


def compare_runs(prev: ScenarioRunRecord, curr: ScenarioRunRecord) -> DriftMetrics:
    # Regression: previously reached goal, now doesn't
    regression = (prev.event == Event.GOAL_REACHED) and (curr.event != Event.GOAL_REACHED)

    # New collision: collision appears in current but not previous
    new_collision = (prev.event != Event.COLLISION) and (curr.event == Event.COLLISION)

    event_changed = prev.event != curr.event
    step_delta = curr.steps - prev.steps

    path_changed = prev.trace.positions != curr.trace.positions
    action_changed = prev.trace.actions != curr.trace.actions

    return DriftMetrics(
        regression=regression,
        new_collision=new_collision,
        event_changed=event_changed,
        step_delta=step_delta,
        path_changed=path_changed,
        action_changed=action_changed,
    )
