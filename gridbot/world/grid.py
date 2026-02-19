from dataclasses import dataclass
from typing import Set, Tuple


Position = Tuple[int, int]


@dataclass(frozen=True)
class Grid:
    width: int
    height: int
    obstacles: Set[Position]
    start: Position
    goal: Position

    def in_bounds(self, pos: Position) -> bool:
        x, y = pos
        return 0 <= x < self.width and 0 <= y < self.height

    def is_obstacle(self, pos: Position) -> bool:
        return pos in self.obstacles

    def is_goal(self, pos: Position) -> bool:
        return pos == self.goal
    def is_valid_position(self, pos: Position) -> bool:
        return self.in_bounds(pos) and not self.is_obstacle(pos)