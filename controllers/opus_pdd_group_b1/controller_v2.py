from heapq import heappush, heappop

from gridbot.sim.actions import Action, Heading


class Controller:
    """Grid robot controller with learned obstacle avoidance.

    The observation has no sensor data, so obstacles can only be inferred:
    if the previous action was FORWARD and the position did not change,
    the edge we tried is blocked. We record that edge and replan.

    Each step runs A* from the current position to the goal, treating known
    blocked edges as obstacles and everything else as traversable. The first
    step of the resulting path tells us which direction to face; we FORWARD
    if already facing that way, otherwise turn toward it via the shorter
    rotation. In the open case A* reproduces the old greedy behavior; in
    blocked cases it routes around.

    Coordinate convention: N = +y, E = +x, S = -y, W = -x.

    Deterministic: fixed iteration order over headings, an insertion counter
    tiebreaks equal-f nodes in the A* frontier.
    """

    _DELTA = {
        Heading.N: (0, 1),
        Heading.E: (1, 0),
        Heading.S: (0, -1),
        Heading.W: (-1, 0),
    }
    _CLOCKWISE = [Heading.N, Heading.E, Heading.S, Heading.W]
    _MAX_NODES = 50_000

    def __init__(self) -> None:
        self._blocked_edges = set()
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
            self._blocked_edges.add((self._last_pos, self._last_heading))

        action = self._decide(pos, heading, goal)

        self._last_pos = pos
        self._last_heading = heading
        self._last_action = action
        return action

    def _decide(self, pos, heading: Heading, goal) -> Action:
        if pos == goal:
            return Action.WAIT

        next_cell = self._plan_first_step(pos, goal)
        if next_cell is None:
            return Action.WAIT

        desired = self._heading_between(pos, next_cell)
        if desired is None:
            return Action.WAIT

        if heading == desired:
            return Action.FORWARD
        return self._turn_toward(heading, desired)

    def _plan_first_step(self, start, goal):
        frontier = []
        counter = 0
        heappush(frontier, (self._manhattan(start, goal), 0, counter, start))

        came_from = {start: None}
        cost = {start: 0}

        expanded = 0
        while frontier and expanded < self._MAX_NODES:
            _, c, _, cur = heappop(frontier)
            expanded += 1

            if cur == goal:
                return self._first_step_from(came_from, start, goal)

            for h, (dx, dy) in self._DELTA.items():
                if (cur, h) in self._blocked_edges:
                    continue
                nxt = (cur[0] + dx, cur[1] + dy)
                new_cost = c + 1
                if nxt not in cost or new_cost < cost[nxt]:
                    cost[nxt] = new_cost
                    came_from[nxt] = cur
                    counter += 1
                    f = new_cost + self._manhattan(nxt, goal)
                    heappush(frontier, (f, new_cost, counter, nxt))

        return None

    @staticmethod
    def _first_step_from(came_from, start, goal):
        step = goal
        while True:
            parent = came_from.get(step)
            if parent == start:
                return step
            if parent is None:
                return None
            step = parent

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
