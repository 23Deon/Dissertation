from gridbot.sim.actions import Action, Heading


class Controller:
    def act(self, observation) -> Action:
        def left_of(heading):
            if heading == Heading.N:
                return Heading.W
            if heading == Heading.W:
                return Heading.S
            if heading == Heading.S:
                return Heading.E
            return Heading.N

        def right_of(heading):
            if heading == Heading.N:
                return Heading.E
            if heading == Heading.E:
                return Heading.S
            if heading == Heading.S:
                return Heading.W
            return Heading.N

        def delta(heading):
            if heading == Heading.N:
                return (0, -1)
            if heading == Heading.E:
                return (1, 0)
            if heading == Heading.S:
                return (0, 1)
            return (-1, 0)

        def next_position(position, heading):
            dx, dy = delta(heading)
            return (position[0] + dx, position[1] + dy)

        def manhattan(a, b):
            return abs(a[0] - b[0]) + abs(a[1] - b[1])

        def preferred_headings(position, goal):
            dx = goal[0] - position[0]
            dy = goal[1] - position[1]

            ordered = []

            if abs(dx) >= abs(dy):
                if dx > 0:
                    ordered.append(Heading.E)
                elif dx < 0:
                    ordered.append(Heading.W)

                if dy > 0:
                    ordered.append(Heading.S)
                elif dy < 0:
                    ordered.append(Heading.N)
            else:
                if dy > 0:
                    ordered.append(Heading.S)
                elif dy < 0:
                    ordered.append(Heading.N)

                if dx > 0:
                    ordered.append(Heading.E)
                elif dx < 0:
                    ordered.append(Heading.W)

            for h in (Heading.N, Heading.E, Heading.S, Heading.W):
                if h not in ordered:
                    ordered.append(h)

            return ordered

        def turn_toward(current, target):
            if current == target:
                return Action.WAIT
            if left_of(current) == target:
                return Action.TURN_LEFT
            if right_of(current) == target:
                return Action.TURN_RIGHT
            return Action.TURN_RIGHT

        def choose_follow_side(position, heading, goal):
            left_heading = left_of(heading)
            right_heading = right_of(heading)

            left_dist = manhattan(next_position(position, left_heading), goal)
            right_dist = manhattan(next_position(position, right_heading), goal)

            if left_dist < right_dist:
                return "left"
            if right_dist < left_dist:
                return "right"

            preferred = preferred_headings(position, goal)
            if preferred[0] == left_heading or preferred[1] == left_heading:
                return "left"
            if preferred[0] == right_heading or preferred[1] == right_heading:
                return "right"

            return self._last_follow_side

        if not hasattr(self, "_mode"):
            self._mode = "greedy"
            self._prev_position = None
            self._last_action = None
            self._follow_side = "right"
            self._last_follow_side = "right"
            self._follow_entry_dist = 0
            self._follow_best_dist = 0
            self._follow_commit = 0
            self._follow_progress_steps = 0
            self._follow_turns = 0

        position = observation.position
        heading = observation.heading
        goal = observation.goal

        if position == goal:
            self._mode = "greedy"
            self._prev_position = position
            self._last_action = Action.WAIT
            self._follow_commit = 0
            self._follow_progress_steps = 0
            self._follow_turns = 0
            return Action.WAIT

        current_dist = manhattan(position, goal)
        preferred = preferred_headings(position, goal)
        primary = preferred[0]

        failed_forward = (
            self._last_action == Action.FORWARD
            and self._prev_position == position
        )
        moved = (
            self._prev_position is not None
            and self._prev_position != position
        )

        if self._mode == "follow":
            if moved and self._last_action == Action.FORWARD:
                self._follow_progress_steps += 1
                if current_dist < self._follow_best_dist:
                    self._follow_best_dist = current_dist
                if self._follow_commit > 0:
                    self._follow_commit -= 1

            if failed_forward:
                self._follow_turns += 1
                action = Action.TURN_LEFT if self._follow_side == "left" else Action.TURN_RIGHT
                self._prev_position = position
                self._last_action = action
                return action

            if self._last_action == Action.TURN_LEFT or self._last_action == Action.TURN_RIGHT:
                action = Action.FORWARD
                self._prev_position = position
                self._last_action = action
                return action

            if (
                self._follow_commit == 0
                and current_dist < self._follow_entry_dist
                and current_dist <= self._follow_best_dist
                and heading == primary
            ):
                self._mode = "greedy"
                self._follow_progress_steps = 0
                self._follow_turns = 0
                action = Action.FORWARD
                self._prev_position = position
                self._last_action = action
                return action

            action = Action.FORWARD
            self._prev_position = position
            self._last_action = action
            return action

        if failed_forward:
            self._mode = "follow"
            self._follow_side = choose_follow_side(position, heading, goal)
            self._last_follow_side = self._follow_side
            self._follow_entry_dist = current_dist
            self._follow_best_dist = current_dist
            self._follow_commit = 4
            self._follow_progress_steps = 0
            self._follow_turns = 0

            action = Action.TURN_LEFT if self._follow_side == "left" else Action.TURN_RIGHT
            self._prev_position = position
            self._last_action = action
            return action

        if heading == primary:
            action = Action.FORWARD
        else:
            action = turn_toward(heading, primary)
            if action == Action.WAIT:
                action = Action.FORWARD

        self._prev_position = position
        self._last_action = action
        return action
