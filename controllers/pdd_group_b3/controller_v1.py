from gridbot.sim.actions import Action, Heading

class Controller:
    def __init__(self):
        # Track last turn direction to avoid spinning in place
        self.last_turn = Action.TURN_LEFT

    def act(self, observation) -> Action:
        x, y = observation.position
        gx, gy = observation.goal
        heading = observation.heading

        dx = gx - x
        dy = gy - y

        # Determine preferred heading toward the goal
        preferred = self._preferred_heading(dx, dy)

        # If already facing preferred direction
        if heading == preferred:
            if not observation.front_blocked:
                return Action.FORWARD
            else:
                # Obstacle ahead: turn (alternate directions to avoid loops)
                return self._alternate_turn()

        # Otherwise, rotate toward preferred heading
        return self._turn_toward(heading, preferred)

    def _preferred_heading(self, dx, dy):
        # Prioritize horizontal vs vertical based on larger distance
        if abs(dx) > abs(dy):
            return Heading.E if dx > 0 else Heading.W
        else:
            return Heading.S if dy > 0 else Heading.N

    def _turn_toward(self, current, target):
        # Define clockwise order
        order = [Heading.N, Heading.E, Heading.S, Heading.W]
        ci = order.index(current)
        ti = order.index(target)

        # Compute shortest turn direction
        if (ti - ci) % 4 == 1:
            return Action.TURN_RIGHT
        elif (ci - ti) % 4 == 1:
            return Action.TURN_LEFT
        else:
            # If opposite direction, choose a consistent turn
            return Action.TURN_LEFT

    def _alternate_turn(self):
        # Alternate turns to reduce chance of getting stuck
        if self.last_turn == Action.TURN_LEFT:
            self.last_turn = Action.TURN_RIGHT
        else:
            self.last_turn = Action.TURN_LEFT
        return self.last_turn
