from gridbot.sim.actions import Action, Heading


class Controller:
    _ORDER = (Heading.N, Heading.E, Heading.S, Heading.W)
    _DELTA = {
        Heading.N: (0, -1),
        Heading.E: (1, 0),
        Heading.S: (0, 1),
        Heading.W: (-1, 0),
    }

    def __init__(self):
        self._prev_pos = None
        self._prev_heading = None
        self._prev_action = None
        self._blocked_edges = set()
        self._visits = {}

    def act(self, observation) -> Action:
        pos = observation.position
        goal = observation.goal
        heading = observation.heading

        if pos == goal:
            return self._record(pos, heading, Action.WAIT)

        if (
            self._prev_action == Action.FORWARD
            and self._prev_pos is not None
            and self._prev_pos == pos
            and self._prev_heading is not None
        ):
            self._blocked_edges.add((pos, self._prev_heading))

        self._visits[pos] = self._visits.get(pos, 0) + 1

        target = self._choose_heading(pos, heading, goal)

        if target is None:
            return self._record(pos, heading, Action.TURN_RIGHT)

        if heading == target:
            return self._record(pos, heading, Action.FORWARD)

        return self._record(pos, heading, self._rotate_toward(heading, target))

    def _choose_heading(self, pos, heading, goal):
        dx = goal[0] - pos[0]
        dy = goal[1] - pos[1]

        goal_dirs = []
        if abs(dx) >= abs(dy):
            if dx > 0:
                goal_dirs.append(Heading.E)
            elif dx < 0:
                goal_dirs.append(Heading.W)
            if dy > 0:
                goal_dirs.append(Heading.S)
            elif dy < 0:
                goal_dirs.append(Heading.N)
        else:
            if dy > 0:
                goal_dirs.append(Heading.S)
            elif dy < 0:
                goal_dirs.append(Heading.N)
            if dx > 0:
                goal_dirs.append(Heading.E)
            elif dx < 0:
                goal_dirs.append(Heading.W)

        all_dirs = list(goal_dirs)
        for candidate in self._ORDER:
            if candidate not in all_dirs:
                all_dirs.append(candidate)

        candidates = []
        for candidate in all_dirs:
            if (pos, candidate) in self._blocked_edges:
                continue
            nxt = self._step(pos, candidate)
            visits = self._visits.get(nxt, 0)
            dist = self._manhattan(nxt, goal)
            in_goal_dir = 0 if candidate in goal_dirs else 1
            same_heading = 0 if candidate == heading else 1
            candidates.append((visits, in_goal_dir, dist, same_heading, candidate))

        if not candidates:
            return None

        candidates.sort(key=lambda item: (item[0], item[1], item[2], item[3]))
        return candidates[0][4]

    def _rotate_toward(self, current, target) -> Action:
        ci = self._ORDER.index(current)
        ti = self._ORDER.index(target)
        diff = (ti - ci) % 4
        if diff == 1:
            return Action.TURN_RIGHT
        if diff == 3:
            return Action.TURN_LEFT
        return Action.TURN_RIGHT

    def _step(self, pos, heading):
        dx, dy = self._DELTA[heading]
        return (pos[0] + dx, pos[1] + dy)

    @staticmethod
    def _manhattan(a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def _record(self, pos, heading, action) -> Action:
        self._prev_pos = pos
        self._prev_heading = heading
        self._prev_action = action
        return action
