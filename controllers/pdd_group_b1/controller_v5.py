from gridbot.sim.actions import Action, Heading


class Controller:
    def __init__(self):
        # Mode: "GOAL" = greedy toward goal, "FOLLOW" = obstacle avoidance
        self.mode = "GOAL"
        self.hit_point = None  # Position where obstacle encountered
        self.visited = set()   # Track visited positions with heading
        self.wall_side = "RIGHT"  # Right-hand wall following

    def act(self, observation) -> Action:
        pos = observation.position
        heading = observation.heading
        goal = observation.goal
        front_blocked = getattr(observation, "front_blocked", False)

        self.visited.add((pos, heading))

        # At goal → wait
        if pos == goal:
            return Action.WAIT

        desired_heading = self._desired_heading(pos, goal)

        if self.mode == "GOAL":
            # Facing desired direction
            if heading == desired_heading:
                if not front_blocked:
                    return Action.FORWARD
                else:
                    # Hit obstacle → switch to wall-follow
                    self.mode = "FOLLOW"
                    self.hit_point = pos
                    return Action.TURN_RIGHT
            else:
                return self._turn_towards(heading, desired_heading)

        # FOLLOW mode: wall-following
        # Exit FOLLOW if aligned with goal and closer than hit point
        if heading == desired_heading and not front_blocked:
            if self._closer_to_goal(pos, self.hit_point, goal):
                self.mode = "GOAL"
                return Action.FORWARD

        # Wall-follow behavior
        if front_blocked:
            return Action.TURN_LEFT

        # Prefer turning right if unvisited
        right_heading = self._turn_right_heading(heading)
        next_pos = self._next_position(pos, right_heading)
        if (next_pos, right_heading) not in self.visited:
            return Action.TURN_RIGHT

        # Otherwise move forward safely
        return Action.FORWARD

    def _desired_heading(self, pos, goal) -> Heading:
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

    def _next_position(self, pos, heading):
        x, y = pos
        if heading == Heading.N:
            return (x, y - 1)
        elif heading == Heading.S:
            return (x, y + 1)
        elif heading == Heading.E:
            return (x + 1, y)
        elif heading == Heading.W:
            return (x - 1, y)

    def _manhattan(self, a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def _closer_to_goal(self, pos, hit_point, goal):
        if hit_point is None:
            return True
        return self._manhattan(pos, goal) < self._manhattan(hit_point, goal)
