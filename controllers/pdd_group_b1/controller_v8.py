from gridbot.sim.actions import Action, Heading


class Controller:
    def __init__(self):
        # Fixed deterministic axis order to avoid wandering: try X first, then Y
        self.primary_axis = "X"

    def act(self, observation) -> Action:
        pos = observation.position
        heading = observation.heading
        goal = observation.goal

        # Already at goal
        if pos == goal:
            return Action.WAIT

        dx = goal[0] - pos[0]
        dy = goal[1] - pos[1]

        # Determine movement heading based on fixed axis order
        if self.primary_axis == "X":
            if dx != 0:
                desired = Heading.E if dx > 0 else Heading.W
            else:
                desired = Heading.S if dy > 0 else Heading.N
        else:
            if dy != 0:
                desired = Heading.S if dy > 0 else Heading.N
            else:
                desired = Heading.E if dx > 0 else Heading.W

        # Align heading
        if heading == desired:
            return Action.FORWARD
        else:
            return self._turn_towards(heading, desired)

    def _turn_towards(self, current: Heading, target: Heading) -> Action:
        order = [Heading.N, Heading.E, Heading.S, Heading.W]
        ci = order.index(current)
        ti = order.index(target)
        diff = (ti - ci) % 4
        if diff == 1:
            return Action.TURN_RIGHT
        elif diff == 2:
            # 180-degree turn, choose right for determinism
            return Action.TURN_RIGHT
        elif diff == 3:
            return Action.TURN_LEFT
        else:
            return Action.FORWARD
