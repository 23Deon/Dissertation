'''Follow up:
Improve the controller so it rotates toward the goal before moving forward.
The behaviour must remain deterministic.
Return only the Python code.
''' 
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

        # Choose the primary direction that most directly reduces distance.
        # Deterministic tie-break: prefer horizontal movement over vertical.
        if abs(dx) >= abs(dy) and dx != 0:
            desired_heading = Heading.E if dx > 0 else Heading.W
        elif dy != 0:
            desired_heading = Heading.S if dy > 0 else Heading.N
        else:
            desired_heading = Heading.E if dx > 0 else Heading.W

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

        # Opposite direction: choose a deterministic rotation direction.
        return Action.TURN_LEFT