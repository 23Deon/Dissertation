from gridbot.sim.actions import Action, Heading


class Controller:
    def act(self, observation) -> Action:
        x, y = observation.position
        gx, gy = observation.goal
        heading = observation.heading

        # If already at goal, do nothing
        if (x, y) == (gx, gy):
            return Action.WAIT

        # Determine desired direction
        dx = gx - x
        dy = gy - y

        if dx != 0:
            desired = Heading.E if dx > 0 else Heading.W
        else:
            desired = Heading.N if dy > 0 else Heading.S

        # If already facing the right direction, move forward
        if heading == desired:
            return Action.FORWARD

        # Define turning logic (clockwise order)
        order = [Heading.N, Heading.E, Heading.S, Heading.W]
        current_idx = order.index(heading)
        desired_idx = order.index(desired)

        # Compute shortest turn direction
        right_turns = (desired_idx - current_idx) % 4
        left_turns = (current_idx - desired_idx) % 4

        if right_turns <= left_turns:
            return Action.TURN_RIGHT
        else:
            return Action.TURN_LEFT
