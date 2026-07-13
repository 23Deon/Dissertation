from gridbot.sim.actions import Action, Heading

class Controller:
    """
    Deterministic goal-seeking controller with stable axis-priority:
    - X-axis first if horizontal distance is nonzero, else Y-axis.
    - This preserves simple L-shaped paths (scenario 3) and straight corridors (scenario 6).
    - Always moves toward goal along preferred axis, turning consistently if misaligned.
    - No reliance on obstacle-sensing fields; only position, heading, and goal.
    """
    def __init__(self):
        pass

    def act(self, observation) -> Action:
        x, y = observation.position
        gx, gy = observation.goal
        heading = observation.heading

        if (x, y) == (gx, gy):
            return Action.WAIT

        dx = gx - x
        dy = gy - y

        # Deterministic axis priority: X first if horizontal distance exists
        if dx != 0:
            preferred = Heading.E if dx > 0 else Heading.W
        elif dy != 0:
            preferred = Heading.S if dy > 0 else Heading.N
        else:
            preferred = heading  # fallback

        # Move forward if already facing preferred heading
        if heading == preferred:
            return Action.FORWARD

        # Otherwise, turn toward preferred heading
        return self._turn_toward(heading, preferred)

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
            # Opposite direction: consistent left turn
            return Action.TURN_LEFT
