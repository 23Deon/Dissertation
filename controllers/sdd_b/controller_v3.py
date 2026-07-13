from gridbot.sim.actions import Action, Heading


class Controller:
    def _init_state(self):
        if not hasattr(self, "_mode"):
            self._mode = "greedy"
            self._follow_side = "right"
            self._prev_position = None
            self._last_action = None
            self._follow_steps = 0
            self._follow_start_dist = 0
            self._best_follow_dist = 0
            self._blocked_streak = 0
            self._forward_streak = 0
            self._since_turn = 0
            self._recent_positions = []

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

    def _side_turn_action(self):
        if self._follow_side == "right":
            return Action.TURN_RIGHT
        return Action.TURN_LEFT

    def _toggle_side(self):
        if self._follow_side == "right":
            self._follow_side = "left"
        else:
            self._follow_side = "right"

    def _remember_position(self, position):
        if not self._recent_positions or self._recent_positions[-1] != position:
            self._recent_positions.append(position)
            if len(self._recent_positions) > 24:
                self._recent_positions.pop(0)

    def _recent_count(self, position):
        count = 0
        for p in self._recent_positions:
            if p == position:
                count += 1
        return count

    def _enter_follow(self, current_dist):
        self._mode = "follow"
        self._toggle_side()
        self._follow_steps = 0
        self._follow_start_dist = current_dist
        self._best_follow_dist = current_dist
        self._blocked_streak = 0
        self._forward_streak = 0
        self._since_turn = 0
        self._recent_positions = []

    def act(self, observation) -> Action:
        self._init_state()

        position = observation.position
        heading = observation.heading
        goal = observation.goal

        if position == goal:
            self._mode = "greedy"
            self._prev_position = position
            self._last_action = Action.WAIT
            self._follow_steps = 0
            self._blocked_streak = 0
            self._forward_streak = 0
            self._since_turn = 0
            self._recent_positions = []
            return Action.WAIT

        current_dist = self._manhattan(position, goal)
        preferred = self._preferred_headings(position, goal)
        failed_forward = self._last_action == Action.FORWARD and self._prev_position == position
        moved = self._prev_position is not None and self._prev_position != position

        if moved:
            self._remember_position(position)

        if self._mode == "greedy":
            if failed_forward:
                self._enter_follow(current_dist)
                self._blocked_streak = 1
                action = self._side_turn_action()
                self._prev_position = position
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
            self._last_action = action
            return action

        self._follow_steps += 1

        if current_dist < self._best_follow_dist:
            self._best_follow_dist = current_dist

        if failed_forward:
            self._blocked_streak += 1
            self._forward_streak = 0
            self._since_turn = 0

            if self._blocked_streak >= 3:
                self._toggle_side()
                self._blocked_streak = 1

            action = self._side_turn_action()
            self._prev_position = position
            self._last_action = action
            return action

        if self._last_action == Action.FORWARD and moved:
            self._blocked_streak = 0
            self._forward_streak += 1
            self._since_turn += 1
        elif self._last_action in (Action.TURN_LEFT, Action.TURN_RIGHT):
            self._since_turn = 0

        revisit_count = self._recent_count(position)

        if self._follow_steps >= 8 and self._forward_streak >= 4:
            if heading in preferred:
                next_pos = self._next_position(position, heading)
                next_dist = self._manhattan(next_pos, goal)
                if next_dist < current_dist and current_dist <= self._best_follow_dist and current_dist < self._follow_start_dist:
                    self._mode = "greedy"
                    self._blocked_streak = 0
                    self._forward_streak = 0
                    self._since_turn = 0
                    action = Action.FORWARD
                    self._prev_position = position
                    self._last_action = action
                    return action

        if self._last_action in (Action.TURN_LEFT, Action.TURN_RIGHT):
            action = Action.FORWARD
            self._prev_position = position
            self._last_action = action
            return action

        should_probe_turn = False

        if self._since_turn >= 6 and heading not in preferred and self._forward_streak >= 3:
            should_probe_turn = True

        if revisit_count >= 2 and self._since_turn >= 2:
            should_probe_turn = True

        if current_dist > self._best_follow_dist + 3 and self._since_turn >= 4:
            should_probe_turn = True

        if should_probe_turn:
            self._toggle_side()
            self._forward_streak = 0
            self._since_turn = 0
            action = self._side_turn_action()
            self._prev_position = position
            self._last_action = action
            return action

        action = Action.FORWARD
        self._prev_position = position
        self._last_action = action
        return action
