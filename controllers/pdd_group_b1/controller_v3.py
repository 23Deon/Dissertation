from gridbot.sim.actions import Action, Heading


class Controller:
    def __init__(self):
        # Memory for simple bug-like navigation
        self.mode = "GOAL"  # GOAL or FOLLOW
        self.follow_dir = "RIGHT"  # wall-follow preference
        self.hit_point = None
        self.visited = set()

    def act(self, observation) -> Action:
        pos = observation.position
        heading = observation.heading
        goal = observation.goal
        front_blocked = getattr(observation, "front_blocked", False)

        self.visited.add((pos, heading))

        # If at goal (safety)
        if pos == goal:
            return Action.WAIT

        desired = self._desired_heading(goal, pos)

        if self.mode == "GOAL":
            if heading == desired:
                if not front_blocked:
                    return Action.FORWARD
                else:
                    # switch to wall-follow
                    self.mode = "FOLLOW"
                    self.hit_point = pos
                    return Action.TURN_RIGHT
            else:
                return self._turn_towards(heading, desired)

        # FOLLOW mode (right-hand wall follower)
        # Try to leave wall-follow if aligned and closer to goal
        if heading == desired and not front_blocked:
            if self._closer_to_goal(pos, self.hit_point, goal):
                self.mode = "GOAL"
                return Action.FORWARD

        # Wall-following logic (safe, no blind forward into obstacle)
        if front_blocked:
            return Action.TURN_LEFT

        # Prefer turning right if it might open space
        right_heading = self._turn_right_heading(heading)
        if (pos, right_heading) not in self.visited:
            return Action.TURN_RIGHT

        return Action.FORWARD

    def _desired_heading(self, goal, pos) -> Heading:
        dx = goal[0] - pos[0]
        dy = goal[1] - pos[1]

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

    def _manhattan(self, a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def _closer_to_goal(self, pos, hit_point, goal):
        if hit_point is None:
            return True
        return self._manhattan(pos, goal) < self._manhattan(hit_point, goal)
