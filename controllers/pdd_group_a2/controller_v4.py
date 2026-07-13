from dataclasses import dataclass
from typing import Literal, Tuple

Heading = Literal["N", "E", "S", "W"]
Action = Literal["forward", "left", "right", "wait"]


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
    A simple greedy controller for a robot on a 2D grid.

    Strategy:
    - If already at the goal, wait.
    - Otherwise, choose the axis with the larger remaining distance.
    - Turn toward the desired direction.
    - Move forward when already facing that direction.
    """

    LEFT_TURN = {
        "N": "W",
        "W": "S",
        "S": "E",
        "E": "N",
    }

    RIGHT_TURN = {
        "N": "E",
        "E": "S",
        "S": "W",
        "W": "N",
    }

    FORWARD_DELTAS = {
        "N": (0, 1),
        "E": (1, 0),
        "S": (0, -1),
        "W": (-1, 0),
    }

    HEADINGS = ["N", "E", "S", "W"]

    def choose_action(self, state: RobotState, goal: Goal) -> Action:
        """
        Return the next action for the robot.
        """
        if (state.x, state.y) == (goal.x, goal.y):
            return "wait"

        desired_heading = self._desired_heading(state, goal)

        if state.heading == desired_heading:
            return "forward"

        return self._turn_toward(state.heading, desired_heading)

    def _desired_heading(self, state: RobotState, goal: Goal) -> Heading:
        """
        Pick the direction that most directly reduces distance to the goal.
        """
        dx = goal.x - state.x
        dy = goal.y - state.y

        # Prefer the axis with larger absolute error.
        if abs(dx) >= abs(dy):
            if dx > 0:
                return "E"
            if dx < 0:
                return "W"
            if dy > 0:
                return "N"
            return "S"
        else:
            if dy > 0:
                return "N"
            if dy < 0:
                return "S"
            if dx > 0:
                return "E"
            return "W"

    def _turn_toward(self, current: Heading, target: Heading) -> Action:
        """
        Choose left or right turn to reach target with the fewest turns.
        """
        current_idx = self.HEADINGS.index(current)
        target_idx = self.HEADINGS.index(target)

        right_steps = (target_idx - current_idx) % 4
        left_steps = (current_idx - target_idx) % 4

        if right_steps < left_steps:
            return "right"
        return "left"

    def apply_action(self, state: RobotState, action: Action) -> RobotState:
        """
        Simulate one action and return the next state.
        Useful for testing.
        """
        if action == "wait":
            return state

        if action == "left":
            return RobotState(state.x, state.y, self.LEFT_TURN[state.heading])

        if action == "right":
            return RobotState(state.x, state.y, self.RIGHT_TURN[state.heading])

        if action == "forward":
            dx, dy = self.FORWARD_DELTAS[state.heading]
            return RobotState(state.x + dx, state.y + dy, state.heading)

        raise ValueError(f"Unknown action: {action}")


def run_until_goal(
    start: RobotState,
    goal: Goal,
    max_steps: int = 100
) -> Tuple[RobotState, list[Action]]:
    """
    Simulate the controller until the robot reaches the goal or max_steps is hit.
    """
    controller = GridRobotController()
    state = start
    actions: list[Action] = []

    for _ in range(max_steps):
        action = controller.choose_action(state, goal)
        actions.append(action)

        if action == "wait":
            break

        state = controller.apply_action(state, action)

        if (state.x, state.y) == (goal.x, goal.y):
            actions.append("wait")
            break

    return state, actions


if __name__ == "__main__":
    start = RobotState(x=0, y=0, heading="N")
    goal = Goal(x=3, y=2)

    final_state, actions = run_until_goal(start, goal)

    print("Start:", start)
    print("Goal:", goal)
    print("Actions:", actions)
    print("Final state:", final_state)
