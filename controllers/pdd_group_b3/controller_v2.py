from gridbot.sim.actions import Action, Heading

class Controller:
    def __init__(self):
        self.last_turn = Action.TURN_LEFT

    def act(self, observation) -> Action:
        x, y = observation.position
        gx, gy = observation.goal
        heading = observation.heading

        dx = gx - x
        dy = gy - y

        # If at goal, do nothing
        if dx == 0 and dy == 0:
            return Action.WAIT

        preferred = self._preferred_heading(dx, dy)

        # If facing preferred direction, try to move forward
        if heading == preferred:
            if not self._is_blocked(observation):
                return Action.FORWARD
            else:
                return self._alternate_turn()

        # If forward is free and roughly toward goal, allow slight flexibility
        if not self._is_blocked(observation):
            if self._heading_reduces_distance(heading, dx, dy):
                return Action.FORWARD

        # Otherwise turn toward preferred direction
        return self._turn_toward(heading, preferred)

    def _is_blocked(self, observation):
        # Handle different possible attribute names safely
        return getattr(observation, "front_blocked",
               getattr(observation, "blocked",
               getattr(observation, "front_is_blocked", False)))

    def _preferred_heading(self, dx, dy):
        # Prefer axis with larger distance
        if abs(dx) > abs(dy):
            return Heading.E if dx > 0 else Heading.W
        else:
            return Heading.S if dy > 0 else Heading.N

    def _heading_reduces_distance(self, heading, dx, dy):
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
            return self._alternate_turn()

    def _alternate_turn(self):
        if self.last_turn == Action.TURN_LEFT:
            self.last_turn = Action.TURN_RIGHT
        else:
            self.last_turn = Action.TURN_LEFT
        return self.last_turn
