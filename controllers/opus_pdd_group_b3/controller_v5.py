import heapq

from gridbot.sim.actions import Action, Heading


class Controller:
    """Online A* over a learned wall map, with parallel-wall prediction.

    Coordinate convention:
        Heading.N -> (0, -1)
        Heading.S -> (0, +1)
        Heading.E -> (+1, 0)
        Heading.W -> (-1, 0)

    High-level approach:
    * Every tick, plan a path from current cell to goal cell with A* using
      Manhattan distance as the heuristic. Unknown edges are treated as
      passable.
    * A FORWARD that doesn't change position means the edge tried is a wall.
      Record it on both sides.
    * Nearby parallel known walls add a soft penalty to similar unknown edges,
      which biases the planner away from re-probing likely wall continuations.
    * Traversed edges are tracked as known-open and exempt from that penalty.
    * If A* finds no path, fall back to any non-walled direction to keep exploring.
    """

    _CW_ORDER = (Heading.N, Heading.E, Heading.S, Heading.W)
    _HEADING_RANK = dict(zip(_CW_ORDER, range(4)))
    _OPPOSITE = {
        Heading.N: Heading.S, Heading.S: Heading.N,
        Heading.E: Heading.W, Heading.W: Heading.E,
    }

    _MAX_NODES = 50000
    _PREDICT_RADIUS = 4
    _PREDICT_WEIGHT = 3.0

    def __init__(self):
        self._last_pos = None
        self._last_action = None
        self._walls = set()
        self._known_open = set()

    def act(self, observation) -> Action:
        pos = tuple(observation.position)
        goal = tuple(observation.goal)
        heading = observation.heading

        if self._last_action == Action.FORWARD and self._last_pos is not None:
            if self._last_pos == pos:
                self._walls.add((pos, heading))
                other = self._next_pos(pos, heading)
                self._walls.add((other, self._OPPOSITE[heading]))
            else:
                self._known_open.add((self._last_pos, heading))
                self._known_open.add((pos, self._OPPOSITE[heading]))

        action = self._decide(pos, goal, heading)

        self._last_pos = pos
        self._last_action = action
        return action

    def _decide(self, pos, goal, heading):
        if pos == goal:
            return Action.WAIT

        plan = self._astar(pos, goal)
        if plan:
            desired = plan[0]
            if heading == desired:
                return Action.FORWARD
            return self._turn_toward(heading, desired)

        for h in self._CW_ORDER:
            if (pos, h) not in self._walls:
                if heading == h:
                    return Action.FORWARD
                return self._turn_toward(heading, h)
        return Action.WAIT

    def _astar(self, start, goal):
        def heur(p):
            return abs(p[0] - goal[0]) + abs(p[1] - goal[1])

        counter = 0
        open_heap = [(heur(start), 0.0, counter, start)]
        came_from = {start: (None, None)}
        g_score = {start: 0.0}

        nodes = 0
        while open_heap:
            nodes += 1
            if nodes > self._MAX_NODES:
                return None

            _, _, _, cell = heapq.heappop(open_heap)
            if cell == goal:
                path = []
                c = cell
                while came_from[c][0] is not None:
                    prev, h_used = came_from[c]
                    path.append(h_used)
                    c = prev
                path.reverse()
                return path

            cur_g = g_score[cell]
            for h in self._CW_ORDER:
                if (cell, h) in self._walls:
                    continue
                nxt = self._next_pos(cell, h)
                cost = 1.0 + self._predict_penalty(cell, h)
                new_g = cur_g + cost
                if new_g < g_score.get(nxt, float("inf")):
                    g_score[nxt] = new_g
                    came_from[nxt] = (cell, h)
                    counter += 1
                    heapq.heappush(
                        open_heap,
                        (new_g + heur(nxt), new_g, counter, nxt),
                    )
        return None

    def _predict_penalty(self, cell, direction):
        if (cell, direction) in self._known_open:
            return 0.0

        x, y = cell
        penalty = 0.0
        if direction in (Heading.E, Heading.W):
            for offset in range(1, self._PREDICT_RADIUS + 1):
                for dy in (-offset, offset):
                    if ((x, y + dy), direction) in self._walls:
                        penalty += self._PREDICT_WEIGHT / offset
        else:
            for offset in range(1, self._PREDICT_RADIUS + 1):
                for dx in (-offset, offset):
                    if ((x + dx, y), direction) in self._walls:
                        penalty += self._PREDICT_WEIGHT / offset
        return penalty

    @staticmethod
    def _next_pos(pos, h):
        x, y = pos
        if h == Heading.N:
            return (x, y - 1)
        if h == Heading.S:
            return (x, y + 1)
        if h == Heading.E:
            return (x + 1, y)
        return (x - 1, y)

    def _turn_toward(self, current, desired):
        ci = self._HEADING_RANK[current]
        di = self._HEADING_RANK[desired]
        diff = (di - ci) % 4
        if diff == 3:
            return Action.TURN_LEFT
        return Action.TURN_RIGHT
