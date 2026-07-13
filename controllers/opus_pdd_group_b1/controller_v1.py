from gridbot.sim.actions import Action, Heading


class Controller:
    """Greedy grid robot controller that navigates toward a goal position.

    Strategy:
      1. If already at the goal, wait.
      2. Otherwise pick a heading that reduces distance to the goal.
         If the current heading already helps, keep it (avoid wasted turns).
         Otherwise prefer the axis with the greater remaining distance.
      3. If already facing the desired heading, move forward.
         Otherwise turn toward it via the shorter rotation.

    Coordinate convention: N increases y, E increases x, S decreases y, W decreases x.
    """

    _CLOCKWISE = [Heading.N, Heading.E, Heading.S, Heading.W]

    def act(self, observation) -> Action:
        px, py = observation.position
        gx, gy = observation.goal
        heading = observation.heading

        if (px, py) == (gx, gy):
            return Action.WAIT

        dx = gx - px
        dy = gy - py

        desired = self._choose_heading(dx, dy, heading)

        if heading == desired:
            return Action.FORWARD

        return self._turn_toward(heading, desired)

    def _choose_heading(self, dx: int, dy: int, current: Heading) -> Heading:
        progress = []
        if dx > 0:
            progress.append(Heading.E)
        elif dx < 0:
            progress.append(Heading.W)
        if dy > 0:
            progress.append(Heading.N)
        elif dy < 0:
            progress.append(Heading.S)

        if current in progress:
            return current

        if abs(dx) >= abs(dy):
            return Heading.E if dx > 0 else Heading.W
        return Heading.N if dy > 0 else Heading.S

    def _turn_toward(self, current: Heading, target: Heading) -> Action:
        i = self._CLOCKWISE.index(current)
        j = self._CLOCKWISE.index(target)
        cw_steps = (j - i) % 4

        if cw_steps == 1:
            return Action.TURN_RIGHT
        return Action.TURN_LEFT
