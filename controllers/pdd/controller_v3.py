''' PROMPT:
Write a Python controller for a grid robot.

Environment:

The controller must implement the class:

class Controller:
    def act(self, observation) -> Action

Observation contains:
- observation.position -> tuple[int, int]
- observation.heading -> Heading
- observation.goal -> tuple[int, int]

Available actions:

from gridbot.sim.actions import Action

Action.FORWARD
Action.TURN_LEFT
Action.TURN_RIGHT
Action.WAIT

Available headings:

from gridbot.sim.actions import Heading

Heading.N
Heading.E
Heading.S
Heading.W

Goal:
Move the robot toward the goal position.

Constraints:
- deterministic behaviour
- no randomness
- must return a valid Action
- class name must be Controller
- return only Python code'''

from gridbot.sim.actions import Action, Heading


class Controller:
    def act(self, observation) -> Action:
        x, y = observation.position
        gx, gy = observation.goal
        heading = observation.heading

        if (x, y) == (gx, gy):
            return Action.WAIT

        dx = gx - x
        dy = gy - y

        # Deterministic axis preference:
        # move horizontally first, then vertically.
        if dx != 0:
            desired_heading = Heading.E if dx > 0 else Heading.W
        else:
            desired_heading = Heading.S if dy > 0 else Heading.N

        if heading == desired_heading:
            return Action.FORWARD

        left_turn = {
            Heading.N: Heading.W,
            Heading.W: Heading.S,
            Heading.S: Heading.E,
            Heading.E: Heading.N,
        }

        right_turn = {
            Heading.N: Heading.E,
            Heading.E: Heading.S,
            Heading.S: Heading.W,
            Heading.W: Heading.N,
        }

        if left_turn[heading] == desired_heading:
            return Action.TURN_LEFT
        if right_turn[heading] == desired_heading:
            return Action.TURN_RIGHT

        # Opposite direction: choose a deterministic turn direction.
        return Action.TURN_LEFT