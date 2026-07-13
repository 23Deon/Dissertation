from gridbot.sim.actions import Action, Heading


class Controller:
    def act(self, observation) -> Action:
        if not hasattr(self, "_mode"):
            self._mode = "goal"
            self._last_position = None
            self._last_action = None
            self._follow_hand = Action.TURN_RIGHT
            self._follow_state = "probe_turn"
            self._entry_distance = 0
            self._follow_progress = 0

        position = observation.position
        heading = observation.heading
        goal = observation.goal

        left_of = {
            Heading.N: Heading.W,
            Heading.W: Heading.S,
            Heading.S: Heading.E,
            Heading.E: Heading.N,
        }
        right_of = {
            Heading.N: Heading.E,
            Heading.E: Heading.S,
            Heading.S: Heading.W,
            Heading.W: Heading.N,
        }
        opposite_of = {
            Heading.N: Heading.S,
            Heading.E: Heading.W,
            Heading.S: Heading.N,
            Heading.W: Heading.E,
        }

        def manhattan(a, b):
            return abs(a[0] - b[0]) + abs(a[1] - b[1])

        def desired_headings(pos, target):
            x, y = pos
            goal_x, goal_y = target
            dx = goal_x - x
            dy = goal_y - y

            result = []
            if abs(dx) >= abs(dy):
                if dx > 0:
                    result.append(Heading.E)
                elif dx < 0:
                    result.append(Heading.W)
                if dy > 0:
                    result.append(Heading.S)
                elif dy < 0:
                    result.append(Heading.N)
            else:
                if dy > 0:
                    result.append(Heading.S)
                elif dy < 0:
                    result.append(Heading.N)
                if dx > 0:
                    result.append(Heading.E)
                elif dx < 0:
                    result.append(Heading.W)
            return result

        def turn_toward(current, target, tie_heading):
            if current == target:
                return Action.FORWARD
            if left_of[current] == target:
                return Action.TURN_LEFT
            if right_of[current] == target:
                return Action.TURN_RIGHT
            if left_of[current] == tie_heading:
                return Action.TURN_LEFT
            if right_of[current] == tie_heading:
                return Action.TURN_RIGHT
            return Action.TURN_LEFT

        def opposite_turn(turn_action):
            if turn_action == Action.TURN_RIGHT:
                return Action.TURN_LEFT
            return Action.TURN_RIGHT

        if position == goal:
            self._mode = "goal"
            self._follow_state = "probe_turn"
            self._follow_progress = 0
            self._last_position = position
            self._last_action = Action.WAIT
            return Action.WAIT

        blocked_forward = (
            self._last_action == Action.FORWARD
            and self._last_position is not None
            and position == self._last_position
        )
        moved_forward = (
            self._last_action == Action.FORWARD
            and self._last_position is not None
            and position != self._last_position
        )

        desired = desired_headings(position, goal)
        primary = desired[0] if desired else heading
        secondary = desired[1] if len(desired) > 1 else opposite_of[primary]
        current_distance = manhattan(position, goal)

        if self._mode == "follow":
            if self._last_action in (Action.TURN_LEFT, Action.TURN_RIGHT):
                if self._follow_state == "probe_turn":
                    self._follow_state = "probe_forward"
                elif self._follow_state == "straight_turn":
                    self._follow_state = "straight_forward"
                elif self._follow_state == "escape_turn":
                    self._follow_state = "straight_forward"
            elif self._last_action == Action.FORWARD:
                if self._follow_state == "probe_forward":
                    if moved_forward:
                        self._follow_progress += 1
                        self._follow_state = "probe_turn"
                    elif blocked_forward:
                        self._follow_state = "straight_turn"
                elif self._follow_state == "straight_forward":
                    if moved_forward:
                        self._follow_progress += 1
                        self._follow_state = "probe_turn"
                    elif blocked_forward:
                        self._follow_state = "escape_turn"

        if self._mode == "goal" and blocked_forward:
            self._mode = "follow"
            self._entry_distance = current_distance
            self._follow_progress = 0
            self._follow_state = "probe_turn"

            if right_of[heading] == secondary:
                self._follow_hand = Action.TURN_RIGHT
            elif left_of[heading] == secondary:
                self._follow_hand = Action.TURN_LEFT
            else:
                self._follow_hand = Action.TURN_RIGHT

        if (
            self._mode == "follow"
            and self._follow_progress >= 2
            and heading == primary
            and current_distance <= self._entry_distance
        ):
            self._mode = "goal"
            self._follow_state = "probe_turn"
            self._follow_progress = 0

        if self._mode == "goal":
            action = turn_toward(heading, primary, secondary)
        else:
            if self._follow_state == "probe_turn":
                action = self._follow_hand
            elif self._follow_state == "probe_forward":
                action = Action.FORWARD
            elif self._follow_state == "straight_turn":
                action = opposite_turn(self._follow_hand)
            elif self._follow_state == "straight_forward":
                action = Action.FORWARD
            else:
                action = opposite_turn(self._follow_hand)

        self._last_position = position
        self._last_action = action
        return action
