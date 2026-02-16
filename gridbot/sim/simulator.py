from dataclasses import dataclass
from typing import Tuple


Position = Tuple[int, int]


@dataclass
class RobotState:
    position: Position
    done: bool = False
    collided: bool = False
    steps: int = 0
