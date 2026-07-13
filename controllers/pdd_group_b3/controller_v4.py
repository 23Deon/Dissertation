from gridbot.sim.actions import Action, Heading

class Controller:
    def __init__(self):
        self.visited = set()
        self.last_action = None
        self.turn_bias = Action.TURN_LEFT  # consistent bias helps avoid oscillation

    def act(self, observation) -> Action:
        x, y = observation.position
        gx, gy = observation.goal
        heading = observation.heading

        if (x, y) == (gx, gy):
            return Action.WAIT

        blocked = self._is_blocked(observation)
        self.visited.add((x, y))

        dx = gx - x
        dy = gy - y

        preferred = self._preferred_heading(dx, dy)

        # 1. If facing goal direction, only move if safe
        if heading == preferred:
            if not blocked:
                return Action.FORWARD
            else:
                return self._safe_turn()

        # 2. If forward is safe AND reduces distance, take it
        if not blocked and self._reduces_distance(heading, dx, dy):
            return Action.FORWARD

        # 3. Try turning toward goal
        turn = self._turn_toward(heading, preferred)

        # Avoid immediate oscillation (left-right-left-right)
        if self._is_opposite_turn(turn, self.last_action):
            turn = self.turn_bias

        self.last_action = turn
        return turn

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
            return self.turn_bias

    def _safe_turn(self):
        # When blocked, prefer consistent turning to avoid collision loops
        turn = self.turn_bias
        self.turn_bias = Action.TURN_RIGHT if self.turn_bias == Action.TURN_LEFT else Action.TURN_LEFT
        self.last_action = turn
        return turn

    def _is_opposite_turn(self, a, b):
        return (a == Action.TURN_LEFT and b == Action.TURN_RIGHT) or \
               (a == Action.TURN_RIGHT and b == Action.TURN_LEFT)
