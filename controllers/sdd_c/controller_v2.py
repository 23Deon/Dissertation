from gridbot.sim.actions import Action, Heading


class Controller:
    def act(self, observation) -> Action:
        if not hasattr(self, "_mode"):
            self._mode = "goal"
            self._follow_turn = Action.TURN_LEFT
            self._follow_count = 0
            self._last_position = None
            self._last_action = None

        position = observation.position
        heading = observation.heading
        goal = observation.goal

        if position == goal:
            self._mode = "goal"
            self._follow_count = 0
            self._last_position = position
            self._last_action = Action.WAIT
            return Action.WAIT

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

        def turned_heading(current, action):
            if action == Action.TURN_LEFT:
                return left_of[current]
            if action == Action.TURN_RIGHT:
                return right_of[current]
            return current

        blocked_forward = (
            self._last_action == Action.FORWARD
            and self._last_position is not None
            and position == self._last_position
        )

        x, y = position
        goal_x, goal_y = goal
        dx = goal_x - x
        dy = goal_y - y

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

        if not preferred:
            self._mode = "goal"
            self._follow_count = 0
            self._last_position = position
            self._last_action = Action.WAIT
            return Action.WAIT

        primary = preferred[0]
        if len(preferred) > 1:
            secondary = preferred[1]
        else:
            secondary = opposite_of[primary]

        def turn_toward(current, target):
            if left_of[current] == target:
                return Action.TURN_LEFT
            if right_of[current] == target:
                return Action.TURN_RIGHT
            if opposite_of[current] == target:
                return Action.TURN_LEFT
            return Action.TURN_LEFT

        def toward_goal(h):
            if dx > 0 and h == Heading.E:
                return True
            if dx < 0 and h == Heading.W:
                return True
            if dy > 0 and h == Heading.S:
                return True
            if dy < 0 and h == Heading.N:
                return True
            return False

        action = Action.WAIT

        if self._mode == "goal":
            if blocked_forward:
                self._mode = "follow"
                self._follow_count = 0
                left_heading = left_of[heading]
                right_heading = right_of[heading]
                if left_heading == secondary:
                    self._follow_turn = Action.TURN_LEFT
                elif right_heading == secondary:
                    self._follow_turn = Action.TURN_RIGHT
                else:
                    self._follow_turn = Action.TURN_LEFT
                action = self._follow_turn
            elif heading == primary:
                action = Action.FORWARD
            else:
                action = turn_toward(heading, primary)
        else:
            if blocked_forward:
                self._follow_count += 1
                action = self._follow_turn
            elif self._last_action in (Action.TURN_LEFT, Action.TURN_RIGHT):
                self._follow_count += 1
                action = Action.FORWARD
            elif toward_goal(heading):
                self._mode = "goal"
                self._follow_count = 0
                action = Action.FORWARD
            else:
                next_heading = turned_heading(heading, self._follow_turn)
                if toward_goal(next_heading):
                    self._mode = "goal"
                    self._follow_count = 0
                else:
                    self._follow_count += 1
                action = self._follow_turn

        self._last_position = position
        self._last_action = action
        return action
