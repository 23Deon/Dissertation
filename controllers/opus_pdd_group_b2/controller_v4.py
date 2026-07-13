from gridbot.sim.actions import Action, Heading


class Controller:
    """Grid robot controller using DFS exploration with goal-biased ordering.

    At each step, moves to the unexplored neighbor with smallest Manhattan
    distance to the goal, never re-entering cells already on the current
    path. When no fresh neighbor exists, backtracks to the parent and
    marks the current cell as a dead end. Each forward that fails adds a
    wall; each cell fully explored is never revisited. This trades
    path-optimality for robustness on mazes, corridors, and detours.

    Coordinate convention (documented — flip if the sim disagrees):
      Heading.N -> (0, +1), E -> (+1, 0), S -> (0, -1), W -> (-1, 0).
    If the sim uses screen-style (row, col) with N decreasing row, negate
    the y components of N and S in _DELTA. Nothing else changes.
    """

    _DELTA = {
        Heading.N: (0, 1),
        Heading.E: (1, 0),
        Heading.S: (0, -1),
        Heading.W: (-1, 0),
    }
    _CW = [Heading.N, Heading.E, Heading.S, Heading.W]

    def __init__(self):
        self._blocked = set()
        self._dead_end = set()
        self._path = []
        self._prev_pos = None
        self._prev_heading = None
        self._prev_action = None

    def act(self, observation) -> Action:
        pos = tuple(observation.position)
        heading = observation.heading
        goal = tuple(observation.goal)

        self._integrate(pos)

        if pos == goal:
            return self._record(pos, heading, Action.WAIT)

        target = self._pick_target(pos, goal)
        if target is None:
            return self._record(pos, heading, Action.WAIT)

        desired = self._heading_for_delta(target[0] - pos[0], target[1] - pos[1])
        if desired is None:
            return self._record(pos, heading, Action.WAIT)

        if heading == desired:
            action = Action.FORWARD
        else:
            action = self._rotate_toward(heading, desired)
        return self._record(pos, heading, action)

    def _integrate(self, pos):
        if self._prev_action != Action.FORWARD:
            if not self._path:
                self._path.append(pos)
            return

        if pos == self._prev_pos:
            dx, dy = self._DELTA[self._prev_heading]
            self._blocked.add((pos[0] + dx, pos[1] + dy))
            return

        if len(self._path) >= 2 and pos == self._path[-2]:
            self._dead_end.add(self._path.pop())
        elif pos not in self._path:
            self._path.append(pos)
        else:
            while self._path and self._path[-1] != pos:
                self._dead_end.add(self._path.pop())

    def _pick_target(self, pos, goal):
        candidates = []
        for i, h in enumerate(self._CW):
            dx, dy = self._DELTA[h]
            n = (pos[0] + dx, pos[1] + dy)
            if n in self._blocked or n in self._dead_end or n in self._path:
                continue
            dist = abs(goal[0] - n[0]) + abs(goal[1] - n[1])
            candidates.append((dist, i, n))

        if candidates:
            candidates.sort()
            return candidates[0][2]

        if len(self._path) >= 2:
            return self._path[-2]
        return None

    def _heading_for_delta(self, dx, dy):
        for h, d in self._DELTA.items():
            if d == (dx, dy):
                return h
        return None

    def _rotate_toward(self, current, desired):
        diff = (self._CW.index(desired) - self._CW.index(current)) % 4
        return Action.TURN_LEFT if diff == 3 else Action.TURN_RIGHT

    def _record(self, pos, heading, action):
        self._prev_pos = pos
        self._prev_heading = heading
        self._prev_action = action
        return action
