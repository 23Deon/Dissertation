from gridbot.sim.actions import Action, Heading

class Controller:
    def __init__(self):
        self.last_turn = Action.TURN_LEFT  # used for alternating when blocked
        self.visited = set()  # track visited positions to avoid loops

    def act(self, observation) -> Action:
        x, y = observation.position
        gx, gy = observation.goal
        heading = observation.heading

        # If at goal, wait
        if (x, y) == (gx, gy):
            return Action.WAIT

        blocked = self._is_blocked(observation)
        self.visited.add((x, y))

        dx = gx - x
        dy = gy - y
        preferred_heading = self._preferred_heading(dx, dy)

        # 1. Move forward if facing goal and path is clear
        if heading == preferred_heading and not blocked:
            return Action.FORWARD

        # 2. Move forward if it reduces distance (greedy forward move)
        if not blocked and self._reduces_distance(heading, dx, dy):
            return Action.FORWARD

        # 3. Turn toward goal
        turn_action = self._turn_toward(heading, preferred_heading)

        # 4. If forward blocked, alternate turns to avoid collision loops
        if blocked:
            turn_action = self._alternate_turn()

        self.last_turn = turn_action
        return turn_action

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
            # Opposite direction: choose last turn bias
            return self.last_turn

    def _alternate_turn(self):
        # Alternate left/right to reduce chance of repeated collisions
        turn = Action.TURN_RIGHT if self.last_turn == Action.TURN_LEFT else Action.TURN_LEFT
        self.last_turn = turn
        return turn
