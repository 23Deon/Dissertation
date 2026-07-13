from gridbot.sim.actions import Action, Heading


class Controller:
    def __init__(self):
        self._last_action = None
        self._last_position = None
        self._last_heading = None
        self._wall_follow_mode = False
        self._wall_follow_steps = 0
        self._wall_follow_limit = 0
        self._blocked_count = 0

    @staticmethod
    def _desired_heading(dx, dy):
        if abs(dx) >= abs(dy):
            if dx > 0:
                return Heading.E
            if dx < 0:
                return Heading.W
            if dy > 0:
                return Heading.S
            if dy < 0:
                return Heading.N
            return None

        if dy > 0:
            return Heading.S
        if dy < 0:
            return Heading.N
        if dx > 0:
            return Heading.E
        if dx < 0:
            return Heading.W
        return None

    @staticmethod
    def _turn_toward(current, target):
        order = [Heading.N, Heading.E, Heading.S, Heading.W]
        ci = order.index(current)
        ti = order.index(target)
        diff = (ti - ci) % 4
        if diff == 0:
            return None
        if diff == 1:
            return Action.TURN_RIGHT
        if diff == 3:
            return Action.TURN_LEFT
        return Action.TURN_RIGHT

    @staticmethod
    def _left_of(heading):
        mapping = {
            Heading.N: Heading.W,
            Heading.W: Heading.S,
            Heading.S: Heading.E,
            Heading.E: Heading.N,
        }
        return mapping[heading]

    @staticmethod
    def _right_of(heading):
        mapping = {
            Heading.N: Heading.E,
            Heading.E: Heading.S,
            Heading.S: Heading.W,
            Heading.W: Heading.N,
        }
        return mapping[heading]

    def _record(self, action, position, heading):
        self._last_action = action
        self._last_position = position
        self._last_heading = heading
        return action

    def act(self, observation) -> Action:
        pos = observation.position
        heading = observation.heading
        goal = observation.goal

        px, py = pos[0], pos[1]
        gx, gy = goal[0], goal[1]

        if px == gx and py == gy:
            self._wall_follow_mode = False
            self._blocked_count = 0
            return self._record(Action.WAIT, pos, heading)

        blocked = (
            self._last_action == Action.FORWARD
            and self._last_position is not None
            and self._last_position == pos
        )

        if blocked:
            self._blocked_count += 1
        elif self._last_action == Action.FORWARD:
            self._blocked_count = 0

        dx = gx - px
        dy = gy - py

        if not self._wall_follow_mode:
            if blocked:
                self._wall_follow_mode = True
                self._wall_follow_steps = 0
                self._wall_follow_limit = 4 * (abs(dx) + abs(dy) + 4)
                turn = self._turn_toward(heading, self._right_of(heading))
                return self._record(turn, pos, heading)

            desired = self._desired_heading(dx, dy)
            if desired is None:
                return self._record(Action.WAIT, pos, heading)
            if heading == desired:
                return self._record(Action.FORWARD, pos, heading)
            turn = self._turn_toward(heading, desired)
            return self._record(turn, pos, heading)

        self._wall_follow_steps += 1
        if self._wall_follow_steps > self._wall_follow_limit:
            self._wall_follow_mode = False
            self._wall_follow_steps = 0
            self._blocked_count = 0

            desired = self._desired_heading(dx, dy)
            if desired is None:
                return self._record(Action.WAIT, pos, heading)
            if heading == desired:
                return self._record(Action.FORWARD, pos, heading)
            return self._record(self._turn_toward(heading, desired), pos, heading)

        if not blocked and self._last_action == Action.FORWARD:
            desired = self._desired_heading(dx, dy)
            if desired is not None and heading == desired:
                self._wall_follow_mode = False
                self._wall_follow_steps = 0
                self._blocked_count = 0
                return self._record(Action.FORWARD, pos, heading)

            left = self._left_of(heading)
            return self._record(self._turn_toward(heading, left), pos, heading)

        if blocked:
            if self._blocked_count >= 4:
                self._wall_follow_mode = False
                self._blocked_count = 0
                return self._record(Action.WAIT, pos, heading)
            return self._record(Action.TURN_RIGHT, pos, heading)

        return self._record(Action.FORWARD, pos, heading)
