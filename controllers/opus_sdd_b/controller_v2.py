from gridbot.sim.actions import Action, Heading


class Controller:
    _ORDER = (Heading.N, Heading.E, Heading.S, Heading.W)
    _DELTA = {
        Heading.N: (0, -1),
        Heading.E: (1, 0),
        Heading.S: (0, 1),
        Heading.W: (-1, 0),
    }

    def __init__(self):
        self._prev_pos = None
        self._prev_action = None
        self._prev_heading = None
        self._blocked_edges = set()
        self._visited = {}
        self._wall_follow = False
        self._wall_side = None
        self._wall_steps = 0
        self._wall_start_dist = None
        self._wall_budget = 0

    def act(self, observation) -> Action:
        pos = observation.position
        goal = observation.goal
        heading = observation.heading

        if pos == goal:
            return self._record(pos, heading, Action.WAIT)

        if (
            self._prev_action == Action.FORWARD
            and self._prev_pos is not None
            and self._prev_pos == pos
            and self._prev_heading is not None
        ):
            self._blocked_edges.add((pos, self._prev_heading))

        self._visited[pos] = self._visited.get(pos, 0) + 1

        cur_dist = self._manhattan(pos, goal)

        if self._wall_follow:
            if cur_dist < (self._wall_start_dist or cur_dist + 1):
                self._wall_follow = False
                self._wall_side = None
                self._wall_steps = 0
            else:
                self._wall_steps += 1
                if self._wall_steps > self._wall_budget:
                    self._wall_follow = False
                    self._wall_side = None
                    self._wall_steps = 0

        if not self._wall_follow:
            action = self._greedy_action(pos, heading, goal)
            if action is not None:
                return self._record(pos, heading, action)

            self._wall_follow = True
            self._wall_start_dist = cur_dist
            self._wall_steps = 0
            self._wall_budget = 80
            self._wall_side = self._choose_wall_side(pos, heading, goal)

        action = self._wall_follow_action(pos, heading)
        return self._record(pos, heading, action)

    def _greedy_action(self, pos, heading, goal):
        dx = goal[0] - pos[0]
        dy = goal[1] - pos[1]

        preferred = []
        if abs(dx) >= abs(dy):
            if dx > 0:
                preferred.append(Heading.E)
            elif dx < 0:
                preferred.append(Heading.W)
            if dy > 0:
                preferred.append(Heading.S)
            elif dy < 0:
                preferred.append(Heading.N)
        else:
            if dy > 0:
                preferred.append(Heading.S)
            elif dy < 0:
                preferred.append(Heading.N)
            if dx > 0:
                preferred.append(Heading.E)
            elif dx < 0:
                preferred.append(Heading.W)

        best = None
        best_score = None
        for candidate in preferred:
            if (pos, candidate) in self._blocked_edges:
                continue
            nxt = self._step(pos, candidate)
            visits = self._visited.get(nxt, 0)
            score = (visits, self._manhattan(nxt, goal))
            if best_score is None or score < best_score:
                best_score = score
                best = candidate

        if best is None:
            return None

        if heading == best:
            return Action.FORWARD
        return self._rotate_toward(heading, best)

    def _wall_follow_action(self, pos, heading):
        side = self._wall_side or "right"

        if side == "right":
            order = [
                self._turn_rel(heading, -1),
                heading,
                self._turn_rel(heading, 1),
                self._turn_rel(heading, 2),
            ]
        else:
            order = [
                self._turn_rel(heading, 1),
                heading,
                self._turn_rel(heading, -1),
                self._turn_rel(heading, 2),
            ]

        chosen = None
        for candidate in order:
            if (pos, candidate) in self._blocked_edges:
                continue
            chosen = candidate
            break

        if chosen is None:
            return Action.TURN_RIGHT

        if chosen == heading:
            return Action.FORWARD
        return self._rotate_toward(heading, chosen)

    def _choose_wall_side(self, pos, heading, goal):
        dx = goal[0] - pos[0]
        dy = goal[1] - pos[1]
        right_h = self._turn_rel(heading, 1)
        left_h = self._turn_rel(heading, -1)
        rdx, rdy = self._DELTA[right_h]
        ldx, ldy = self._DELTA[left_h]
        right_align = rdx * (1 if dx > 0 else -1 if dx < 0 else 0) + rdy * (
            1 if dy > 0 else -1 if dy < 0 else 0
        )
        left_align = ldx * (1 if dx > 0 else -1 if dx < 0 else 0) + ldy * (
            1 if dy > 0 else -1 if dy < 0 else 0
        )
        if left_align > right_align:
            return "left"
        return "right"

    def _turn_rel(self, heading, steps):
        index = self._ORDER.index(heading)
        return self._ORDER[(index + steps) % 4]

    def _rotate_toward(self, current, target) -> Action:
        ci = self._ORDER.index(current)
        ti = self._ORDER.index(target)
        diff = (ti - ci) % 4
        if diff == 1:
            return Action.TURN_RIGHT
        if diff == 3:
            return Action.TURN_LEFT
        return Action.TURN_RIGHT

    def _step(self, pos, heading):
        dx, dy = self._DELTA[heading]
        return (pos[0] + dx, pos[1] + dy)

    @staticmethod
    def _manhattan(a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def _record(self, pos, heading, action) -> Action:
        self._prev_pos = pos
        self._prev_heading = heading
        self._prev_action = action
        return action
