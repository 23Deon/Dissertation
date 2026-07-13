from gridbot.sim.actions import Action, Heading


class Controller:
    def __init__(self):
        self.visited = set()
        self.last_positions = []
        self.turn_bias = 1  # alternates to avoid loops

    def act(self, observation) -> Action:
        x, y = observation.position
        gx, gy = observation.goal
        heading = observation.heading

        front_blocked = getattr(observation, "front_blocked", False)

        # Track visits
        self.visited.add((x, y))
        self.last_positions.append((x, y))
        if len(self.last_positions) > 6:
            self.last_positions.pop(0)

        # If at goal
        if (x, y) == (gx, gy):
            return Action.WAIT

        # Detect oscillation (looping)
        if self.last_positions.count((x, y)) > 2:
            self.turn_bias *= -1  # flip strategy

        # Compute preferred directions (toward goal)
        dx = gx - x
        dy = gy - y

        preferred = []
        if abs(dx) > abs(dy):
            if dx != 0:
                preferred.append(Heading.E if dx > 0 else Heading.W)
            if dy != 0:
                preferred.append(Heading.N if dy > 0 else Heading.S)
        else:
            if dy != 0:
                preferred.append(Heading.N if dy > 0 else Heading.S)
            if dx != 0:
                preferred.append(Heading.E if dx > 0 else Heading.W)

        # Add remaining directions
        for h in [Heading.N, Heading.E, Heading.S, Heading.W]:
            if h not in preferred:
                preferred.append(h)

        # Try to act toward preferred direction safely
        for desired in preferred:
            if heading == desired:
                if not front_blocked:
                    return Action.FORWARD
                else:
                    # Obstacle ahead → choose turn based on bias
                    return Action.TURN_RIGHT if self.turn_bias > 0 else Action.TURN_LEFT
            else:
                # Turn toward desired
                if self._turn_left(heading) == desired:
                    return Action.TURN_LEFT
                if self._turn_right(heading) == desired:
                    return Action.TURN_RIGHT

        # If stuck, rotate to explore
        return Action.TURN_RIGHT if self.turn_bias > 0 else Action.TURN_LEFT

    def _turn_left(self, h):
        return {
            Heading.N: Heading.W,
            Heading.W: Heading.S,
            Heading.S: Heading.E,
            Heading.E: Heading.N,
        }[h]

    def _turn_right(self, h):
        return {
            Heading.N: Heading.E,
            Heading.E: Heading.S,
            Heading.S: Heading.W,
            Heading.W: Heading.N,
        }[h]
