from gridbot.sim.actions import Action, Heading


class Controller:
    _ORDER = (Heading.N, Heading.E, Heading.S, Heading.W)

    def __init__(self):
        self._prev_pos = None
        self._prev_action = None
        self._blocked = set()
        self._blocked_cell = None

    def act(self, observation) -> Action:
        pos = observation.position
        goal = observation.goal
        heading = observation.heading

        if pos == goal:
            return self._record(pos, Action.WAIT)

        if self._blocked_cell != pos:
            self._blocked = set()
            self._blocked_cell = pos

        if (
            self._prev_action == Action.FORWARD
            and self._prev_pos is not None
            and self._prev_pos == pos
        ):
            self._blocked.add(heading)

        dx = goal[0] - pos[0]
        dy = goal[1] - pos[1]

        preferred = []
        if abs(dx) >= abs(dy):
            if dx > 0:
                preferred.append(Heading.E)
            elif dx < 0:
                preferred.append(Heading.W)
            if dy > 0:
                preferred.append(Heading.S)
            elif dy < 0:
                preferred.append(Heading.N)
        else:
            if dy > 0:
                preferred.append(Heading.S)
            elif dy < 0:
                preferred.append(Heading.N)
            if dx > 0:
                preferred.append(Heading.E)
            elif dx < 0:
                preferred.append(Heading.W)

        for candidate in self._ORDER:
            if candidate not in preferred:
                preferred.append(candidate)

        target = None
        for candidate in preferred:
            if candidate not in self._blocked:
                target = candidate
                break

        if target is None:
            self._blocked = set()
            return self._record(pos, Action.WAIT)

        if heading == target:
            return self._record(pos, Action.FORWARD)

        return self._record(pos, self._rotate_toward(heading, target))

    def _rotate_toward(self, current, target) -> Action:
        ci = self._ORDER.index(current)
        ti = self._ORDER.index(target)
        diff = (ti - ci) % 4
        if diff == 1:
            return Action.TURN_RIGHT
        if diff == 3:
            return Action.TURN_LEFT
        return Action.TURN_RIGHT

    def _record(self, pos, action) -> Action:
        self._prev_pos = pos
        self._prev_action = action
        return action
