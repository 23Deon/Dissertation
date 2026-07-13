from gridbot.sim.actions import Action, Heading


class Controller:
    def act(self, observation) -> Action:
        if not hasattr(self, "_mode"):
            self._mode = "goal"
            self._follow_turn = Action.TURN_LEFT
            self._follow_count = 0
            self._last_position = None

        position = observation.position
        heading = observation.heading
        goal = observation.goal
        front_blocked = observation.front_blocked

        if position == goal:
            self._mode = "goal"
            self._follow_count = 0
            self._last_position = position
            return Action.WAIT

        x, y = position
        goal_x, goal_y = goal
        dx = goal_x - x
        dy = goal_y - y

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

        def turn_toward(current, target):
            if left_of[current] == target:
                return Action.TURN_LEFT
            if right_of[current] == target:
                return Action.TURN_RIGHT
            if opposite_of[current] == target:
                return Action.TURN_LEFT
            return Action.TURN_LEFT

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
            return Action.WAIT

        primary = preferred[0]

        def approaching_goal(h):
            if dx > 0 and h == Heading.E:
                return True
            if dx < 0 and h == Heading.W:
                return True
            if dy > 0 and h == Heading.S:
                return True
            if dy < 0 and h == Heading.N:
                return True
            return False

        if self._mode == "follow":
            if heading == primary and not front_blocked:
                self._mode = "goal"
                self._follow_count = 0
                self._last_position = position
                return Action.FORWARD

            if approaching_goal(heading) and not front_blocked and self._follow_count >= 2:
                self._mode = "goal"
                self._follow_count = 0
                self._last_position = position
                return Action.FORWARD

            if front_blocked:
                self._follow_count += 1
                self._last_position = position
                return self._follow_turn

            self._follow_count += 1
            self._last_position = position
            return Action.FORWARD

        if heading == primary:
            if not front_blocked:
                self._last_position = position
                return Action.FORWARD
            self._mode = "follow"
            self._follow_count = 0
            if len(preferred) > 1:
                secondary = preferred[1]
            else:
                secondary = opposite_of[primary]
            left_heading = left_of[heading]
            if left_heading == secondary:
                self._follow_turn = Action.TURN_LEFT
                self._last_position = position
                return Action.TURN_LEFT
            self._follow_turn = Action.TURN_RIGHT
            self._last_position = position
            return Action.TURN_RIGHT

        action = turn_toward(heading, primary)
        self._last_position = position
        if action == Action.FORWARD:
            if front_blocked:
                return Action.TURN_LEFT
            return Action.FORWARD
        return action
