from gridbot.sim.actions import Action, Heading


class Controller:
    def __init__(self):
        # Wall-following state
        self.following_wall = False
        self.goal_heading = None

    def act(self, observation) -> Action:
        pos = observation.position
        heading = observation.heading
        goal = observation.goal

        # Robust front_blocked handling (fix for previous crash)
        front_blocked = getattr(observation, "front_blocked", False)

        # Compute goal-directed heading
        dx = goal[0] - pos[0]
        dy = goal[1] - pos[1]
        desired = self._desired_heading(dx, dy)

        # If we are not currently wall-following, try greedy move
        if not self.following_wall:
            if heading == desired:
                if not front_blocked:
                    return Action.FORWARD
                else:
                    # Start wall-following
                    self.following_wall = True
                    self.goal_heading = desired
                    return Action.TURN_RIGHT
            else:
                return self._turn_towards(heading, desired)

        # Wall-following mode (right-hand rule)
        # If we realign with goal direction and path is clear → exit wall-follow
        if heading == desired and not front_blocked:
            self.following_wall = False
            return Action.FORWARD

        if front_blocked:
            return Action.TURN_LEFT
        else:
            # Try to keep wall on the right:
            # Prefer turning right if it helps exploration
            right_heading = self._turn_right_heading(heading)
            if right_heading == desired:
                return Action.TURN_RIGHT
            return Action.FORWARD

    def _desired_heading(self, dx, dy) -> Heading:
        # Bias toward reducing Manhattan distance
        if abs(dx) > abs(dy):
            return Heading.E if dx > 0 else Heading.W
        else:
            return Heading.S if dy > 0 else Heading.N

    def _turn_towards(self, current: Heading, target: Heading) -> Action:
        order = [Heading.N, Heading.E, Heading.S, Heading.W]
        ci = order.index(current)
        ti = order.index(target)

        if (ti - ci) % 4 == 1:
            return Action.TURN_RIGHT
        elif (ci - ti) % 4 == 1:
            return Action.TURN_LEFT
        else:
            return Action.TURN_RIGHT

    def _turn_right_heading(self, heading: Heading) -> Heading:
        order = [Heading.N, Heading.E, Heading.S, Heading.W]
        return order[(order.index(heading) + 1) % 4]
