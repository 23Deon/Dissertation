from gridbot.sim.actions import Action, Heading


class Controller:
    _CW_ORDER = [Heading.N, Heading.E, Heading.S, Heading.W]

    def __init__(self):
        self._prev_pos = None
        self._prev_action = None
        self._priority = 0

    def act(self, observation) -> Action:
        pos = observation.position
        heading = observation.heading
        goal = observation.goal

        if pos[0] == goal[0] and pos[1] == goal[1]:
            self._prev_pos = pos
            self._prev_action = Action.WAIT
            return Action.WAIT

        if self._prev_action == Action.FORWARD and self._prev_pos is not None:
            if self._prev_pos == pos:
                self._priority = (self._priority + 1) % 4
            else:
                self._priority = 0

        dx = goal[0] - pos[0]
        dy = goal[1] - pos[1]

        ranked = self._ranked_headings(dx, dy)
        desired = ranked[self._priority]

        if heading == desired:
            action = Action.FORWARD
        else:
            action = self._turn_toward(heading, desired)

        self._prev_pos = pos
        self._prev_action = action
        return action

    def _ranked_headings(self, dx, dy):
        if dx >= 0:
            x_toward, x_away = Heading.E, Heading.W
        else:
            x_toward, x_away = Heading.W, Heading.E

        if dy >= 0:
            y_toward, y_away = Heading.S, Heading.N
        else:
            y_toward, y_away = Heading.N, Heading.S

        if abs(dx) >= abs(dy):
            return [x_toward, y_toward, y_away, x_away]
        return [y_toward, x_toward, x_away, y_away]

    def _turn_toward(self, current, desired):
        ci = self._CW_ORDER.index(current)
        di = self._CW_ORDER.index(desired)
        diff = (di - ci) % 4
        if diff == 1:
            return Action.TURN_RIGHT
        if diff == 3:
            return Action.TURN_LEFT
        return Action.TURN_RIGHT
