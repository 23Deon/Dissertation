from gridbot.sim.actions import Action, Heading

class Controller:
    """
    Improved deterministic goal-seeking controller with implicit detour bias.
    Does not rely on obstacle sensing. Preserves successful behaviors on
    simple paths while trying to avoid early collisions by alternating axis priority.
    """
    def __init__(self):
        # Alternate axis priority to implicitly detour around obstacles
        self.alternate_axis = True  # True: prioritize X first, False: prioritize Y first
        self.step_count = 0

    def act(self, observation) -> Action:
        x, y = observation.position
        gx, gy = observation.goal
        heading = observation.heading

        self.step_count += 1

        if (x, y) == (gx, gy):
            return Action.WAIT

        dx = gx - x
        dy = gy - y

        # Switch axis priority every 3 steps to implicitly try detours
        if self.step_count % 3 == 0:
            self.alternate_axis = not self.alternate_axis

        # Determine preferred heading based on axis priority
        if self.alternate_axis:
            preferred = self._axis_priority_heading(dx, dy, primary='x')
        else:
            preferred = self._axis_priority_heading(dx, dy, primary='y')

        # If already facing preferred heading, move forward
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

        # Choose shortest rotation direction
        if (ti - ci) % 4 == 1:
            return Action.TURN_RIGHT
        elif (ci - ti) % 4 == 1:
            return Action.TURN_LEFT
        else:
            # Opposite direction: choose consistent left turn
            return Action.TURN_LEFT
