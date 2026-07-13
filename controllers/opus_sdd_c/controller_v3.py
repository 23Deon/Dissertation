from gridbot.sim.actions import Action, Heading


class Controller:
    _CW_ORDER = [Heading.N, Heading.E, Heading.S, Heading.W]

    def __init__(self):
        self._prev_pos = None
        self._prev_action = None
        self._mode = "greedy"
        self._greedy_block_streak = 0
        self._wall_side = None
        self._wall_steps = 0
        self._wall_budget = 0
        self._wall_entry_pos = None
        self._wall_entry_dist = 0
        self._wall_block_streak = 0
        self._best_dist = None
        self._steps_since_best = 0

    def act(self, observation) -> Action:
        pos = observation.position
        heading = observation.heading
        goal = observation.goal

        if isinstance(pos, list):
            pos = tuple(pos)
        if isinstance(goal, list):
            goal = tuple(goal)

        if pos[0] == goal[0] and pos[1] == goal[1]:
            self._prev_pos = pos
            self._prev_action = Action.WAIT
            return Action.WAIT

        dist = abs(goal[0] - pos[0]) + abs(goal[1] - pos[1])
        if self._best_dist is None or dist < self._best_dist:
            self._best_dist = dist
            self._steps_since_best = 0
        else:
            self._steps_since_best += 1

        blocked = (
            self._prev_action == Action.FORWARD
            and self._prev_pos is not None
            and self._prev_pos == pos
        )

        if self._mode == "greedy":
            action = self._act_greedy(pos, heading, goal, blocked)
        else:
            action = self._act_wall(pos, heading, goal, blocked)

        self._prev_pos = pos
        self._prev_action = action
        return action

    def _act_greedy(self, pos, heading, goal, blocked):
        if blocked:
            self._greedy_block_streak += 1
        elif self._prev_action == Action.FORWARD:
            self._greedy_block_streak = 0

        if self._greedy_block_streak >= 2:
            self._enter_wall(pos, heading, goal, prefer_side=None)
            return self._act_wall(pos, heading, goal, blocked=False)

        dx = goal[0] - pos[0]
        dy = goal[1] - pos[1]
        ranked = self._ranked_headings(dx, dy)

        priority = min(self._greedy_block_streak, len(ranked) - 1)
        desired = ranked[priority]

        if heading == desired:
            return Action.FORWARD
        return self._turn_toward(heading, desired)

    def _enter_wall(self, pos, heading, goal, prefer_side):
        self._mode = "wall"
        self._wall_steps = 0
        self._wall_budget = 200
        self._wall_entry_pos = pos
        self._wall_entry_dist = abs(goal[0] - pos[0]) + abs(goal[1] - pos[1])
        self._wall_block_streak = 0
        self._greedy_block_streak = 0

        if prefer_side is not None:
            self._wall_side = prefer_side
            return

        dx = goal[0] - pos[0]
        dy = goal[1] - pos[1]

        left_h = self._rotate(heading, -1)
        right_h = self._rotate(heading, 1)

        def score(candidate):
            if candidate == Heading.E:
                return dx
            if candidate == Heading.W:
                return -dx
            if candidate == Heading.S:
                return dy
            return -dy

        if score(right_h) >= score(left_h):
            self._wall_side = "right"
        else:
            self._wall_side = "left"

    def _act_wall(self, pos, heading, goal, blocked):
        self._wall_steps += 1

        if self._wall_steps > self._wall_budget:
            self._mode = "greedy"
            self._greedy_block_streak = 0
            self._wall_block_streak = 0
            return self._act_greedy(pos, heading, goal, blocked=False)

        dist = abs(goal[0] - pos[0]) + abs(goal[1] - pos[1])

        if (
            self._wall_steps > 3
            and dist + 1 < self._wall_entry_dist
            and not blocked
            and pos != self._wall_entry_pos
        ):
            self._mode = "greedy"
            self._greedy_block_streak = 0
            self._wall_block_streak = 0
            return self._act_greedy(pos, heading, goal, blocked=False)

        if blocked:
            self._wall_block_streak += 1
        elif self._prev_action == Action.FORWARD:
            self._wall_block_streak = 0

        if self._wall_block_streak >= 3:
            self._wall_side = "left" if self._wall_side == "right" else "right"
            self._wall_block_streak = 0

        if self._wall_side == "right":
            pref = [
                self._rotate(heading, 1),
                heading,
                self._rotate(heading, -1),
                self._rotate(heading, 2),
            ]
        else:
            pref = [
                self._rotate(heading, -1),
                heading,
                self._rotate(heading, 1),
                self._rotate(heading, 2),
            ]

        idx = min(self._wall_block_streak, len(pref) - 1)
        desired = pref[idx]

        if self._wall_steps == 1 and not blocked:
            desired = pref[0]

        if heading == desired:
            return Action.FORWARD
        return self._turn_toward(heading, desired)

    def _rotate(self, heading, steps):
        index = self._CW_ORDER.index(heading)
        return self._CW_ORDER[(index + steps) % 4]

    def _ranked_headings(self, dx, dy):
        if dx >= 0:
            x_toward, x_away = Heading.E, Heading.W
        else:
            x_toward, x_away = Heading.W, Heading.E

        if dy >= 0:
            y_toward, y_away = Heading.S, Heading.N
        else:
            y_toward, y_away = Heading.N, Heading.S

        if abs(dx) >= abs(dy):
            return [x_toward, y_toward, y_away, x_away]
        return [y_toward, x_toward, x_away, y_away]

    def _turn_toward(self, current, desired):
        ci = self._CW_ORDER.index(current)
        di = self._CW_ORDER.index(desired)
        diff = (di - ci) % 4
        if diff == 1:
            return Action.TURN_RIGHT
        if diff == 3:
            return Action.TURN_LEFT
        return Action.TURN_RIGHT
