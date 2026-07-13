from gridbot.sim.actions import Action, Heading


class Controller:
    def __init__(self):
        self._last_action = None
        self._last_position = None

        self._wf_mode = False
        self._wf_hand = None
        self._wf_entry_distance = None
        self._wf_blocked_streak = 0

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
    def _desired_heading(dx, dy):
        if dx == 0 and dy == 0:
            return None
        if abs(dx) >= abs(dy):
            if dx > 0:
                return Heading.E
            if dx < 0:
                return Heading.W
            if dy > 0:
                return Heading.S
            if dy < 0:
                return Heading.N
        else:
            if dy > 0:
                return Heading.S
            if dy < 0:
                return Heading.N
            if dx > 0:
                return Heading.E
            if dx < 0:
                return Heading.W
        return None

    def _record(self, action, pos):
        self._last_action = action
        self._last_position = pos
        return action

    def act(self, observation) -> Action:
        pos = observation.position
        heading = observation.heading
        goal = observation.goal

        px, py = pos[0], pos[1]
        gx, gy = goal[0], goal[1]

        if px == gx and py == gy:
            self._wf_mode = False
            self._wf_hand = None
            self._wf_blocked_streak = 0
            return self._record(Action.WAIT, pos)

        blocked = (
            self._last_action == Action.FORWARD
            and self._last_position is not None
            and self._last_position == pos
        )

        dx = gx - px
        dy = gy - py
        dist = abs(dx) + abs(dy)

        if self._wf_mode and dist < self._wf_entry_distance:
            self._wf_mode = False
            self._wf_hand = None
            self._wf_blocked_streak = 0

        if not self._wf_mode:
            if blocked:
                desired_now = self._desired_heading(dx, dy)
                if desired_now in (Heading.E, Heading.W):
                    if dy > 0:
                        target = Heading.S
                    elif dy < 0:
                        target = Heading.N
                    else:
                        target = Heading.S
                else:
                    if dx > 0:
                        target = Heading.E
                    elif dx < 0:
                        target = Heading.W
                    else:
                        target = Heading.E

                turn = self._turn_toward(heading, target)
                if turn is None:
                    turn = Action.TURN_RIGHT

                self._wf_hand = "left" if turn == Action.TURN_RIGHT else "right"
                self._wf_mode = True
                self._wf_entry_distance = dist
                self._wf_blocked_streak = 1
                return self._record(turn, pos)

            desired = self._desired_heading(dx, dy)
            if desired is None:
                return self._record(Action.WAIT, pos)
            if heading == desired:
                return self._record(Action.FORWARD, pos)
            turn = self._turn_toward(heading, desired)
            if turn is None:
                return self._record(Action.FORWARD, pos)
            return self._record(turn, pos)

        if blocked:
            self._wf_blocked_streak += 1
            if self._wf_blocked_streak >= 4:
                return self._record(Action.WAIT, pos)
            if self._wf_hand == "left":
                return self._record(Action.TURN_RIGHT, pos)
            return self._record(Action.TURN_LEFT, pos)

        if self._last_action == Action.FORWARD:
            self._wf_blocked_streak = 0
            if self._wf_hand == "left":
                return self._record(Action.TURN_LEFT, pos)
            return self._record(Action.TURN_RIGHT, pos)

        return self._record(Action.FORWARD, pos)
