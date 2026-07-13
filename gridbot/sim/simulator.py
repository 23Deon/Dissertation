from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from gridbot.sim.actions import Action, Heading, forward_delta, turn_left, turn_right
from gridbot.sim.trace import Trace, TraceStep
from gridbot.sim.types import Event
from gridbot.world.grid import Grid

Position = Tuple[int, int]


@dataclass
class RobotState:
    position: Position
    heading: Heading
    t: int = 0
    done: bool = False
    last_event: Event = Event.OK


class Simulator:
    def __init__(self, grid: Grid, max_steps: int = 200, start_heading: Heading = Heading.E):
        self.grid = grid
        self.max_steps = max_steps
        self.state = RobotState(position=grid.start, heading=start_heading)
        self.trace = Trace(steps=[])

    def _log(self, action: Action, event: Event) -> None:
        s = self.state
        self.trace.append(
            TraceStep(
                t=s.t,
                position=s.position,
                heading=s.heading,
                action=action,
                event=event,
            )
        )

    def step(self, action: Action) -> Event:
        s = self.state
        if s.done:
            return s.last_event

        s.t += 1  # advance time deterministically

        if action == Action.WAIT:
            s.last_event = Event.OK
            if s.t >= self.max_steps:
                s.done = True
                s.last_event = Event.TIMEOUT
            self._log(action, s.last_event)
            return s.last_event

        if action == Action.TURN_LEFT:
            s.heading = turn_left(s.heading)
            s.last_event = Event.OK
            if s.t >= self.max_steps:
                s.done = True
                s.last_event = Event.TIMEOUT
            self._log(action, s.last_event)
            return s.last_event

        if action == Action.TURN_RIGHT:
            s.heading = turn_right(s.heading)
            s.last_event = Event.OK
            if s.t >= self.max_steps:
                s.done = True
                s.last_event = Event.TIMEOUT
            self._log(action, s.last_event)
            return s.last_event

        # FORWARD
        dx, dy = forward_delta(s.heading)
        new_pos = (s.position[0] + dx, s.position[1] + dy)

        if (not self.grid.in_bounds(new_pos)) or self.grid.is_obstacle(new_pos):
            # A blocked move is non-fatal: the robot stays in place, spends a step,
            # and can try a different deterministic action next turn.
            s.last_event = Event.OK
            if s.t >= self.max_steps:
                s.done = True
                s.last_event = Event.TIMEOUT
            self._log(action, s.last_event)
            return s.last_event

        s.position = new_pos

        if self.grid.is_goal(new_pos):
            s.done = True
            s.last_event = Event.GOAL_REACHED
            self._log(action, s.last_event)
            return s.last_event

        s.last_event = Event.OK
        if s.t >= self.max_steps:
            s.done = True
            s.last_event = Event.TIMEOUT
        self._log(action, s.last_event)
        return s.last_event
