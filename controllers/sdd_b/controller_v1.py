from gridbot.sim.actions import Action, Heading


class Controller:
    def _init_state(self):
        if not hasattr(self, "_mode"):
            self._mode = "greedy"
            self._follow_turn = Action.TURN_RIGHT
            self._last_position = None
            self._stuck_turns = 0

    def _delta(self, heading):
        if heading == Heading.N:
            return (0, -1)
        if heading == Heading.E:
            return (1, 0)
        if heading == Heading.S:
            return (0, 1)
        return (-1, 0)

    def _left_of(self, heading):
        if heading == Heading.N:
            return Heading.W
        if heading == Heading.W:
            return Heading.S
        if heading == Heading.S:
            return Heading.E
        return Heading.N

    def _right_of(self, heading):
        if heading == Heading.N:
            return Heading.E
        if heading == Heading.E:
            return Heading.S
        if heading == Heading.S:
            return Heading.W
        return Heading.N

    def _next_position(self, position, heading):
        dx, dy = self._delta(heading)
        return (position[0] + dx, position[1] + dy)

    def _manhattan(self, a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def _preferred_headings(self, position, goal):
        dx = goal[0] - position[0]
        dy = goal[1] - position[1]

        primary = None
        secondary = None

        if abs(dx) >= abs(dy):
            if dx > 0:
                primary = Heading.E
            elif dx < 0:
                primary = Heading.W

            if dy > 0:
                secondary = Heading.S
            elif dy < 0:
                secondary = Heading.N
        else:
            if dy > 0:
                primary = Heading.S
            elif dy < 0:
                primary = Heading.N

            if dx > 0:
                secondary = Heading.E
            elif dx < 0:
                secondary = Heading.W

        headings = []
        if primary is not None:
            headings.append(primary)
        if secondary is not None and secondary != primary:
            headings.append(secondary)

        for h in (Heading.N, Heading.E, Heading.S, Heading.W):
            if h not in headings:
                headings.append(h)
        return headings

    def _turn_toward(self, current, target):
        if current == target:
            return Action.WAIT
        if self._left_of(current) == target:
            return Action.TURN_LEFT
        if self._right_of(current) == target:
            return Action.TURN_RIGHT
        return Action.TURN_RIGHT

    def _choose_follow_turn(self, position, heading, goal):
        preferred = self._preferred_headings(position, goal)
        left_heading = self._left_of(heading)
        right_heading = self._right_of(heading)

        for h in preferred:
            if h == left_heading:
                return Action.TURN_LEFT
            if h == right_heading:
                return Action.TURN_RIGHT
        return Action.TURN_RIGHT

    def act(self, observation) -> Action:
        self._init_state()

        position = observation.position
        heading = observation.heading
        goal = observation.goal
        front_blocked = observation.front_blocked

        if position == goal:
            self._mode = "greedy"
            self._stuck_turns = 0
            self._last_position = position
            return Action.WAIT

        current_dist = self._manhattan(position, goal)
        preferred = self._preferred_headings(position, goal)

        if self._last_position == position:
            self._stuck_turns += 1
        else:
            self._stuck_turns = 0
        self._last_position = position

        if self._mode == "follow":
            if not front_blocked:
                forward_pos = self._next_position(position, heading)
                if heading in preferred and self._manhattan(forward_pos, goal) < current_dist:
                    self._mode = "greedy"
                    self._stuck_turns = 0
                    return Action.FORWARD
                if self._stuck_turns >= 3:
                    if self._follow_turn == Action.TURN_RIGHT:
                        self._follow_turn = Action.TURN_LEFT
                    else:
                        self._follow_turn = Action.TURN_RIGHT
                    self._stuck_turns = 0
                    return self._follow_turn
                return Action.FORWARD

            turn_action = self._choose_follow_turn(position, heading, goal)
            self._follow_turn = turn_action
            self._stuck_turns = 0
            return turn_action

        for desired in preferred:
            if heading == desired:
                if not front_blocked:
                    return Action.FORWARD
                self._mode = "follow"
                self._follow_turn = self._choose_follow_turn(position, heading, goal)
                self._stuck_turns = 0
                return self._follow_turn

        target = preferred[0]
        action = self._turn_toward(heading, target)
        if action in (Action.TURN_LEFT, Action.TURN_RIGHT):
            return action

        if not front_blocked:
            return Action.FORWARD

        return Action.TURN_RIGHT
