from __future__ import annotations

from dataclasses import dataclass

from gridbot.eval.record import ScenarioRunRecord
from gridbot.sim.types import Event


@dataclass(frozen=True)
class DriftMetrics:
    regression: bool
    improvement: bool
    same: bool
    drift: bool
    new_collision: bool
    event_changed: bool
    steps_changed: bool
    step_delta: int
    trace_changed: bool
    path_changed: bool
    action_changed: bool
    heading_changed: bool
    change_type: str


def compare_runs(prev: ScenarioRunRecord, curr: ScenarioRunRecord) -> DriftMetrics:
    regression = (prev.event == Event.GOAL_REACHED) and (curr.event != Event.GOAL_REACHED)
    improvement = (prev.event != Event.GOAL_REACHED) and (curr.event == Event.GOAL_REACHED)

    new_collision = (prev.event != Event.COLLISION) and (curr.event == Event.COLLISION)

    event_changed = prev.event != curr.event
    step_delta = curr.steps - prev.steps
    steps_changed = step_delta != 0

    path_changed = prev.trace.positions != curr.trace.positions
    action_changed = prev.trace.actions != curr.trace.actions
    heading_changed = prev.trace.headings != curr.trace.headings
    trace_changed = path_changed or action_changed or heading_changed

    if regression:
        change_type = "regression"
    elif improvement:
        change_type = "improvement"
    elif prev.event == curr.event == Event.GOAL_REACHED and step_delta > 0:
        regression = True
        change_type = "regression"
    elif prev.event == curr.event == Event.GOAL_REACHED and step_delta < 0:
        improvement = True
        change_type = "improvement"
    elif not event_changed and not steps_changed and not trace_changed:
        change_type = "same"
    else:
        change_type = "drift"

    same = change_type == "same"
    drift = change_type == "drift"

    return DriftMetrics(
        regression=regression,
        improvement=improvement,
        same=same,
        drift=drift,
        new_collision=new_collision,
        event_changed=event_changed,
        steps_changed=steps_changed,
        step_delta=step_delta,
        trace_changed=trace_changed,
        path_changed=path_changed,
        action_changed=action_changed,
        heading_changed=heading_changed,
        change_type=change_type,
    )
