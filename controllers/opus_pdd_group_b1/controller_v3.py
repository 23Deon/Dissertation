from heapq import heappush, heappop

from gridbot.sim.actions import Action, Heading


class Controller:
    """Grid robot controller with learned obstacles and cached plans.

    Strategy:
      - Plan a path from current position to the goal with A*, treating known
        blocked edges as obstacles and everything else as free.
      - Cache the plan. Each successful FORWARD advances us one cell through
        the plan; no replanning needed.
      - A bump (FORWARD that didn't move us) teaches us an edge is blocked,
        invalidates the plan, and triggers a replan on the next step.

    Why this is faster than replanning every step:
      - A* runs once per bump, not once per action.
      - A* uses forward tie-breaking (prefer lower h on tied f), which turns
        the typical open-grid expansion from O(d^2) into roughly O(d).
      - Closed set + lazy duplicate rejection keeps the heap honest so stale
        entries do not eat the expansion budget.

    When we bump we record BOTH directions of the edge: the wall between A
    and B blocks (A, toward B) and (B, toward A) equally, so later arrivals
    from the other side don't need to re-bump to learn it.

    Coordinate convention: N = +y, E = +x, S = -y, W = -x.
    Determinism: fixed iteration order over headings; heap tuples always
    include an integer tiebreaker so the heap never compares raw cells.
    """

    _DELTA = {
        Heading.N: (0, 1),
        Heading.E: (1, 0),
        Heading.S: (0, -1),
        Heading.W: (-1, 0),
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
        pos = self._as_tuple(observation.position)
        goal = self._as_tuple(observation.goal)
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
            for h_dir, (dx, dy) in self._DELTA.items():
                if (cur, h_dir) in self._blocked:
                    continue
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
                f = new_cost + h_val
                heappush(frontier, (f, h_val, counter, nxt))

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

    @staticmethod
    def _heading_between(a, b):
        dx, dy = b[0] - a[0], b[1] - a[1]
        if (dx, dy) == (1, 0):
            return Heading.E
        if (dx, dy) == (-1, 0):
            return Heading.W
        if (dx, dy) == (0, 1):
            return Heading.N
        if (dx, dy) == (0, -1):
            return Heading.S
        return None

    def _turn_toward(self, current: Heading, target: Heading) -> Action:
        i = self._CLOCKWISE.index(current)
        j = self._CLOCKWISE.index(target)
        cw = (j - i) % 4
        if cw == 1:
            return Action.TURN_RIGHT
        return Action.TURN_LEFT

    @staticmethod
    def _as_tuple(p):
        if hasattr(p, "x") and hasattr(p, "y"):
            return (p.x, p.y)
        return tuple(p)
