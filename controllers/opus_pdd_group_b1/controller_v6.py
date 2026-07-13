from heapq import heappush, heappop

from gridbot.sim.actions import Action, Heading


class Controller:
    """Grid robot controller.

    Coordinate convention (screen-space):
        Heading.E: (+1,  0)   increases x
        Heading.W: (-1,  0)   decreases x
        Heading.S: ( 0, +1)   increases y
        Heading.N: ( 0, -1)   decreases y

    A bump -- FORWARD that leaves the robot in place -- means wall, obstacle,
    or boundary. That's the only obstacle information we ever get.
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

    _MAX_NODES = 200_000
    _H_WEIGHT = 1.2
    _BUMP_PENALTY = 4.0

    def __init__(self) -> None:
        self._blocked = set()
        self._bump_cells = set()
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
            self._bump_cells.add(self._last_pos)
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

        if len(self._plan) >= 2:
            next_cell = self._plan[1]
            desired = self._heading_between(pos, next_cell)
            if desired is not None:
                if heading == desired:
                    return Action.FORWARD
                return self._turn_toward(heading, desired)

        desired = self._exploration_heading(pos, heading)
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
        heappush(frontier, (h0 * self._H_WEIGHT, h0, 0, counter, start))

        came_from = {start: None}
        first_step = {start: None}
        cost = {start: 0.0}
        closed = set()
        expanded = 0

        while frontier and expanded < self._MAX_NODES:
            _, _, _, _, cur = heappop(frontier)
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

                step_cost = 1.0
                if cur in self._bump_cells or nxt in self._bump_cells:
                    step_cost += self._BUMP_PENALTY

                new_cost = c + step_cost
                if nxt in cost and new_cost >= cost[nxt]:
                    continue

                cost[nxt] = new_cost
                came_from[nxt] = cur
                if cur == start:
                    first_step[nxt] = nxt
                else:
                    first_step[nxt] = first_step[cur]

                counter += 1
                h_val = self._manhattan(nxt, goal)
                f = new_cost + self._H_WEIGHT * h_val
                fs = first_step[nxt]
                anti_rebump = 0 if (fs is not None and fs in self._bump_cells) else 1
                heappush(frontier, (f, h_val, -anti_rebump, counter, nxt))

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

    def _exploration_heading(self, pos, heading: Heading):
        best = None
        best_score = None
        for h_dir in self._CLOCKWISE:
            if (pos, h_dir) in self._blocked:
                continue
            dx, dy = self._DELTA[h_dir]
            nxt = (pos[0] + dx, pos[1] + dy)
            score = sum(1 for hh in self._CLOCKWISE if (nxt, hh) in self._blocked)
            key = (score, 0 if h_dir == heading else 1)
            if best_score is None or key < best_score:
                best_score = key
                best = h_dir
        return best

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
