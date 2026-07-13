from gridbot.sim.actions import Action, Heading


class Controller:
    def act(self, observation) -> Action:
        x, y = observation.position
        gx, gy = observation.goal
        heading = observation.heading

        # At goal
        if (x, y) == (gx, gy):
            return Action.WAIT

        # Compute deltas
        dx, dy = gx - x, gy - y

        # Decisive deterministic axis policy:
        # Prioritize moving along the axis with larger distance, fallback to secondary
        if abs(dx) >= abs(dy):
            primary = Heading.E if dx > 0 else Heading.W
            secondary = Heading.N if dy > 0 else Heading.S
        else:
            primary = Heading.N if dy > 0 else Heading.S
            secondary = Heading.E if dx > 0 else Heading.W

        # Move along primary axis
        if heading == primary:
            return Action.FORWARD
        # Turn toward primary axis
        if self._turn_left(heading) == primary:
            return Action.TURN_LEFT
        if self._turn_right(heading) == primary:
            return Action.TURN_RIGHT

        # Move along secondary axis if primary not yet reached
        if heading == secondary:
            return Action.FORWARD
        if self._turn_left(heading) == secondary:
            return Action.TURN_LEFT
        if self._turn_right(heading) == secondary:
            return Action.TURN_RIGHT

        # Fallback: rotate clockwise
        return Action.TURN_RIGHT

    def _turn_left(self, h):
        return {Heading.N: Heading.W, Heading.W: Heading.S, Heading.S: Heading.E, Heading.E: Heading.N}[h]

    def _turn_right(self, h):
        return {Heading.N: Heading.E, Heading.E: Heading.S, Heading.S: Heading.W, Heading.W: Heading.N}[h]
