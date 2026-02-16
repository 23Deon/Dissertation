from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

from gridbot.sim.actions import Action, Heading
from gridbot.sim.simulator import Event

Position = Tuple[int, int]


@dataclass(frozen=True)
class TraceStep:
    t: int
    position: Position
    heading: Heading
    action: Action
    event: Event


@dataclass
class Trace:
    steps: List[TraceStep]

    def append(self, step: TraceStep) -> None:
        self.steps.append(step)
