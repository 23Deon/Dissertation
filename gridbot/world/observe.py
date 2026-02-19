from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from gridbot.sim.actions import Heading

Position = Tuple[int, int]


@dataclass(frozen=True)
class Observation:
    position: Position
    heading: Heading
    goal: Position
