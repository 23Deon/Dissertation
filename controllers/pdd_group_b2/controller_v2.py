from gridbot.sim.actions import Action, Heading


class Controller:
    def __init__(self):
        self.visited = set()

    def act(self, observation) -> Action:
        x, y = observation.position
        gx, gy = observation.goal
        heading = observation.heading

        self.visited.add((x, y))

        # Safe access for front_blocked (fixes previous runtime error)
        front_blocked = getattr(observation, "front_blocked", False)

        # If at goal, just wait
        if (x, y) == (gx, gy):
            return Action.WAIT

        # Determine preferred directions (prioritize reducing Manhattan distance)
        dx = gx - x
        dy = gy - y

        preferred_dirs = []
        if abs(dx) > abs(dy):
            preferred_dirs.append(Heading.E if dx > 0 else Heading.W)
            if dy != 0:
                preferred_dirs.append(Heading.N if dy > 0 else Heading.S)
        else:
            if dy != 0:
                preferred_dirs.append(Heading.N if dy > 0 else Heading.S)
            if dx != 0:
                preferred_dirs.append(Heading.E if dx > 0 else Heading.W)

        # Add fallback directions
        for h in [Heading.N, Heading.E, Heading.S, Heading.W]:
            if h not in preferred_dirs:
                preferred_dirs.append(h)

        # Try to move in preferred directions
        for desired in preferred_dirs:
            if heading == desired:
                if not front_blocked:
                    return Action.FORWARD
            else:
                # Turn toward desired
                if self._turn_left(heading) == desired:
                    return Action.TURN_LEFT
                elif self._turn_right(heading) == desired:
                    return Action.TURN_RIGHT
                else:
                    # If opposite direction, prefer two right turns
                    return Action.TURN_RIGHT

        # If all else fails (blocked), rotate to find new path
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
