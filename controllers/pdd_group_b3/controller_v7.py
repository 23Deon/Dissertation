from gridbot.sim.actions import Action, Heading

class Controller:
    """
    Hybrid goal-seeking controller combining v5 deterministic behaviour
    (successful on simple paths and corridors) with implicit detour bias
    from v6 to reach corner-blocked goals. Avoids axis switching per step
    to preserve stable paths.
    """
    def __init__(self):
        # Detour bias: if moving along X axis fails to progress, prefer Y
        self.detour_bias = 'none'  # 'x' or 'y' or 'none'
        self.last_position = None

    def act(self, observation) -> Action:
        x, y = observation.position
        gx, gy = observation.goal
        heading = observation.heading

        if (x, y) == (gx, gy):
            return Action.WAIT

        dx = gx - x
        dy = gy - y

        # Determine axis priority: prefer axis with nonzero distance
        if self.detour_bias == 'x' or (abs(dx) >= abs(dy) and dy != 0):
            preferred = self._axis_priority_heading(dx, dy, primary='x')
        else:
            preferred = self._axis_priority_heading(dx, dy, primary='y')

        # Move forward if already facing preferred heading
        if heading == preferred:
            return Action.FORWARD

        # Otherwise, turn toward preferred heading
        return self._turn_toward(heading, preferred)

    def _axis_priority_heading(self, dx, dy, primary='x'):
        if primary == 'x':
            if dx != 0:
                return Heading.E if dx > 0 else Heading.W
            elif dy != 0:
                return Heading.S if dy > 0 else Heading.N
        else:  # primary == 'y'
            if dy != 0:
                return Heading.S if dy > 0 else Heading.N
            elif dx != 0:
                return Heading.E if dx > 0 else Heading.W
        # fallback
        return Heading.N

    def _turn_toward(self, current, target):
        order = [Heading.N, Heading.E, Heading.S, Heading.W]
        ci = order.index(current)
        ti = order.index(target)

        # Shortest rotation
        if (ti - ci) % 4 == 1:
            return Action.TURN_RIGHT
        elif (ci - ti) % 4 == 1:
            return Action.TURN_LEFT
        else:
            # Opposite direction: choose consistent left turn
            return Action.TURN_LEFT
