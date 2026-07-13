from gridbot.sim.actions import Action, Heading


class Controller:
    def _init_state(self):
        if not hasattr(self, "_mode"):
            self._mode = "greedy"
            self._follow_side = "right"
            self._prev_position = None
            self._prev_heading = None
            self._last_action = None
            self._turn_budget = 0

    def _left(self, heading):
        if heading == Heading.N:
            return Heading.W
        if heading == Heading.W:
            return Heading.S
        if heading == Heading.S:
            return Heading.E
        return Heading.N

    def _right(self, heading):
        if heading == Heading.N:
            return Heading.E
        if heading == Heading.E:
            return Heading.S
        if heading == Heading.S:
            return Heading.W
        return Heading.N

    def _opposite(self, heading):
        if heading == Heading.N:
            return Heading.S
        if heading == Heading.S:
            return Heading.N
        if heading == Heading.E:
            return Heading.W
        return Heading.E

    def _delta(self, heading):
        if heading == Heading.N:
            return (0, -1)
        if heading == Heading.E:
            return (1, 0)
        if heading == Heading.S:
            return (0, 1)
        return (-1, 0)

    def _next_position(self, position, heading):
        dx, dy = self._delta(heading)
        return (position[0] + dx, position[1] + dy)

    def _manhattan(self, a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def _preferred_headings(self, position, goal):
        dx = goal[0] - position[0]
        dy = goal[1] - position[1]

        first = None
        second = None

        if abs(dx) >= abs(dy):
            if dx > 0:
                first = Heading.E
            elif dx < 0:
                first = Heading.W

            if dy > 0:
                second = Heading.S
            elif dy < 0:
                second = Heading.N
        else:
            if dy > 0:
                first = Heading.S
            elif dy < 0:
                first = Heading.N

            if dx > 0:
                second = Heading.E
            elif dx < 0:
                second = Heading.W

        ordered = []
        if first is not None:
            ordered.append(first)
        if second is not None and second != first:
            ordered.append(second)

        for h in (Heading.N, Heading.E, Heading.S, Heading.W):
            if h not in ordered:
                ordered.append(h)
        return ordered

    def _turn_toward(self, current, target):
        if current == target:
            return Action.WAIT
        if self._left(current) == target:
            return Action.TURN_LEFT
        if self._right(current) == target:
            return Action.TURN_RIGHT
        return Action.TURN_RIGHT

    def _follow_turn_action(self):
        if self._follow_side == "right":
            return Action.TURN_RIGHT
        return Action.TURN_LEFT

    def act(self, observation) -> Action:
        self._init_state()

        position = observation.position
        heading = observation.heading
        goal = observation.goal

        if position == goal:
            self._mode = "greedy"
            self._turn_budget = 0
            self._prev_position = position
            self._prev_heading = heading
            self._last_action = Action.WAIT
            return Action.WAIT

        failed_forward = (
            self._last_action == Action.FORWARD
            and self._prev_position == position
        )

        current_dist = self._manhattan(position, goal)
        preferred = self._preferred_headings(position, goal)

        if failed_forward:
            if self._mode != "follow":
                self._mode = "follow"
                if self._follow_side == "right":
                    self._follow_side = "left"
                else:
                    self._follow_side = "right"
            self._turn_budget = 2
            action = self._follow_turn_action()
            self._prev_position = position
            self._prev_heading = heading
            self._last_action = action
            return action

        if self._mode == "follow":
            if heading in preferred:
                next_pos = self._next_position(position, heading)
                if self._manhattan(next_pos, goal) < current_dist:
                    self._mode = "greedy"
                    self._turn_budget = 0
                    action = Action.FORWARD
                    self._prev_position = position
                    self._prev_heading = heading
                    self._last_action = action
                    return action

            if self._turn_budget > 0:
                self._turn_budget -= 1
                action = self._follow_turn_action()
                self._prev_position = position
                self._prev_heading = heading
                self._last_action = action
                return action

            action = Action.FORWARD
            self._prev_position = position
            self._prev_heading = heading
            self._last_action = action
            return action

        target = preferred[0]
        if heading == target:
            action = Action.FORWARD
        else:
            action = self._turn_toward(heading, target)
            if action == Action.WAIT:
                action = Action.FORWARD

        self._prev_position = position
        self._prev_heading = heading
        self._last_action = action
        return action
