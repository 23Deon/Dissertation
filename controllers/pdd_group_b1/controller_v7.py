from gridbot.sim.actions import Action, Heading


class Controller:
    def __init__(self):
        # Deterministic axis priority: alternate between X and Y for safer detours
        self.axis_priority = "X"
        # Simple step-based guard to avoid repeating risky turns
        self.last_turn = None

    def act(self, observation) -> Action:
        pos = observation.position
        heading = observation.heading
        goal = observation.goal

        # Already at goal
        if pos == goal:
            return Action.WAIT

        dx = goal[0] - pos[0]
        dy = goal[1] - pos[1]

        # Determine movement axis order
        if self.axis_priority == "X":
            primary = Heading.E if dx > 0 else Heading.W
            secondary = Heading.S if dy > 0 else Heading.N
        else:
            primary = Heading.S if dy > 0 else Heading.N
            secondary = Heading.E if dx > 0 else Heading.W

        # Simple guard: if last turn was same as desired, pick alternative axis
        if self.last_turn == primary:
            desired = secondary
        else:
            desired = primary

        # Align heading
        if heading == desired:
            return Action.FORWARD
        else:
            turn = self._turn_towards(heading, desired)
            if turn in (Action.TURN_LEFT, Action.TURN_RIGHT):
                self.last_turn = desired
            else:
                self.last_turn = None
            return turn

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
