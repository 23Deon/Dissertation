import heapq

from gridbot.sim.actions import Action, Heading


class Controller:
    """Online A* grid controller.

    The controller builds a wall map from experience: every time a FORWARD
    action fails to change position, the edge it tried to cross is recorded
    as a wall (both sides — walls are symmetric between adjacent cells).
    On each tick it replans a shortest path from the current cell to the
    goal using A* over the known map, treating unknown edges as passable
    so the planner is optimistic about unexplored territory. It then
    executes one step of the plan: FORWARD if already facing the right way,
    otherwise a single turn toward it.

    Why this works where pure greedy fails:

    * Dead ends. Once every exit of a dead-end cell is known-walled,
      A* routes from the current cell back through the one remaining
      passable edge — the entrance — without needing to "remember" it
      specially.
    * Corridors / counterintuitive routes. A* considers all known edges
      globally, so it will commit to moving away from the goal when that
      is the only path the map supports.
    * No thrashing. Any path A* returns is consistent with every wall
      learned so far, so the robot cannot re-try an edge it has already
      confirmed blocked.

    Conventions: position and goal are (x, y) tuples. N = +y, E = +x.
    If the simulator uses screen coordinates (N = -y), swap the N/S
    branches in _next_pos.
    """

    _CW_ORDER = (Heading.N, Heading.E, Heading.S, Heading.W)
    _HEADING_RANK = dict(zip(_CW_ORDER, range(4)))
    _OPPOSITE = {
        Heading.N: Heading.S,
        Heading.S: Heading.N,
        Heading.E: Heading.W,
        Heading.W: Heading.E,
    }
    _MAX_NODES = 20000

    def __init__(self):
        self._last_pos = None
        self._last_action = None
        self._walls = set()

    def act(self, observation) -> Action:
        pos = tuple(observation.position)
        goal = tuple(observation.goal)
        heading = observation.heading

        if self._last_action == Action.FORWARD and self._last_pos == pos:
            self._walls.add((pos, heading))
            other = self._next_pos(pos, heading)
            self._walls.add((other, self._OPPOSITE[heading]))

        action = self._decide(pos, goal, heading)

        self._last_pos = pos
        self._last_action = action
        return action

    def _decide(self, pos, goal, heading):
        if pos == goal:
            return Action.WAIT

        plan = self._astar(pos, goal)
        if not plan:
            return Action.WAIT

        desired = plan[0]
        if heading == desired:
            return Action.FORWARD
        return self._turn_toward(heading, desired)

    def _astar(self, start, goal):
        def heuristic(p):
            return abs(p[0] - goal[0]) + abs(p[1] - goal[1])

        counter = 0
        open_heap = [(heuristic(start), 0, counter, start)]
        g_score = {start: 0}
        came_from = {start: (None, None)}

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
                tentative = cur_g + 1
                if tentative < g_score.get(nxt, 1 << 30):
                    g_score[nxt] = tentative
                    came_from[nxt] = (cell, h)
                    counter += 1
                    heapq.heappush(
                        open_heap,
                        (tentative + heuristic(nxt), tentative, counter, nxt),
                    )

        return None

    @staticmethod
    def _next_pos(pos, h):
        x, y = pos
        if h == Heading.N:
            return (x, y + 1)
        if h == Heading.S:
            return (x, y - 1)
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
