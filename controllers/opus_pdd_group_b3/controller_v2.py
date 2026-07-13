from gridbot.sim.actions import Action, Heading


class Controller:
    """Greedy grid controller with blocked-edge recovery.

    Strategy per tick:
      1. If at the goal, WAIT.
      2. Rank the four headings by: not-blocked, not-visited, then signed
         progress toward the goal (Manhattan-distance reduction). Lowest key
         wins.
      3. If the winning heading matches the current heading, FORWARD;
         otherwise turn toward it on the shortest arc.

    Blocked recovery:
      If a FORWARD action didn't change position, the (cell, heading) edge
      is recorded as blocked and never retried. This memory is persistent
      across revisits to the same cell, which prevents the oscillation you
      get from memoryless greedy search in front of concave obstacles.

    Visited-cell preference pushes the robot to explore new ground rather
    than retreating the way it came, which is what breaks 2-cell loops
    against a wall.

    Conventions: position and goal are (x, y) tuples. N = +y, E = +x.
    If your sim uses screen coordinates (N = -y), swap the N/S branches in
    _next_pos and _progress.
    """

    _CW_ORDER = (Heading.N, Heading.E, Heading.S, Heading.W)
    _HEADING_RANK = dict(zip(_CW_ORDER, range(4)))

    def __init__(self):
        self._last_pos = None
        self._last_action = None
        self._blocked_edges = set()
        self._visited = set()

    def act(self, observation) -> Action:
        pos = tuple(observation.position)
        goal = tuple(observation.goal)
        heading = observation.heading

        if self._last_action == Action.FORWARD and self._last_pos == pos:
            self._blocked_edges.add((pos, heading))

        self._visited.add(pos)

        action = self._choose_action(pos, goal, heading)

        self._last_pos = pos
        self._last_action = action
        return action

    def _choose_action(self, pos, goal, heading):
        dx = goal[0] - pos[0]
        dy = goal[1] - pos[1]

        if dx == 0 and dy == 0:
            return Action.WAIT

        ranked = sorted(
            self._CW_ORDER,
            key=lambda h: self._rank(h, pos, dx, dy),
        )
        best = ranked[0]

        if (pos, best) in self._blocked_edges:
            return Action.WAIT

        if heading == best:
            return Action.FORWARD
        return self._turn_toward(heading, best)

    def _rank(self, h, pos, dx, dy):
        is_blocked = (pos, h) in self._blocked_edges
        revisits = self._next_pos(pos, h) in self._visited
        distance_cost = -self._progress(h, dx, dy)
        return (is_blocked, revisits, distance_cost, self._HEADING_RANK[h])

    @staticmethod
    def _progress(h, dx, dy):
        if h == Heading.E:
            return dx
        if h == Heading.W:
            return -dx
        if h == Heading.N:
            return dy
        return -dy

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
