from collections import deque

from gridbot.sim.actions import Action, Heading


class Controller:
    """Grid robot controller: BFS over known-free cells, learn walls from failed forwards."""

    _DELTA = {
        Heading.E: (1, 0),
        Heading.W: (-1, 0),
        Heading.S: (0, 1),
        Heading.N: (0, -1),
    }
    _CW = [Heading.N, Heading.E, Heading.S, Heading.W]

    def __init__(self):
        self._blocked = set()
        self._path = []
        self._prev_pos = None
        self._prev_heading = None
        self._prev_action = None

    def act(self, observation) -> Action:
        pos = tuple(observation.position)
        heading = observation.heading
        goal = tuple(observation.goal)

        if self._prev_action == Action.FORWARD:
            if pos == self._prev_pos:
                dx, dy = self._DELTA[self._prev_heading]
                blocked_cell = (pos[0] + dx, pos[1] + dy)
                self._blocked.add(blocked_cell)
                if self._path and self._path[0] == blocked_cell:
                    self._path = []
            elif self._path and pos == self._path[0]:
                self._path.pop(0)
            else:
                self._path = []

        if pos == goal:
            return self._record(pos, heading, Action.WAIT)

        if self._path and (
            self._path[-1] != goal or any(c in self._blocked for c in self._path)
        ):
            self._path = []

        if not self._path:
            self._path = self._bfs(pos, goal)

        if not self._path:
            action = self._probe(pos, heading)
            return self._record(pos, heading, action)

        nxt = self._path[0]
        desired = self._heading_for_delta(nxt[0] - pos[0], nxt[1] - pos[1])
        if desired is None:
            self._path = []
            return self._record(pos, heading, self._probe(pos, heading))

        if heading == desired:
            action = Action.FORWARD
        else:
            action = self._rotate_toward(heading, desired)
        return self._record(pos, heading, action)

    def _bfs(self, start, goal):
        if start == goal:
            return []
        parent = {start: None}
        q = deque([start])
        while q:
            cur = q.popleft()
            if cur == goal:
                path = []
                node = cur
                while node != start:
                    path.append(node)
                    node = parent[node]
                path.reverse()
                return path
            neighbors = []
            for i, h in enumerate(self._CW):
                dx, dy = self._DELTA[h]
                n = (cur[0] + dx, cur[1] + dy)
                if n in self._blocked or n in parent:
                    continue
                key = (abs(n[0] - goal[0]) + abs(n[1] - goal[1]), i)
                neighbors.append((key, n))
            neighbors.sort()
            for _, n in neighbors:
                parent[n] = cur
                q.append(n)
        return []

    def _probe(self, pos, heading):
        dx, dy = self._DELTA[heading]
        ahead = (pos[0] + dx, pos[1] + dy)
        if ahead not in self._blocked:
            return Action.FORWARD
        for h in self._CW:
            ddx, ddy = self._DELTA[h]
            if (pos[0] + ddx, pos[1] + ddy) not in self._blocked:
                return self._rotate_toward(heading, h)
        return Action.WAIT

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
