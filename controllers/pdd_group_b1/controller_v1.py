from gridbot.sim.actions import Action, Heading


class Controller:
    def __init__(self):
        # Used to remember if we are currently avoiding an obstacle
        self.avoiding = False

    def act(self, observation) -> Action:
        pos = observation.position
        heading = observation.heading
        goal = observation.goal
        front_blocked = observation.front_blocked

        # Compute desired direction (greedy toward goal)
        dx = goal[0] - pos[0]
        dy = goal[1] - pos[1]

        desired_heading = self._desired_heading(dx, dy)

        # If we're facing the desired direction
        if heading == desired_heading:
            if not front_blocked:
                self.avoiding = False
                return Action.FORWARD
            else:
                # Obstacle ahead → start avoiding
                self.avoiding = True
                return Action.TURN_RIGHT

        # If not facing desired direction, rotate toward it
        if not self.avoiding:
            return self._turn_towards(heading, desired_heading)

        # If avoiding obstacle, follow simple wall-following
        if front_blocked:
            return Action.TURN_RIGHT
        else:
            return Action.FORWARD

    def _desired_heading(self, dx, dy) -> Heading:
        # Prioritize horizontal vs vertical movement
        if abs(dx) > abs(dy):
            return Heading.E if dx > 0 else Heading.W
        else:
            return Heading.S if dy > 0 else Heading.N

    def _turn_towards(self, current: Heading, target: Heading) -> Action:
        order = [Heading.N, Heading.E, Heading.S, Heading.W]
        ci = order.index(current)
        ti = order.index(target)

        # Compute shortest turn direction
        if (ci - ti) % 4 == 1:
            return Action.TURN_LEFT
        else:
            return Action.TURN_RIGHT
