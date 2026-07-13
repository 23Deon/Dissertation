from heapq import heappush, heappop

from gridbot.sim.actions import Action, Heading


class Controller:
    """Grid robot controller with obstacle learning and cached A* planning.

    Coordinate convention (documented — flip if the sim disagrees):
      Heading.N -> (0, +1), E -> (+1, 0), S -> (0, -1), W -> (-1, 0).
    That is, positions are (x, y) with N increasing y. If the sim uses
    screen-style (row, col) with N decreasing row, negate the y components
    of the two affected entries in _DELTA; nothing else needs to change.

    Assumes static obstacles. Dynamic obstacles are not modeled — a cell,
    once learned as blocked, stays blocked for the life of this controller.
    """

    _DELTA = {
        Heading.N: (0, 1),
        Heading.E: (1, 0),
        Heading.S: (0, -1),
        Heading.W: (-1, 0),
    }
    _CW = [Heading.N, Heading.E, Heading.S, Heading.W]
    _SEARCH_LIMIT = 200_000

    def __init__(self):
        self._blocked = set()
        self._plan = []
        self._last_pos = None
        self._last_heading = None
        self._last_action = None

    def act(self, observation) -> Action:
        pos = tuple(observation.position)
        heading = observation.heading
        goal = tuple(observation.goal)

        if self._last_action == Action.FORWARD:
            if self._last_pos == pos and self._last_heading == heading:
                dx, dy = self._DELTA[heading]
                self._blocked.add((pos[0] + dx, pos[1] + dy))
            elif self._plan and pos == self._plan[0]:
                self._plan.pop(0)
            else:
                self._plan = []

        if pos == goal:
            return self._remember(pos, heading, Action.WAIT)

        if (
            not self._plan
            or self._plan[-1] != goal
            or any(cell in self._blocked for cell in self._plan)
        ):
            self._plan = self._astar(pos, goal)

        if self._plan:
            desired = self._heading_between(pos, self._plan[0])
            if desired == heading:
                action = Action.FORWARD
            elif desired is not None:
                action = self._rotate_toward(heading, desired)
            else:
                self._plan = []
                action = self._fallback(pos, heading)
        else:
            action = self._fallback(pos, heading)

        return self._remember(pos, heading, action)

    def _remember(self, pos, heading, action):
        self._last_pos, self._last_heading, self._last_action = pos, heading, action
        return action

    def _heading_between(self, src, dst):
        delta = (dst[0] - src[0], dst[1] - src[1])
        for h in self._CW:
            if self._DELTA[h] == delta:
                return h
        return None

    def _rotate_toward(self, current, desired):
        diff = (self._CW.index(desired) - self._CW.index(current)) % 4
        return Action.TURN_LEFT if diff == 3 else Action.TURN_RIGHT

    def _astar(self, start, goal):
        if start == goal:
            return []

        def h(cell):
            return abs(cell[0] - goal[0]) + abs(cell[1] - goal[1])

        came_from = {start: None}
        g_score = {start: 0}
        counter = 0
        open_heap = [(h(start), 0, counter, start)]
        expansions = 0

        while open_heap and expansions < self._SEARCH_LIMIT:
            _, g_cur, _, cur = heappop(open_heap)
            if g_cur > g_score[cur]:
                continue
            if cur == goal:
                path = []
                while cur != start:
                    path.append(cur)
                    cur = came_from[cur]
                path.reverse()
                return path
            expansions += 1
            for hd in self._CW:
                dx, dy = self._DELTA[hd]
                nxt = (cur[0] + dx, cur[1] + dy)
                if nxt in self._blocked:
                    continue
                ng = g_cur + 1
                if ng < g_score.get(nxt, float("inf")):
                    g_score[nxt] = ng
                    came_from[nxt] = cur
                    counter += 1
                    heappush(open_heap, (ng + h(nxt), ng, counter, nxt))
        return []

    def _fallback(self, pos, heading):
        dx, dy = self._DELTA[heading]
        if (pos[0] + dx, pos[1] + dy) not in self._blocked:
            return Action.FORWARD
        for hd in self._CW:
            ddx, ddy = self._DELTA[hd]
            if (pos[0] + ddx, pos[1] + ddy) not in self._blocked:
                return self._rotate_toward(heading, hd)
        return Action.WAIT
