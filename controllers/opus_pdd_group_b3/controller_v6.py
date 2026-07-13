import heapq

from gridbot.sim.actions import Action, Heading


class Controller:
    """Online heading-aware A* with wall learning and parallel-wall prediction."""

    _CW_ORDER = (Heading.N, Heading.E, Heading.S, Heading.W)
    _HEADING_RANK = dict(zip(_CW_ORDER, range(4)))
    _OPPOSITE = {
        Heading.N: Heading.S, Heading.S: Heading.N,
        Heading.E: Heading.W, Heading.W: Heading.E,
    }

    _MAX_NODES = 200000
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

        action = self._plan(pos, heading, goal)
        if action is not None:
            return action

        for h in self._CW_ORDER:
            if (pos, h) not in self._walls:
                if heading == h:
                    return Action.FORWARD
                return self._turn_toward(heading, h)
        return Action.WAIT

    def _plan(self, start_cell, start_heading, goal_cell):
        start_state = (start_cell, start_heading)

        def heur(cell):
            return abs(cell[0] - goal_cell[0]) + abs(cell[1] - goal_cell[1])

        counter = 0
        open_heap = [(heur(start_cell), 0.0, counter, start_state)]
        came_from = {start_state: (None, None)}
        g_score = {start_state: 0.0}

        nodes = 0
        while open_heap:
            nodes += 1
            if nodes > self._MAX_NODES:
                return None

            _, _, _, state = heapq.heappop(open_heap)
            cell, hd = state

            if cell == goal_cell:
                cur = state
                first_action = None
                while came_from[cur][0] is not None:
                    prev_state, action = came_from[cur]
                    first_action = action
                    cur = prev_state
                return first_action

            cur_g = g_score[state]
            hd_rank = self._HEADING_RANK[hd]

            successors = []
            if (cell, hd) not in self._walls:
                nxt_cell = self._next_pos(cell, hd)
                cost = 1.0 + self._predict_penalty(cell, hd)
                successors.append(((nxt_cell, hd), cost, Action.FORWARD))
            lhd = self._CW_ORDER[(hd_rank - 1) % 4]
            rhd = self._CW_ORDER[(hd_rank + 1) % 4]
            successors.append(((cell, lhd), 1.0, Action.TURN_LEFT))
            successors.append(((cell, rhd), 1.0, Action.TURN_RIGHT))

            for nxt_state, cost, action in successors:
                new_g = cur_g + cost
                if new_g < g_score.get(nxt_state, float('inf')):
                    g_score[nxt_state] = new_g
                    came_from[nxt_state] = (state, action)
                    counter += 1
                    heapq.heappush(
                        open_heap,
                        (new_g + heur(nxt_state[0]), new_g, counter, nxt_state),
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
