from gridbot.sim.actions import Action, Heading


class Controller:
    def __init__(self):
        # Track last few positions to avoid loops
        self.last_positions = []

    def act(self, observation) -> Action:
        x, y = observation.position
        gx, gy = observation.goal
        heading = observation.heading

        # Fix: safe access to front_blocked
        front_blocked = getattr(observation, "front_blocked", False)

        # Track last positions
        self.last_positions.append((x, y))
        if len(self.last_positions) > 6:
            self.last_positions.pop(0)

        # At goal
        if (x, y) == (gx, gy):
            return Action.WAIT

        # Compute preferred headings toward goal (greedy Manhattan)
        dx, dy = gx - x, gy - y
        preferred = []
        if abs(dx) >= abs(dy):
            if dx != 0:
                preferred.append(Heading.E if dx > 0 else Heading.W)
            if dy != 0:
                preferred.append(Heading.N if dy > 0 else Heading.S)
        else:
            if dy != 0:
                preferred.append(Heading.N if dy > 0 else Heading.S)
            if dx != 0:
                preferred.append(Heading.E if dx > 0 else Heading.W)

        # Fallback headings
        for h in [Heading.N, Heading.E, Heading.S, Heading.W]:
            if h not in preferred:
                preferred.append(h)

        # Avoid going back to recent positions if possible
        for desired in preferred:
            if heading == desired:
                if not front_blocked:
                    next_pos = self._next_position((x, y), heading)
                    if next_pos not in self.last_positions[-3:]:
                        return Action.FORWARD
                    # Otherwise, try turning instead
                    return Action.TURN_RIGHT
                else:
                    return Action.TURN_RIGHT
            else:
                if self._turn_left(heading) == desired:
                    return Action.TURN_LEFT
                if self._turn_right(heading) == desired:
                    return Action.TURN_RIGHT

        # Fallback: rotate to explore
        return Action.TURN_RIGHT

    def _turn_left(self, h):
        return {Heading.N: Heading.W, Heading.W: Heading.S, Heading.S: Heading.E, Heading.E: Heading.N}[h]

    def _turn_right(self, h):
        return {Heading.N: Heading.E, Heading.E: Heading.S, Heading.S: Heading.W, Heading.W: Heading.N}[h]

    def _next_position(self, pos, heading):
        x, y = pos
        if heading == Heading.N:
            return (x, y + 1)
        if heading == Heading.S:
            return (x, y - 1)
        if heading == Heading.E:
            return (x + 1, y)
        if heading == Heading.W:
            return (x - 1, y)
        return (x, y)
