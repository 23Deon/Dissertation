from __future__ import annotations

from dataclasses import dataclass
from typing import Set, Tuple

Position = Tuple[int, int]


@dataclass(frozen=True)
class Scenario:
    width: int
    height: int
    obstacles: Set[Position]
    start: Position
    goal: Position
    max_steps: int = 200
