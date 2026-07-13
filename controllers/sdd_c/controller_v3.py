from gridbot.sim.actions import Action, Heading


class Controller:
    def act(self, observation) -> Action:
        if not hasattr(self, "_mode"):
            self._mode = "goal"
            self._last_position = None
            self._last_action = None
            self._preferred_heading = Heading.N
            self._follow_hand = "right"
            self._follow_phase = "try_hand_turn"
            self._turn_balance = 0
            self._follow_steps = 0
            self._entry_distance = 0

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

        def manhattan(pos, target):
            return abs(pos[0] - target[0]) + abs(pos[1] - target[1])

        def desired_headings(pos, target):
            x, y = pos
            goal_x, goal_y = target
            dx = goal_x - x
            dy = goal_y - y

            headings = []
            if abs(dx) >= abs(dy):
                if dx > 0:
                    headings.append(Heading.E)
                elif dx < 0:
                    headings.append(Heading.W)
                if dy > 0:
                    headings.append(Heading.S)
                elif dy < 0:
                    headings.append(Heading.N)
            else:
                if dy > 0:
                    headings.append(Heading.S)
                elif dy < 0:
                    headings.append(Heading.N)
                if dx > 0:
                    headings.append(Heading.E)
                elif dx < 0:
                    headings.append(Heading.W)
            return headings

        def turn_toward(current, target):
            if current == target:
                return Action.FORWARD
            if left_of[current] == target:
                return Action.TURN_LEFT
            if right_of[current] == target:
                return Action.TURN_RIGHT
            return Action.TURN_LEFT

        def turn_delta(action):
            if action == Action.TURN_RIGHT:
                return 1
            if action == Action.TURN_LEFT:
                return -1
            return 0

        def hand_turn_action():
            return Action.TURN_RIGHT if self._follow_hand == "right" else Action.TURN_LEFT

        def away_turn_action():
            return Action.TURN_LEFT if self._follow_hand == "right" else Action.TURN_RIGHT

        if position == goal:
            self._mode = "goal"
            self._last_position = position
            self._last_action = Action.WAIT
            self._follow_phase = "try_hand_turn"
            self._turn_balance = 0
            self._follow_steps = 0
            return Action.WAIT

        blocked_forward = (
            self._last_action == Action.FORWARD
            and self._last_position is not None
            and position == self._last_position
        )

        moved_after_forward = (
            self._last_action == Action.FORWARD
            and self._last_position is not None
            and position != self._last_position
        )

        desired = desired_headings(position, goal)
        primary = desired[0] if desired else heading
        if len(desired) > 1:
            secondary = desired[1]
        else:
            secondary = opposite_of[primary]
        current_distance = manhattan(position, goal)

        if self._mode == "follow":
            if self._last_action == Action.TURN_LEFT or self._last_action == Action.TURN_RIGHT:
                if self._follow_phase == "try_hand_turn":
                    self._follow_phase = "try_hand_forward"
                elif self._follow_phase == "undo_hand_turn":
                    self._follow_phase = "try_straight_forward"
                elif self._follow_phase == "turn_away_corner":
                    self._follow_phase = "try_away_forward"
                elif self._follow_phase == "turn_away_again":
                    self._follow_phase = "try_back_forward"
            elif self._last_action == Action.FORWARD:
                if self._follow_phase == "try_hand_forward":
                    self._follow_phase = "try_hand_turn" if moved_after_forward else "undo_hand_turn"
                elif self._follow_phase == "try_straight_forward":
                    self._follow_phase = "try_hand_turn" if moved_after_forward else "turn_away_corner"
                elif self._follow_phase == "try_away_forward":
                    self._follow_phase = "try_hand_turn" if moved_after_forward else "turn_away_again"
                elif self._follow_phase == "try_back_forward":
                    self._follow_phase = "try_hand_turn" if moved_after_forward else "turn_away_again"

        if self._mode == "goal" and blocked_forward:
            self._mode = "follow"
            self._preferred_heading = primary
            self._entry_distance = current_distance
            self._follow_steps = 0
            self._turn_balance = 0
            self._follow_phase = "try_hand_turn"
            if right_of[heading] == secondary:
                self._follow_hand = "right"
            elif left_of[heading] == secondary:
                self._follow_hand = "left"
            else:
                self._follow_hand = "right"

        if self._mode == "follow":
            if (
                self._follow_phase == "try_hand_turn"
                and self._follow_steps >= 4
                and heading == self._preferred_heading
                and self._turn_balance == 0
                and current_distance < self._entry_distance
            ):
                self._mode = "goal"

        if self._mode == "goal":
            action = turn_toward(heading, primary)
        else:
            if self._follow_phase == "try_hand_turn":
                action = hand_turn_action()
            elif self._follow_phase == "try_hand_forward":
                action = Action.FORWARD
            elif self._follow_phase == "undo_hand_turn":
                action = away_turn_action()
            elif self._follow_phase == "try_straight_forward":
                action = Action.FORWARD
            elif self._follow_phase == "turn_away_corner":
                action = away_turn_action()
            elif self._follow_phase == "try_away_forward":
                action = Action.FORWARD
            elif self._follow_phase == "turn_away_again":
                action = away_turn_action()
            elif self._follow_phase == "try_back_forward":
                action = Action.FORWARD
            else:
                action = away_turn_action()

        self._turn_balance += turn_delta(action)
        if self._mode == "follow":
            self._follow_steps += 1

        self._last_position = position
        self._last_action = action
        return action
