from gridbot.sim.actions import Action, Heading


class Controller:
    def __init__(self):
        self._last_position = None
        self._last_heading = None
        self._last_action = Action.WAIT
        self._blocked_edges = set()
        self._known_free = set()
        self._visit_counts = {}
        self._recent_positions = []
        self._step_count = 0

    def act(self, observation) -> Action:
        position = observation.position
        heading = observation.heading
        goal = observation.goal
        self._step_count += 1

        if self._last_position is not None and self._last_action == Action.FORWARD:
            if position == self._last_position:
                self._blocked_edges.add((self._last_position, self._last_heading))
            else:
                previous = self._last_position
                self._known_free.add((previous, self._last_heading))
                self._known_free.add((position, self._opposite(heading)))

        self._note_visit(position)

        if position == goal:
            self._last_position = position
            self._last_heading = heading
            self._last_action = Action.WAIT
            return Action.WAIT

        plan = self._plan(position, heading, goal)
        if plan:
            action = plan[0]
        else:
            target_heading = self._fallback_heading(position, heading, goal)
            action = self._turn_toward(heading, target_heading)

        self._last_position = position
        self._last_heading = heading
        self._last_action = action
        return action

    def _plan(self, start_pos, start_heading, goal):
        bounds = self._search_bounds(start_pos, goal)
        start_state = (start_pos, start_heading)
        open_list = [(self._estimate(start_pos, start_heading, goal), 0, start_state)]
        best_cost = {start_state: 0}
        parent = {}
        closed = set()

        while open_list:
            best_index = 0
            best_item = open_list[0]
            i = 1
            while i < len(open_list):
                item = open_list[i]
                if item[0] < best_item[0] or (item[0] == best_item[0] and item[1] < best_item[1]):
                    best_index = i
                    best_item = item
                i += 1

            _, cost_so_far, state = open_list.pop(best_index)
            if state in closed:
                continue
            closed.add(state)

            position, heading = state
            if position == goal:
                return self._reconstruct(parent, state)

            for action, next_state, action_cost in self._successors(position, heading, bounds):
                next_cost = cost_so_far + action_cost
                previous_best = best_cost.get(next_state)
                if previous_best is None or next_cost < previous_best:
                    best_cost[next_state] = next_cost
                    parent[next_state] = (state, action)
                    priority = next_cost + self._estimate(next_state[0], next_state[1], goal)
                    open_list.append((priority, next_cost, next_state))

        return None

    def _successors(self, position, heading, bounds):
        left_heading = self._left_of(heading)
        right_heading = self._right_of(heading)

        results = [
            (Action.TURN_LEFT, (position, left_heading), 1),
            (Action.TURN_RIGHT, (position, right_heading), 1),
        ]

        if (position, heading) not in self._blocked_edges:
            next_position = self._step(position, heading)
            if self._in_bounds(next_position, bounds):
                forward_cost = 1
                if (position, heading) not in self._known_free:
                    forward_cost += 2
                forward_cost += self._visit_counts.get(next_position, 0) * 2
                forward_cost += self._recent_count(next_position) * 2
                results.append((Action.FORWARD, (next_position, heading), forward_cost))

        return results

    def _estimate(self, position, heading, goal):
        dx = goal[0] - position[0]
        dy = goal[1] - position[1]
        manhattan = abs(dx) + abs(dy)
        target_heading = self._preferred_heading(position, goal)
        turn_penalty = self._turn_distance(heading, target_heading)
        return manhattan + turn_penalty

    def _search_bounds(self, position, goal):
        points = [position, goal]
        for pos, _ in self._blocked_edges:
            points.append(pos)
        points.extend(self._visit_counts.keys())

        min_x = points[0][0]
        max_x = points[0][0]
        min_y = points[0][1]
        max_y = points[0][1]
        for px, py in points[1:]:
            if px < min_x:
                min_x = px
            if px > max_x:
                max_x = px
            if py < min_y:
                min_y = py
            if py > max_y:
                max_y = py

        margin = 8
        blocked_seen = len(self._blocked_edges)
        if blocked_seen > 6:
            margin += 2
        if blocked_seen > 12:
            margin += 2

        return (min_x - margin, max_x + margin, min_y - margin, max_y + margin)

    def _reconstruct(self, parent, state):
        actions = []
        while state in parent:
            previous_state, action = parent[state]
            actions.append(action)
            state = previous_state
        actions.reverse()
        return actions

    def _fallback_heading(self, position, heading, goal):
        ordered = [
            self._preferred_heading(position, goal),
            self._left_of(heading),
            self._right_of(heading),
            heading,
            self._opposite(heading),
        ]
        for candidate in ordered:
            if candidate is None:
                continue
            if (position, candidate) not in self._blocked_edges:
                return candidate
        return heading

    def _preferred_heading(self, position, goal):
        dx = goal[0] - position[0]
        dy = goal[1] - position[1]

        if abs(dx) >= abs(dy):
            if dx > 0:
                return Heading.E
            if dx < 0:
                return Heading.W
            if dy > 0:
                return Heading.S
            return Heading.N

        if dy > 0:
            return Heading.S
        if dy < 0:
            return Heading.N
        if dx > 0:
            return Heading.E
        return Heading.W

    def _turn_toward(self, current, target):
        if current == target:
            return Action.FORWARD
        if self._left_of(current) == target:
            return Action.TURN_LEFT
        if self._right_of(current) == target:
            return Action.TURN_RIGHT
        return Action.TURN_LEFT

    def _turn_distance(self, current, target):
        if current == target:
            return 0
        if self._left_of(current) == target or self._right_of(current) == target:
            return 1
        return 2

    def _left_of(self, heading):
        if heading == Heading.N:
            return Heading.W
        if heading == Heading.W:
            return Heading.S
        if heading == Heading.S:
            return Heading.E
        return Heading.N

    def _right_of(self, heading):
        if heading == Heading.N:
            return Heading.E
        if heading == Heading.E:
            return Heading.S
        if heading == Heading.S:
            return Heading.W
        return Heading.N

    def _opposite(self, heading):
        if heading == Heading.N:
            return Heading.S
        if heading == Heading.S:
            return Heading.N
        if heading == Heading.E:
            return Heading.W
        return Heading.E

    def _step(self, position, heading):
        if heading == Heading.N:
            return (position[0], position[1] - 1)
        if heading == Heading.S:
            return (position[0], position[1] + 1)
        if heading == Heading.E:
            return (position[0] + 1, position[1])
        return (position[0] - 1, position[1])

    def _note_visit(self, position):
        old = self._visit_counts.get(position, 0)
        if old < 9:
            self._visit_counts[position] = old + 1
        self._recent_positions.append(position)
        if len(self._recent_positions) > 10:
            self._recent_positions.pop(0)

    def _recent_count(self, position):
        count = 0
        i = 0
        while i < len(self._recent_positions):
            if self._recent_positions[i] == position:
                count += 1
            i += 1
        return count

    def _in_bounds(self, position, bounds):
        min_x, max_x, min_y, max_y = bounds
        return min_x <= position[0] <= max_x and min_y <= position[1] <= max_y
