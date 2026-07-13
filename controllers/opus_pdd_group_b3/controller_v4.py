import heapq

from gridbot.sim.actions import Action, Heading


class Controller:
    """Online heading-aware A* with wall prediction and empirical direction learning.

    Three ideas layered on top of each other:

    1. State space is (cell, heading) and actions are FORWARD / TURN_LEFT /
       TURN_RIGHT, each unit cost. A* therefore returns a minimum-action
       sequence, not just a minimum-cell path — turns are counted, so plans
       that avoid unnecessary rotation are preferred.

    2. Parallel-wall prediction. After a bump, edges in the same direction
       at nearby perpendicular offsets get a soft cost penalty that falls
       off with distance. This stops the planner from re-probing the same
       wall at every cell of a long corridor — previously the dominant
       source of wasted actions.

    3. Empirical direction vectors. For each heading, the (dx, dy) that a
       FORWARD actually produces is learned by observation. Defaults
       follow the standard math convention (N=+y, E=+x), but the first
       successful forward in each heading overwrites that default with
       the simulator's actual behaviour. This makes the controller robust
       to whichever convention the sim uses.

    Walls are recorded symmetrically (both sides of each edge) so a wall
    learned from one side doesn't need to be re-bumped from the other.
    """

    _CW_ORDER = (Heading.N, Heading.E, Heading.S, Heading.W)
    _HEADING_RANK = dict(zip(_CW_ORDER, range(4)))
    _OPPOSITE = {
        Heading.N: Heading.S,
        Heading.S: Heading.N,
        Heading.E: Heading.W,
        Heading.W: Heading.E,
    }
    _DEFAULT_DELTAS = {
        Heading.N: (0, 1),
        Heading.E: (1, 0),
        Heading.S: (0, -1),
        Heading.W: (-1, 0),
    }

    _MAX_NODES = 50000
    _PREDICT_RADIUS = 4
    _PREDICT_WEIGHT = 3.0

    def __init__(self):
        self._last_pos = None
        self._last_heading = None
        self._last_action = None
        self._walls = set()
        self._deltas = dict(self._DEFAULT_DELTAS)

    def act(self, observation) -> Action:
        pos = tuple(observation.position)
        goal = tuple(observation.goal)
        heading = observation.heading

        if self._last_action == Action.FORWARD and self._last_pos is not None:
            if self._last_pos == pos:
                self._walls.add((pos, self._last_heading))
                dx, dy = self._deltas[self._last_heading]
                other = (pos[0] + dx, pos[1] + dy)
                self._walls.add((other, self._OPPOSITE[self._last_heading]))
            else:
                dx = pos[0] - self._last_pos[0]
                dy = pos[1] - self._last_pos[1]
                self._deltas[self._last_heading] = (dx, dy)

        action = self._decide(pos, goal, heading)

        self._last_pos = pos
        self._last_heading = heading
        self._last_action = action
        return action

    def _decide(self, pos, goal, heading):
        if pos == goal:
            return Action.WAIT
        action = self._plan(pos, heading, goal)
        return action if action is not None else Action.WAIT

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
                if new_g < g_score.get(nxt_state, float("inf")):
                    g_score[nxt_state] = new_g
                    came_from[nxt_state] = (state, action)
                    counter += 1
                    nxt_cell = nxt_state[0]
                    heapq.heappush(
                        open_heap,
                        (new_g + heur(nxt_cell), new_g, counter, nxt_state),
                    )

        return None

    def _predict_penalty(self, cell, direction):
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

    def _next_pos(self, pos, h):
        dx, dy = self._deltas[h]
        return (pos[0] + dx, pos[1] + dy)
