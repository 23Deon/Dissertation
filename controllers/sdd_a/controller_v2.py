from gridbot.sim.actions import Action, Heading


class Controller:
    def act(self, observation) -> Action:
        x, y = observation.position
        goal_x, goal_y = observation.goal
        heading = observation.heading

        if (x, y) == (goal_x, goal_y):
            self._phase = 0
            self._last_position = (x, y)
            self._last_action = Action.WAIT
            return Action.WAIT

        if not hasattr(self, "_phase"):
            self._phase = 0
        if not hasattr(self, "_last_position"):
            self._last_position = (x, y)
        if not hasattr(self, "_last_action"):
            self._last_action = Action.WAIT

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

        def turn_toward(current, target):
            if current == target:
                return Action.FORWARD
            if right_of[current] == target:
                return Action.TURN_RIGHT
            if left_of[current] == target:
                return Action.TURN_LEFT
            return Action.TURN_RIGHT

        dx = goal_x - x
        dy = goal_y - y

        if abs(dx) >= abs(dy):
            primary = Heading.E if dx > 0 else Heading.W if dx < 0 else None
            secondary = Heading.S if dy > 0 else Heading.N if dy < 0 else None
        else:
            primary = Heading.S if dy > 0 else Heading.N if dy < 0 else None
            secondary = Heading.E if dx > 0 else Heading.W if dx < 0 else None

        preferred = []
        if primary is not None:
            preferred.append(primary)
        if secondary is not None and secondary != primary:
            preferred.append(secondary)

        if not preferred:
            self._phase = 0
            self._last_position = (x, y)
            self._last_action = Action.WAIT
            return Action.WAIT

        stuck_after_forward = (
            self._last_action == Action.FORWARD and self._last_position == (x, y)
        )

        if stuck_after_forward:
            if self._phase == 0:
                self._phase = 1
                action = Action.TURN_RIGHT
            elif self._phase == 1:
                self._phase = 2
                action = Action.FORWARD
            elif self._phase == 2:
                self._phase = 3
                action = Action.TURN_LEFT
            elif self._phase == 3:
                self._phase = 4
                action = Action.TURN_LEFT
            elif self._phase == 4:
                self._phase = 5
                action = Action.FORWARD
            else:
                self._phase = 0
                target = preferred[0]
                action = turn_toward(heading, target)
        else:
            if self._phase in (2, 5):
                self._phase = 0

            target = preferred[0]
            if heading == target:
                action = Action.FORWARD
            elif len(preferred) > 1 and heading == preferred[1]:
                action = Action.FORWARD
            else:
                action = turn_toward(heading, target)

        self._last_position = (x, y)
        self._last_action = action

        if action in (Action.FORWARD, Action.TURN_LEFT, Action.TURN_RIGHT, Action.WAIT):
            return action
        return Action.WAIT
