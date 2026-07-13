from gridbot.sim.actions import Action, Heading


class Controller:
    def act(self, observation) -> Action:
        if not hasattr(self, "_mode"):
            self._mode = 0

        x, y = observation.position
        goal_x, goal_y = observation.goal
        heading = observation.heading
        front_blocked = observation.front_blocked

        if (x, y) == (goal_x, goal_y):
            self._mode = 0
            return Action.WAIT

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
            if target is None or current == target:
                return Action.WAIT
            if right_of[current] == target:
                return Action.TURN_RIGHT
            if left_of[current] == target:
                return Action.TURN_LEFT
            return Action.TURN_RIGHT

        if self._mode == 1:
            if heading in preferred and not front_blocked:
                self._mode = 0
                return Action.FORWARD
            if front_blocked:
                return Action.TURN_RIGHT
            return Action.FORWARD

        if heading in preferred:
            if not front_blocked:
                return Action.FORWARD
            self._mode = 1
            return Action.TURN_RIGHT

        for target in preferred:
            if target == heading:
                if not front_blocked:
                    return Action.FORWARD
                self._mode = 1
                return Action.TURN_RIGHT

            action = turn_toward(heading, target)
            if action == Action.TURN_LEFT or action == Action.TURN_RIGHT:
                return action

        if front_blocked:
            return Action.TURN_RIGHT
        return Action.FORWARD
