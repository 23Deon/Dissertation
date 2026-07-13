from gridbot.sim.actions import Action, Heading


class Controller:
    def act(self, observation) -> Action:
        x, y = observation.position
        gx, gy = observation.goal
        heading = observation.heading

        # Safe access to front_blocked
        front_blocked = getattr(observation, "front_blocked", False)

        # At goal
        if (x, y) == (gx, gy):
            return Action.WAIT

        # Compute preferred heading toward goal
        dx, dy = gx - x, gy - y
        if abs(dx) > abs(dy):
            primary = Heading.E if dx > 0 else Heading.W
            secondary = Heading.N if dy > 0 else Heading.S
        else:
            primary = Heading.N if dy > 0 else Heading.S
            secondary = Heading.E if dx > 0 else Heading.W

        # Try to move forward if facing primary direction
        if heading == primary and not front_blocked:
            return Action.FORWARD
        if heading == secondary and not front_blocked:
            return Action.FORWARD

        # Determine turn direction to face primary
        if self._turn_left(heading) == primary:
            return Action.TURN_LEFT
        if self._turn_right(heading) == primary:
            return Action.TURN_RIGHT

        # If blocked or opposite, try secondary
        if self._turn_left(heading) == secondary:
            return Action.TURN_LEFT
        if self._turn_right(heading) == secondary:
            return Action.TURN_RIGHT

        # If front blocked, rotate to explore
        if front_blocked:
            return Action.TURN_RIGHT

        # Otherwise, move forward
        return Action.FORWARD

    def _turn_left(self, h):
        return {Heading.N: Heading.W, Heading.W: Heading.S, Heading.S: Heading.E, Heading.E: Heading.N}[h]

    def _turn_right(self, h):
        return {Heading.N: Heading.E, Heading.E: Heading.S, Heading.S: Heading.W, Heading.W: Heading.N}[h]
