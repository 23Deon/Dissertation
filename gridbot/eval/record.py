from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

from gridbot.sim.actions import Action, Heading
from gridbot.sim.types import Event

Position = Tuple[int, int]


@dataclass(frozen=True)
class TraceRecord:
    positions: List[Position]
    actions: List[Action]
    headings: List[Heading]


@dataclass(frozen=True)
class ScenarioRunRecord:
    event: Event
    steps: int
    trace: TraceRecord
