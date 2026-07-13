from gridbot.sim.actions import Action, Heading


class Controller:
    def __init__(self):
        # Track axis preference: "X" or "Y" for deterministic detour
        self.axis_priority = "X"

    def act(self, observation) -> Action:
        pos = observation.position
        heading = observation.heading
        goal = observation.goal

        # Already at goal
        if pos == goal:
            return Action.WAIT

        dx = goal[0] - pos[0]
        dy = goal[1] - pos[1]

        # Choose movement axis based on deterministic priority
        if self.axis_priority == "X":
            primary = Heading.E if dx > 0 else Heading.W
            secondary = Heading.S if dy > 0 else Heading.N
        else:
            primary = Heading.S if dy > 0 else Heading.N
            secondary = Heading.E if dx > 0 else Heading.W

        # Try to move along primary axis first
        if heading == primary:
            return Action.FORWARD
        elif heading == secondary:
            return Action.FORWARD
        else:
            # Determine turn direction to primary axis
            return self._turn_towards(heading, primary)

    def _turn_towards(self, current: Heading, target: Heading) -> Action:
        order = [Heading.N, Heading.E, Heading.S, Heading.W]
        ci = order.index(current)
        ti = order.index(target)
        diff = (ti - ci) % 4
        if diff == 1:
            return Action.TURN_RIGHT
        elif diff == 2:
            # 180-degree turn, arbitrary choose right
            return Action.TURN_RIGHT
        elif diff == 3:
            return Action.TURN_LEFT
        else:
            return Action.FORWARD  # Already aligned
