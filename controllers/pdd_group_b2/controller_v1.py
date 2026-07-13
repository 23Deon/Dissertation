from gridbot.sim.actions import Action, Heading


class Controller:
    def act(self, observation) -> Action:
        x, y = observation.position
        gx, gy = observation.goal
        heading = observation.heading

        # Compute desired direction toward goal (greedy Manhattan move)
        dx = gx - x
        dy = gy - y

        # Determine preferred heading
        if abs(dx) > abs(dy):
            desired = Heading.E if dx > 0 else Heading.W
        else:
            desired = Heading.N if dy > 0 else Heading.S

        # If already facing desired direction
        if heading == desired:
            if not observation.front_blocked:
                return Action.FORWARD
            else:
                # Obstacle ahead → try turning right first
                return Action.TURN_RIGHT

        # Otherwise, turn toward desired direction
        if self._turn_left(heading) == desired:
            return Action.TURN_LEFT
        else:
            return Action.TURN_RIGHT

    def _turn_left(self, heading):
        return {
            Heading.N: Heading.W,
            Heading.W: Heading.S,
            Heading.S: Heading.E,
            Heading.E: Heading.N,
        }[heading]

    def _turn_right(self, heading):
        return {
            Heading.N: Heading.E,
            Heading.E: Heading.S,
            Heading.S: Heading.W,
            Heading.W: Heading.N,
        }[heading]
