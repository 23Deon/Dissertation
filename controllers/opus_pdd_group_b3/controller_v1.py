from gridbot.sim.actions import Action, Heading


class Controller:
    """Greedy grid controller: face the goal, walk toward it, stop on arrival.

    Coordinate convention assumed: N = +y, E = +x, S = -y, W = -x.
    If the simulator uses screen coordinates (N = -y), swap the N/S branches
    in ``_desired_heading``.
    """

    _CW_ORDER = (Heading.N, Heading.E, Heading.S, Heading.W)

    def act(self, observation) -> Action:
        pos = observation.position
        goal = observation.goal
        heading = observation.heading

        dx = goal.x - pos.x
        dy = goal.y - pos.y

        if dx == 0 and dy == 0:
            return Action.WAIT

        desired = self._desired_heading(dx, dy, heading)
        if heading == desired:
            return Action.FORWARD
        return self._turn_toward(heading, desired)

    def _desired_heading(self, dx, dy, heading):
        if heading in (Heading.E, Heading.W) and dx != 0:
            return Heading.E if dx > 0 else Heading.W
        if heading in (Heading.N, Heading.S) and dy != 0:
            return Heading.N if dy > 0 else Heading.S

        if abs(dx) >= abs(dy) and dx != 0:
            return Heading.E if dx > 0 else Heading.W
        return Heading.N if dy > 0 else Heading.S

    def _turn_toward(self, current, desired):
        ci = self._CW_ORDER.index(current)
        di = self._CW_ORDER.index(desired)
        diff = (di - ci) % 4
        if diff == 3:
            return Action.TURN_LEFT
        return Action.TURN_RIGHT
