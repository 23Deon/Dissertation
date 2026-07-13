from gridbot.sim.actions import Action, Heading


class Controller:
    _CW_ORDER = [Heading.N, Heading.E, Heading.S, Heading.W]

    def __init__(self):
        self._prev_pos = None
        self._prev_action = None
        self._mode = "greedy"
        self._wall_side = None
        self._wall_steps = 0
        self._wall_budget = 0
        self._greedy_block_streak = 0
        self._last_free_pos = None
        self._since_progress = 0

    def act(self, observation) -> Action:
        pos = observation.position
        if not isinstance(pos, tuple):
            pos = tuple(pos)
        heading = observation.heading
        goal = observation.goal
        if not isinstance(goal, tuple):
            goal = tuple(goal)

        if pos[0] == goal[0] and pos[1] == goal[1]:
            self._prev_pos = pos
            self._prev_action = Action.WAIT
            self._mode = "greedy"
            self._greedy_block_streak = 0
            self._wall_side = None
            self._wall_steps = 0
            self._wall_budget = 0
            return Action.WAIT

        blocked = (
            self._prev_action == Action.FORWARD
            and self._prev_pos is not None
            and self._prev_pos == pos
        )

        if self._last_free_pos is None:
            self._last_free_pos = pos
            self._since_progress = 0
        elif pos != self._last_free_pos:
            self._last_free_pos = pos
            self._since_progress = 0
        else:
            self._since_progress += 1

        if self._mode == "greedy":
            action = self._act_greedy(pos, heading, goal, blocked)
        else:
            action = self._act_wall_follow(pos, heading, goal, blocked)

        self._prev_pos = pos
        self._prev_action = action
        return action

    def _act_greedy(self, pos, heading, goal, blocked):
        if blocked:
            self._greedy_block_streak += 1
        elif self._prev_action == Action.FORWARD:
            self._greedy_block_streak = 0

        if self._greedy_block_streak >= 2:
            self._enter_wall_follow(pos, heading, goal)
            return self._act_wall_follow(pos, heading, goal, blocked=False)

        dx = goal[0] - pos[0]
        dy = goal[1] - pos[1]
        ranked = self._ranked_headings(dx, dy)

        priority = min(self._greedy_block_streak, len(ranked) - 1)
        desired = ranked[priority]

        if heading == desired:
            return Action.FORWARD
        return self._turn_toward(heading, desired)

    def _enter_wall_follow(self, pos, heading, goal):
        self._mode = "wall"
        dx = goal[0] - pos[0]
        dy = goal[1] - pos[1]
        if abs(dx) >= abs(dy):
            primary = Heading.E if dx >= 0 else Heading.W
        else:
            primary = Heading.S if dy >= 0 else Heading.N

        if abs(dx) >= abs(dy):
            self._wall_side = "right" if dy >= 0 else "left"
        else:
            self._wall_side = "right" if dx <= 0 else "left"

        self._wall_steps = 0
        self._wall_budget = 64
        self._wall_primary = primary
        self._wall_rotation_index = 0

    def _act_wall_follow(self, pos, heading, goal, blocked):
        self._wall_steps += 1

        if self._wall_steps > self._wall_budget:
            self._mode = "greedy"
            self._greedy_block_streak = 0
            return self._act_greedy(pos, heading, goal, blocked=False)

        dx = goal[0] - pos[0]
        dy = goal[1] - pos[1]
        if (dx == 0 or dy == 0) and self._wall_steps > 2 and not blocked:
            self._mode = "greedy"
            self._greedy_block_streak = 0
            return self._act_greedy(pos, heading, goal, blocked=False)

        if self._wall_side == "right":
            preferred = [
                self._rotate(heading, -1),
                heading,
                self._rotate(heading, 1),
                self._rotate(heading, 2),
            ]
        else:
            preferred = [
                self._rotate(heading, 1),
                heading,
                self._rotate(heading, -1),
                self._rotate(heading, 2),
            ]

        if blocked:
            index = self._wall_rotation_index
            index = min(index + 1, len(preferred) - 1)
            self._wall_rotation_index = index
        else:
            self._wall_rotation_index = 0

        desired = preferred[self._wall_rotation_index]

        if heading == desired:
            return Action.FORWARD
        return self._turn_toward(heading, desired)

    @property
    def _wall_rotation_index(self):
        return getattr(self, "_wri", 0)

    @_wall_rotation_index.setter
    def _wall_rotation_index(self, value):
        self._wri = value

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
