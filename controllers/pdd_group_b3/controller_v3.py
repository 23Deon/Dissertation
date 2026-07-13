from gridbot.sim.actions import Action, Heading

class Controller:
    def __init__(self):
        self.mode = "GOAL"  # or "WALL"
        self.wall_side = Action.TURN_LEFT  # follow wall on this side
        self.last_positions = []

    def act(self, observation) -> Action:
        x, y = observation.position
        gx, gy = observation.goal
        heading = observation.heading

        dx = gx - x
        dy = gy - y

        if dx == 0 and dy == 0:
            return Action.WAIT

        blocked = self._is_blocked(observation)

        # Detect loops: if stuck revisiting same positions, switch mode
        self.last_positions.append((x, y))
        if len(self.last_positions) > 6:
            self.last_positions.pop(0)
            if len(set(self.last_positions)) <= 2:
                self.mode = "WALL"

        preferred = self._preferred_heading(dx, dy)

        # Try goal-seeking mode
        if self.mode == "GOAL":
            if heading == preferred:
                if not blocked:
                    return Action.FORWARD
                else:
                    self.mode = "WALL"
                    return self._turn(self.wall_side)

            # If forward is safe and reduces distance, go
            if not blocked and self._reduces_distance(heading, dx, dy):
                return Action.FORWARD

            return self._turn_toward(heading, preferred)

        # Wall-following mode
        if self.mode == "WALL":
            # If we can face goal direction again, switch back
            if heading == preferred and not blocked:
                self.mode = "GOAL"
                return Action.FORWARD

            # Try to keep wall on chosen side
            turn_dir = self.wall_side
            check_heading = self._apply_turn(heading, turn_dir)

            if not self._would_be_blocked(observation, check_heading):
                return turn_dir

            if not blocked:
                return Action.FORWARD

            # Otherwise turn opposite
            return self._turn(self._opposite_turn(turn_dir))

        return Action.WAIT

    def _is_blocked(self, observation):
        return getattr(observation, "front_blocked",
               getattr(observation, "blocked",
               getattr(observation, "front_is_blocked", False)))

    def _preferred_heading(self, dx, dy):
        if abs(dx) > abs(dy):
            return Heading.E if dx > 0 else Heading.W
        else:
            return Heading.S if dy > 0 else Heading.N

    def _reduces_distance(self, heading, dx, dy):
        if heading == Heading.N:
            return dy < 0
        if heading == Heading.S:
            return dy > 0
        if heading == Heading.E:
            return dx > 0
        if heading == Heading.W:
            return dx < 0
        return False

    def _turn_toward(self, current, target):
        order = [Heading.N, Heading.E, Heading.S, Heading.W]
        ci = order.index(current)
        ti = order.index(target)

        if (ti - ci) % 4 == 1:
            return Action.TURN_RIGHT
        elif (ci - ti) % 4 == 1:
            return Action.TURN_LEFT
        else:
            return self._turn(self.wall_side)

    def _turn(self, direction):
        return direction

    def _opposite_turn(self, turn):
        return Action.TURN_RIGHT if turn == Action.TURN_LEFT else Action.TURN_LEFT

    def _apply_turn(self, heading, turn):
        order = [Heading.N, Heading.E, Heading.S, Heading.W]
        idx = order.index(heading)
        if turn == Action.TURN_LEFT:
            return order[(idx - 1) % 4]
        else:
            return order[(idx + 1) % 4]

    def _would_be_blocked(self, observation, new_heading):
        # We cannot truly see sideways, so assume unknown = blocked only if forward is blocked and same heading
        if new_heading == observation.heading:
            return self._is_blocked(observation)
        return False
