from gridbot.sim.actions import Action, Heading


class Controller:
    def act(self, observation) -> Action:
        x, y = observation.position
        gx, gy = observation.goal
        heading = observation.heading

        # Compute direction to goal
        dx = gx - x
        dy = gy - y

        # If already at goal, wait
        if dx == 0 and dy == 0:
            return Action.WAIT

        # Decide desired heading
        if dx > 0:
            desired = Heading.E
        elif dx < 0:
            desired = Heading.W
        elif dy > 0:
            desired = Heading.N
        else:  # dy < 0
            desired = Heading.S

        # If facing the right direction, move forward
        if heading == desired:
            return Action.FORWARD

        # Otherwise, decide shortest turn
        if self._turn_left(heading) == desired:
            return Action.TURN_LEFT
        else:
            return Action.TURN_RIGHT

    def _turn_left(self, heading):
        return {
            Heading.N: Heading.W,
            Heading.W: Heading.S,
            Heading.S: Heading.E,
            Heading.E: Heading.N,
        }[heading]

    def _turn_right(self, heading):
        return {
            Heading.N: Heading.E,
            Heading.E: Heading.S,
            Heading.S: Heading.W,
            Heading.W: Heading.N,
        }[heading]
