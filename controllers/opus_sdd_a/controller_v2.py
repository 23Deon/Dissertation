from gridbot.sim.actions import Action, Heading


class Controller:
    def __init__(self):
        self._last_action = None
        self._last_position = None
        self._last_heading = None

        self._wf_mode = False
        self._wf_hand = None
        self._wf_entry_distance = None
        self._wf_steps = 0
        self._wf_limit = 0
        self._wf_just_entered = False

        self._pos_history = []
        self._history_limit = 64

        self._blocked_in_wf = 0

    @staticmethod
    def _left_of(heading):
        return {
            Heading.N: Heading.W,
            Heading.W: Heading.S,
            Heading.S: Heading.E,
            Heading.E: Heading.N,
        }[heading]

    @staticmethod
    def _right_of(heading):
        return {
            Heading.N: Heading.E,
            Heading.E: Heading.S,
            Heading.S: Heading.W,
            Heading.W: Heading.N,
        }[heading]

    @staticmethod
    def _opposite(heading):
        return {
            Heading.N: Heading.S,
            Heading.S: Heading.N,
            Heading.E: Heading.W,
            Heading.W: Heading.E,
        }[heading]

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

    def _push_history(self, pos):
        self._pos_history.append(pos)
        if len(self._pos_history) > self._history_limit:
            self._pos_history.pop(0)

    def _record(self, action, pos, heading):
        self._last_action = action
        self._last_position = pos
        self._last_heading = heading
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
            self._blocked_in_wf = 0
            return self._record(Action.WAIT, pos, heading)

        blocked = (
            self._last_action == Action.FORWARD
            and self._last_position is not None
            and self._last_position == pos
        )

        if self._last_action == Action.FORWARD and not blocked:
            self._push_history(pos)

        dx = gx - px
        dy = gy - py
        dist = abs(dx) + abs(dy)

        if not self._wf_mode:
            if blocked:
                desired = self._desired_heading(dx, dy)
                hand = "right"
                if desired in (Heading.E, Heading.W):
                    if desired == Heading.E:
                        hand = "right" if dy >= 0 else "left"
                    else:
                        hand = "right" if dy <= 0 else "left"
                elif desired in (Heading.N, Heading.S):
                    if desired == Heading.S:
                        hand = "right" if dx <= 0 else "left"
                    else:
                        hand = "right" if dx >= 0 else "left"

                self._wf_mode = True
                self._wf_hand = hand
                self._wf_entry_distance = dist
                self._wf_steps = 0
                self._wf_limit = 8 * (abs(dx) + abs(dy) + 8) + 64
                self._wf_just_entered = True
                self._blocked_in_wf = 0

                if hand == "left":
                    return self._record(Action.TURN_LEFT, pos, heading)
                return self._record(Action.TURN_RIGHT, pos, heading)

            desired = self._desired_heading(dx, dy)
            if desired is None:
                return self._record(Action.WAIT, pos, heading)
            if heading == desired:
                return self._record(Action.FORWARD, pos, heading)
            turn = self._turn_toward(heading, desired)
            if turn is None:
                return self._record(Action.FORWARD, pos, heading)
            return self._record(turn, pos, heading)

        self._wf_steps += 1

        desired = self._desired_heading(dx, dy)
        if (
            not self._wf_just_entered
            and not blocked
            and self._last_action == Action.FORWARD
            and dist < self._wf_entry_distance
            and desired is not None
            and heading == desired
        ):
            self._wf_mode = False
            self._wf_hand = None
            self._blocked_in_wf = 0
            return self._record(Action.FORWARD, pos, heading)

        if self._wf_steps > self._wf_limit:
            self._wf_mode = False
            self._wf_hand = None
            self._blocked_in_wf = 0
            if desired is None:
                return self._record(Action.WAIT, pos, heading)
            if heading == desired:
                return self._record(Action.FORWARD, pos, heading)
            turn = self._turn_toward(heading, desired)
            if turn is None:
                return self._record(Action.FORWARD, pos, heading)
            return self._record(turn, pos, heading)

        self._wf_just_entered = False

        if blocked:
            self._blocked_in_wf += 1
            if self._blocked_in_wf >= 4:
                self._wf_mode = False
                self._wf_hand = None
                self._blocked_in_wf = 0
                return self._record(Action.WAIT, pos, heading)
            if self._wf_hand == "left":
                return self._record(Action.TURN_RIGHT, pos, heading)
            return self._record(Action.TURN_LEFT, pos, heading)

        self._blocked_in_wf = 0

        if self._last_action == Action.FORWARD:
            if self._wf_hand == "left":
                return self._record(Action.TURN_LEFT, pos, heading)
            return self._record(Action.TURN_RIGHT, pos, heading)

        return self._record(Action.FORWARD, pos, heading)
