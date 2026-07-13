from heapq import heappush, heappop

from gridbot.sim.actions import Action, Heading


class Controller:
    """Grid robot controller.

    Coordinate convention (screen-space, as used by this project):
        Heading.E: (+1,  0)   increases x
        Heading.W: (-1,  0)   decreases x
        Heading.S: ( 0, +1)   increases y
        Heading.N: ( 0, -1)   decreases y

    Navigation strategy:
      - Plan a path with A*, treating known blocked edges as impassable
        and everything else as free. Cache the plan.
      - Each successful FORWARD advances through the cached plan; no
        replanning needed.
      - If FORWARD does not move us, that edge is a wall/obstacle/boundary.
        Record it in both directions, drop the plan, replan on the next step.

    A* uses forward tie-breaking (on tied f, prefer lower h) so expansion
    stays roughly linear in the path length on open grids, and a closed
    set so stale heap entries don't waste the node budget.

    Deterministic: fixed iteration order over headings; heap tuples carry
    an integer tiebreaker so raw cells are never compared.
    """

    _DELTA = {
        Heading.E: (1, 0),
        Heading.W: (-1, 0),
        Heading.S: (0, 1),
        Heading.N: (0, -1),
    }
    _OPPOSITE = {
        Heading.N: Heading.S,
        Heading.E: Heading.W,
        Heading.S: Heading.N,
        Heading.W: Heading.E,
    }
    _CLOCKWISE = [Heading.N, Heading.E, Heading.S, Heading.W]

    _MAX_NODES = 100_000

    def __init__(self) -> None:
        self._blocked = set()
        self._plan = []
        self._plan_goal = None
        self._last_pos = None
        self._last_heading = None
        self._last_action = None

    def act(self, observation) -> Action:
        pos = tuple(observation.position)
        goal = tuple(observation.goal)
        heading = observation.heading

        if (
            self._last_action == Action.FORWARD
            and self._last_pos is not None
            and pos == self._last_pos
        ):
            self._mark_edge_blocked(self._last_pos, self._last_heading)
            self._plan = []

        if self._plan_goal is not None and self._plan_goal != goal:
            self._plan = []

        while self._plan and self._plan[0] != pos:
            self._plan.pop(0)

        if not self._plan:
            path = self._astar(pos, goal)
            if path is not None:
                self._plan = path
                self._plan_goal = goal

        action = self._choose_action(pos, heading, goal)

        self._last_pos = pos
        self._last_heading = heading
        self._last_action = action
        return action

    def _choose_action(self, pos, heading: Heading, goal) -> Action:
        if pos == goal:
            return Action.WAIT
        if len(self._plan) < 2:
            return Action.WAIT

        next_cell = self._plan[1]
        desired = self._heading_between(pos, next_cell)
        if desired is None:
            return Action.WAIT

        if heading == desired:
            return Action.FORWARD
        return self._turn_toward(heading, desired)

    def _mark_edge_blocked(self, cell, heading: Heading) -> None:
        self._blocked.add((cell, heading))
        dx, dy = self._DELTA[heading]
        other_cell = (cell[0] + dx, cell[1] + dy)
        self._blocked.add((other_cell, self._OPPOSITE[heading]))

    def _astar(self, start, goal):
        if start == goal:
            return [start]

        frontier = []
        counter = 0
        h0 = self._manhattan(start, goal)
        heappush(frontier, (h0, h0, counter, start))

        came_from = {start: None}
        cost = {start: 0}
        closed = set()
        expanded = 0

        while frontier and expanded < self._MAX_NODES:
            _, _, _, cur = heappop(frontier)
            if cur in closed:
                continue
            closed.add(cur)
            expanded += 1

            if cur == goal:
                return self._reconstruct(came_from, goal)

            c = cost[cur]
            for h_dir in self._CLOCKWISE:
                if (cur, h_dir) in self._blocked:
                    continue
                dx, dy = self._DELTA[h_dir]
                nxt = (cur[0] + dx, cur[1] + dy)
                if nxt in closed:
                    continue
                new_cost = c + 1
                if nxt in cost and new_cost >= cost[nxt]:
                    continue
                cost[nxt] = new_cost
                came_from[nxt] = cur
                counter += 1
                h_val = self._manhattan(nxt, goal)
                heappush(frontier, (new_cost + h_val, h_val, counter, nxt))

        return None

    @staticmethod
    def _reconstruct(came_from, goal):
        path = []
        node = goal
        while node is not None:
            path.append(node)
            node = came_from.get(node)
        path.reverse()
        return path

    @staticmethod
    def _manhattan(a, b) -> int:
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def _heading_between(self, a, b):
        delta = (b[0] - a[0], b[1] - a[1])
        for h, hdelta in self._DELTA.items():
            if hdelta == delta:
                return h
        return None

    def _turn_toward(self, current: Heading, target: Heading) -> Action:
        i = self._CLOCKWISE.index(current)
        j = self._CLOCKWISE.index(target)
        cw = (j - i) % 4
        if cw == 1:
            return Action.TURN_RIGHT
        return Action.TURN_LEFT
