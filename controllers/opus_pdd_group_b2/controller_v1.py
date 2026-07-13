from gridbot.sim.actions import Action, Heading


class Controller:
    """Drives a grid robot toward its goal on an open grid.

    Assumes position and goal are (x, y) tuples where N increases y and E increases x.
    """

    _DELTA = {
        Heading.N: (0, 1),
        Heading.E: (1, 0),
        Heading.S: (0, -1),
        Heading.W: (-1, 0),
    }

    _CW_ORDER = [Heading.N, Heading.E, Heading.S, Heading.W]

    def act(self, observation) -> Action:
        px, py = observation.position
        gx, gy = observation.goal
        heading = observation.heading

        if (px, py) == (gx, gy):
            return Action.WAIT

        dx, dy = gx - px, gy - py
        hdx, hdy = self._DELTA[heading]

        if (hdx > 0 and dx > 0) or (hdx < 0 and dx < 0):
            return Action.FORWARD
        if (hdy > 0 and dy > 0) or (hdy < 0 and dy < 0):
            return Action.FORWARD

        if abs(dx) >= abs(dy):
            desired = Heading.E if dx > 0 else Heading.W
        else:
            desired = Heading.N if dy > 0 else Heading.S

        diff = (self._CW_ORDER.index(desired) - self._CW_ORDER.index(heading)) % 4
        return Action.TURN_LEFT if diff == 3 else Action.TURN_RIGHT
