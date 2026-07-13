from heapq import heappush, heappop

from gridbot.sim.actions import Action, Heading


class Controller:
    """Grid robot controller with learned obstacles, cached A* plans, and
    runtime calibration of the coordinate convention.

    Why calibration matters
    -----------------------
    Earlier versions hard-coded N = +y, E = +x. If the simulator uses a
    different convention (commonly N = -y when positions are row/col with
    row 0 at the top), that single sign flip makes the controller walk
    away from the goal on any vertical-heavy scenario -- which matches the
    observed failure pattern: open and short-detour scenarios pass because
    short horizontal moves happen to work; corridors and longer routes do
    not.

    This version learns the convention instead of assuming it. After each
    successful FORWARD we observe the actual (dx, dy) delta for the
    heading we were facing and derive the full delta map (N/S share a sign,
    E/W share a sign). Until both axes are calibrated we fall back to the
    default guess; the first successful move on each axis fixes any flip.

    Learned obstacles and plan caching are the same idea as before:
      - A bump (FORWARD that didn't move us) marks that edge blocked in
        both directions and invalidates the cached plan.
      - A* runs only when needed (no plan, goal changed, bump). Successful
        FORWARDs advance through the cached plan with no replanning.
      - A* uses forward tie-breaking and a closed set so heap traffic stays
        linear in the path length on open grids.

    Determinism
    -----------
    Fixed iteration order over headings; heap tuples include an integer
    tiebreaker so raw cells are never compared. Starting from the same
    observation history the controller produces the same action sequence.
    """

    _CLOCKWISE = [Heading.N, Heading.E, Heading.S, Heading.W]
    _OPPOSITE = {
        Heading.N: Heading.S,
        Heading.E: Heading.W,
        Heading.S: Heading.N,
        Heading.W: Heading.E,
    }
    _DEFAULT_DELTA = {
        Heading.N: (0, 1),
        Heading.E: (1, 0),
        Heading.S: (0, -1),
        Heading.W: (-1, 0),
    }
    _MAX_NODES = 100_000

    def __init__(self) -> None:
        self._delta = dict(self._DEFAULT_DELTA)
        self._x_axis_calibrated = False
        self._y_axis_calibrated = False

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

        if self._last_action == Action.FORWARD and self._last_pos is not None:
            dx = pos[0] - self._last_pos[0]
            dy = pos[1] - self._last_pos[1]
            if (dx, dy) == (0, 0):
                self._mark_edge_blocked(self._last_pos, self._last_heading)
                self._plan = []
            else:
                self._calibrate(self._last_heading, dx, dy)

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

    def _calibrate(self, heading: Heading, dx: int, dy: int) -> None:
        if heading in (Heading.E, Heading.W):
            if dx == 0:
                return
            expected = self._delta[heading][0]
            if expected != dx:
                self._delta[Heading.E] = (dx if heading == Heading.E else -dx, 0)
                self._delta[Heading.W] = (-self._delta[Heading.E][0], 0)
                self._blocked.clear()
                self._plan = []
                self._plan_goal = None
            self._x_axis_calibrated = True
        elif heading in (Heading.N, Heading.S):
            if dy == 0:
                return
            expected = self._delta[heading][1]
            if expected != dy:
                self._delta[Heading.N] = (0, dy if heading == Heading.N else -dy)
                self._delta[Heading.S] = (0, -self._delta[Heading.N][1])
                self._blocked.clear()
                self._plan = []
                self._plan_goal = None
            self._y_axis_calibrated = True

    def _mark_edge_blocked(self, cell, heading: Heading) -> None:
        self._blocked.add((cell, heading))
        dx, dy = self._delta[heading]
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
                dx, dy = self._delta[h_dir]
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
        dx, dy = b[0] - a[0], b[1] - a[1]
        for h, (hdx, hdy) in self._delta.items():
            if (hdx, hdy) == (dx, dy):
                return h
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
