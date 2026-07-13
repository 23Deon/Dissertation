from gridbot.sim.actions import Action, Heading


class Controller:
    def act(self, observation) -> Action:
        x, y = observation.position
        goal_x, goal_y = observation.goal
        heading = observation.heading

        # Already at the goal.
        if (x, y) == (goal_x, goal_y):
            return Action.WAIT

        # Deterministic axis priority:
        # 1) reduce x-distance first
        # 2) then reduce y-distance
        if x < goal_x:
            desired = Heading.E
        elif x > goal_x:
            desired = Heading.W
        elif y < goal_y:
            desired = Heading.N
        else:
            desired = Heading.S

        if heading == desired:
            return Action.FORWARD

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

        if right_of[heading] == desired:
            return Action.TURN_RIGHT

        # Opposite direction: choose a fixed turn direction for determinism.
        return Action.TURN_RIGHT
