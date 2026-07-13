from gridbot.sim.actions import Action, Heading


class Controller:
    def act(self, observation) -> Action:
        x, y = observation.position
        gx, gy = observation.goal
        heading = observation.heading

        dx = gx - x
        dy = gy - y

        if dx == 0 and dy == 0:
            return Action.WAIT

        if dx != 0:
            desired = Heading.E if dx > 0 else Heading.W
        else:
            desired = Heading.S if dy > 0 else Heading.N

        if heading == desired:
            return Action.FORWARD

        right_turn = {
            Heading.N: Heading.E,
            Heading.E: Heading.S,
            Heading.S: Heading.W,
            Heading.W: Heading.N,
        }

        left_turn = {
            Heading.N: Heading.W,
            Heading.W: Heading.S,
            Heading.S: Heading.E,
            Heading.E: Heading.N,
        }

        if right_turn[heading] == desired:
            return Action.TURN_RIGHT

        if left_turn[heading] == desired:
            return Action.TURN_LEFT

        return Action.TURN_RIGHT
