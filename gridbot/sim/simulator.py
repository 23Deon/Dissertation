from dataclasses import dataclass
from typing import Tuple
from gridbot.world.grid import Grid

Position = Tuple[int, int]


@dataclass
class RobotState:
    position: Position
    done: bool = False
    collided: bool = False
    steps: int = 0

class Simulator:
    def __init__(self, grid: Grid):
        self.grid = grid
        self.state = RobotState(position=grid.start)

    def step(self, move: Tuple[int, int]) -> None:
        if self.state.done:
            return

        x, y = self.state.position
        dx, dy = move
        new_pos = (x + dx, y + dy)

        self.state.steps += 1

        if not self.grid.in_bounds(new_pos) or self.grid.is_obstacle(new_pos):
            self.state.collided = True
            self.state.done = True
            return

        self.state.position = new_pos

        if self.grid.is_goal(new_pos):
            self.state.done = True