from collections import deque

from gridbot.sim.actions import Action, Heading


class Controller:
    """Grid robot controller that learns obstacles from failed moves.

    Each step, the controller runs a BFS from its current position to the
    goal over the set of cells it has not observed to be blocked. The
    first cell on that shortest path determines the next action (turn or
    forward). Whenever a FORWARD action leaves the robot in the same cell
    and with the same heading as before, the cell directly ahead must be
    an obstacle, so it is added to the blocked set and avoided thereafter.

    Assumes (x, y) coordinates with Heading.N increasing y and Heading.E
    increasing x. If the sim uses row/col with N decreasing row instead,
    flip the signs of the y components in _DELTA.
    """

    _DELTA = {
        Heading.N: (0, 1),
        Heading.E: (1, 0),
        Heading.S: (0, -1),
        Heading.W: (-1, 0),
    }
    _CW = [Heading.N, Heading.E, Heading.S, Heading.W]
    _SEARCH_LIMIT = 20000

    def __init__(self):
        self._blocked = set()
        self._last_position = None
        self._last_heading = None
        self._last_action = None

    def act(self, observation) -> Action:
        pos = tuple(observation.position)
        heading = observation.heading
        goal = tuple(observation.goal)

        if (
            self._last_action == Action.FORWARD
            and self._last_position == pos
            and self._last_heading == heading
        ):
            hdx, hdy = self._DELTA[heading]
            self._blocked.add((pos[0] + hdx, pos[1] + hdy))

        if pos == goal:
            action = Action.WAIT
        else:
            next_cell = self._plan(pos, goal)
            if next_cell is None:
                action = self._fallback(pos, heading)
            else:
                desired = self._heading_between(pos, next_cell)
                if heading == desired:
                    action = Action.FORWARD
                else:
                    action = self._rotation_toward(heading, desired)

        self._last_position = pos
        self._last_heading = heading
        self._last_action = action
        return action

    def _heading_between(self, src, dst):
        delta = (dst[0] - src[0], dst[1] - src[1])
        for h, d in self._DELTA.items():
            if d == delta:
                return h
        return None

    def _rotation_toward(self, current, desired):
        diff = (self._CW.index(desired) - self._CW.index(current)) % 4
        return Action.TURN_LEFT if diff == 3 else Action.TURN_RIGHT

    def _plan(self, start, goal):
        if start == goal:
            return None
        parent = {start: None}
        queue = deque([start])
        expansions = 0
        while queue and expansions < self._SEARCH_LIMIT:
            cur = queue.popleft()
            expansions += 1
            if cur == goal:
                node = cur
                while parent[node] != start:
                    node = parent[node]
                return node
            for h in self._CW:
                dx, dy = self._DELTA[h]
                nxt = (cur[0] + dx, cur[1] + dy)
                if nxt in parent or nxt in self._blocked:
                    continue
                parent[nxt] = cur
                queue.append(nxt)
        return None

    def _fallback(self, pos, heading):
        hdx, hdy = self._DELTA[heading]
        if (pos[0] + hdx, pos[1] + hdy) not in self._blocked:
            return Action.FORWARD
        for h in self._CW:
            dx, dy = self._DELTA[h]
            if (pos[0] + dx, pos[1] + dy) not in self._blocked:
                return self._rotation_toward(heading, h)
        return Action.WAIT
