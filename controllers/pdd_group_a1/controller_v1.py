from gridbot.sim.actions import Action, Heading


class Controller:
    def act(self, observation) -> Action:
        x, y = observation.position
        goal_x, goal_y = observation.goal
        heading = observation.heading

        dx = goal_x - x
        dy = goal_y - y

        # Already at the goal.
        if dx == 0 and dy == 0:
            return Action.WAIT

        # Deterministic axis preference:
        # 1. Resolve horizontal distance first
        # 2. Then resolve vertical distance
        if dx != 0:
            desired = Heading.E if dx > 0 else Heading.W
        else:
            desired = Heading.N if dy > 0 else Heading.S

        if heading == desired:
            return Action.FORWARD

        # Deterministic turning policy:
        # if a left turn reaches the desired heading, turn left;
        # otherwise turn right.
        left_of = {
            Heading.N: Heading.W,
            Heading.W: Heading.S,
            Heading.S: Heading.E,
            Heading.E: Heading.N,
        }

        right_of = {
            Heading.N: Heading.E,
            Heading.E: Heading.S,
            Heading.S: Heading.W,
            Heading.W: Heading.N,
        }

        if left_of[heading] == desired:
            return Action.TURN_LEFT

        return Action.TURN_RIGHT
