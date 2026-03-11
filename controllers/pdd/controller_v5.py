''' Follow up Prompt:
Improve the controller so it minimizes unnecessary turning and reaches the goal efficiently.
Keep deterministic behaviour.
Return only the Python code.
'''     

from gridbot.sim.actions import Action, Heading


class Controller:
    def act(self, observation) -> Action:
        x, y = observation.position
        gx, gy = observation.goal
        heading = observation.heading

        if (x, y) == (gx, gy):
            return Action.WAIT

        dx = gx - x
        dy = gy - y

        left_turn = {
            Heading.N: Heading.W,
            Heading.W: Heading.S,
            Heading.S: Heading.E,
            Heading.E: Heading.N,
        }

        right_turn = {
            Heading.N: Heading.E,
            Heading.E: Heading.S,
            Heading.S: Heading.W,
            Heading.W: Heading.N,
        }

        opposite = {
            Heading.N: Heading.S,
            Heading.S: Heading.N,
            Heading.E: Heading.W,
            Heading.W: Heading.E,
        }

        def heading_for_axis(delta_x: int, delta_y: int):
            options = []
            if delta_x > 0:
                options.append(Heading.E)
            elif delta_x < 0:
                options.append(Heading.W)

            if delta_y > 0:
                options.append(Heading.S)
            elif delta_y < 0:
                options.append(Heading.N)

            return options

        def turn_cost(current: Heading, target: Heading) -> int:
            if current == target:
                return 0
            if left_turn[current] == target or right_turn[current] == target:
                return 1
            return 2

        candidate_headings = heading_for_axis(dx, dy)

        # Prefer the move that requires the least turning.
        # Deterministic tie-break:
        # 1) lower turn cost
        # 2) larger remaining distance reduced on that axis
        # 3) fixed heading order N, E, S, W
        heading_priority = {
            Heading.N: 0,
            Heading.E: 1,
            Heading.S: 2,
            Heading.W: 3,
        }

        def axis_distance(target: Heading) -> int:
            if target in (Heading.E, Heading.W):
                return abs(dx)
            return abs(dy)

        desired_heading = min(
            candidate_headings,
            key=lambda h: (
                turn_cost(heading, h),
                -axis_distance(h),
                heading_priority[h],
            ),
        )

        if heading == desired_heading:
            return Action.FORWARD

        if left_turn[heading] == desired_heading:
            return Action.TURN_LEFT

        if right_turn[heading] == desired_heading:
            return Action.TURN_RIGHT

        # Opposite direction: deterministically choose left.
        if opposite[heading] == desired_heading:
            return Action.TURN_LEFT

        return Action.WAIT