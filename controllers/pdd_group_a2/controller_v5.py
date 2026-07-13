from dataclasses import dataclass
from typing import Literal, Tuple

Action = Literal["forward", "left", "right", "wait"]
Heading = Literal["N", "E", "S", "W"]


@dataclass(frozen=True)
class RobotState:
    x: int
    y: int
    heading: Heading


@dataclass(frozen=True)
class Goal:
    x: int
    y: int


class GridRobotController:
    """
    A simple goal-seeking controller for a grid robot.

    Coordinate convention:
    - x increases to the east
    - y increases to the north

    Headings:
    - N = north
    - E = east
    - S = south
    - W = west
    """

    HEADINGS: Tuple[Heading, ...] = ("N", "E", "S", "W")
    VECTORS = {
        "N": (0, 1),
        "E": (1, 0),
        "S": (0, -1),
        "W": (-1, 0),
    }

    def choose_action(self, state: RobotState, goal: Goal) -> Action:
        """
        Return the next action that moves the robot toward the goal.
        """
        dx = goal.x - state.x
        dy = goal.y - state.y

        # Already at the goal
        if dx == 0 and dy == 0:
            return "wait"

        # Pick a desired heading.
        # This version prefers reducing x-distance first, then y-distance.
        desired_heading = self._desired_heading(dx, dy)

        if state.heading == desired_heading:
            return "forward"

        return self._turn_toward(state.heading, desired_heading)

    def _desired_heading(self, dx: int, dy: int) -> Heading:
        """
        Choose the heading that reduces distance to the goal.
        Preference:
        1. Move along x-axis if needed
        2. Otherwise move along y-axis
        """
        if dx > 0:
            return "E"
        if dx < 0:
            return "W"
        if dy > 0:
            return "N"
        return "S"

    def _turn_toward(self, current: Heading, target: Heading) -> Action:
        """
        Return left or right based on the shorter turn.
        If both are equally short, prefer right.
        """
        current_idx = self.HEADINGS.index(current)
        target_idx = self.HEADINGS.index(target)

        right_turns = (target_idx - current_idx) % 4
        left_turns = (current_idx - target_idx) % 4

        if right_turns <= left_turns:
            return "right"
        return "left"

    def apply_action(self, state: RobotState, action: Action) -> RobotState:
        """
        Simulate one action and return the new state.
        Useful for testing.
        """
        if action == "wait":
            return state

        if action == "left":
            idx = self.HEADINGS.index(state.heading)
            new_heading = self.HEADINGS[(idx - 1) % 4]
            return RobotState(state.x, state.y, new_heading)

        if action == "right":
            idx = self.HEADINGS.index(state.heading)
            new_heading = self.HEADINGS[(idx + 1) % 4]
            return RobotState(state.x, state.y, new_heading)

        if action == "forward":
            vx, vy = self.VECTORS[state.heading]
            return RobotState(state.x + vx, state.y + vy, state.heading)

        raise ValueError(f"Unknown action: {action}")


if __name__ == "__main__":
    controller = GridRobotController()

    state = RobotState(x=0, y=0, heading="N")
    goal = Goal(x=3, y=2)

    print(f"Start: {state}")
    print(f"Goal:  {goal}")

    for step in range(20):
        action = controller.choose_action(state, goal)
        print(f"Step {step + 1}: action={action}, state={state}")

        if action == "wait":
            print("Reached goal.")
            break

        state = controller.apply_action(state, action)
