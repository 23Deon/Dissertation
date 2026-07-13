from gridbot.sim.actions import Action, Heading


class Controller:
    def act(self, observation) -> Action:
        x, y = observation.position
        goal_x, goal_y = observation.goal
        heading = observation.heading

        left_of = {
            Heading.N: Heading.W,
            Heading.W: Heading.S,
            Heading.S: Heading.E,
            Heading.E: Heading.N,
        }
        right_of = {
            Heading.N: Heading.E,
            Heading.E: Heading.S,
            Heading.S: Heading.W,
            Heading.W: Heading.N,
        }
        opposite_of = {
            Heading.N: Heading.S,
            Heading.S: Heading.N,
            Heading.E: Heading.W,
            Heading.W: Heading.E,
        }
        delta_of = {
            Heading.N: (0, -1),
            Heading.E: (1, 0),
            Heading.S: (0, 1),
            Heading.W: (-1, 0),
        }
        heading_order = (Heading.N, Heading.E, Heading.S, Heading.W)

        def step(pos, hdg):
            dx, dy = delta_of[hdg]
            return (pos[0] + dx, pos[1] + dy)

        def distance(pos):
            return abs(goal_x - pos[0]) + abs(goal_y - pos[1])

        def turn_cost(current, target):
            if current == target:
                return 0
            if left_of[current] == target or right_of[current] == target:
                return 1
            return 2

        def turn_toward(current, target):
            if current == target:
                return Action.FORWARD
            if right_of[current] == target:
                return Action.TURN_RIGHT
            if left_of[current] == target:
                return Action.TURN_LEFT
            if self._turn_bias == 0:
                return Action.TURN_RIGHT
            return Action.TURN_LEFT

        def edge_key(pos, hdg):
            return (pos[0], pos[1], hdg)

        def is_blocked(pos, hdg):
            return edge_key(pos, hdg) in self._blocked_edges

        def note_visit(pos):
            old = self._visit_counts.get(pos, 0)
            if old < 9:
                self._visit_counts[pos] = old + 1
            else:
                self._visit_counts[pos] = 9
            self._recent_positions.append(pos)
            if len(self._recent_positions) > 12:
                self._recent_positions.pop(0)

        def recent_count(pos):
            c = 0
            i = 0
            while i < len(self._recent_positions):
                if self._recent_positions[i] == pos:
                    c += 1
                i += 1
            return c

        def greedy_order(pos, current_heading):
            dx = goal_x - pos[0]
            dy = goal_y - pos[1]

            primary = None
            secondary = None

            if abs(dx) >= abs(dy):
                if dx > 0:
                    primary = Heading.E
                elif dx < 0:
                    primary = Heading.W
                if dy > 0:
                    secondary = Heading.S
                elif dy < 0:
                    secondary = Heading.N
            else:
                if dy > 0:
                    primary = Heading.S
                elif dy < 0:
                    primary = Heading.N
                if dx > 0:
                    secondary = Heading.E
                elif dx < 0:
                    secondary = Heading.W

            order = []
            if primary is not None:
                order.append(primary)
            if secondary is not None and secondary != primary:
                order.append(secondary)

            turn_pref = (
                current_heading,
                left_of[current_heading],
                right_of[current_heading],
                opposite_of[current_heading],
            )
            i = 0
            while i < len(turn_pref):
                hdg = turn_pref[i]
                if hdg not in order:
                    order.append(hdg)
                i += 1

            i = 0
            while i < len(heading_order):
                hdg = heading_order[i]
                if hdg not in order:
                    order.append(hdg)
                i += 1

            return order

        def best_greedy_heading(pos, current_heading):
            order = greedy_order(pos, current_heading)
            current_dist = distance(pos)
            best_heading = None
            best_score = None

            i = 0
            while i < len(order):
                hdg = order[i]
                if not is_blocked(pos, hdg):
                    nxt = step(pos, hdg)
                    nxt_dist = distance(nxt)
                    improve_penalty = 0
                    if nxt_dist > current_dist:
                        improve_penalty = 200
                    elif nxt_dist == current_dist:
                        improve_penalty = 60

                    score = (
                        nxt_dist * 1000
                        + improve_penalty
                        + self._visit_counts.get(nxt, 0) * 20
                        + recent_count(nxt) * 15
                        + turn_cost(current_heading, hdg) * 3
                        + i
                    )

                    if best_score is None or score < best_score:
                        best_score = score
                        best_heading = hdg
                i += 1

            if best_heading is not None:
                return best_heading

            i = 0
            while i < len(order):
                hdg = order[i]
                if hdg == current_heading:
                    return hdg
                i += 1
            return current_heading

        def choose_follow_heading(pos, current_heading, side):
            if side == 0:
                order = [
                    left_of[current_heading],
                    current_heading,
                    right_of[current_heading],
                    opposite_of[current_heading],
                ]
            else:
                order = [
                    right_of[current_heading],
                    current_heading,
                    left_of[current_heading],
                    opposite_of[current_heading],
                ]

            best_heading = None
            best_score = None
            i = 0
            while i < len(order):
                hdg = order[i]
                if not is_blocked(pos, hdg):
                    nxt = step(pos, hdg)
                    backtrack_penalty = 0
                    if len(self._recent_positions) >= 2 and nxt == self._recent_positions[-2]:
                        backtrack_penalty = 50
                    score = (
                        i * 100
                        + self._visit_counts.get(nxt, 0) * 12
                        + recent_count(nxt) * 10
                        + distance(nxt) * 2
                        + backtrack_penalty
                    )
                    if best_score is None or score < best_score:
                        best_score = score
                        best_heading = hdg
                i += 1

            if best_heading is not None:
                return best_heading

            return opposite_of[current_heading]

        def start_follow_mode(blocked_heading):
            self._mode = 1
            self._follow_steps = 0
            self._follow_fails = 0
            self._follow_entry_distance = distance((x, y))
            self._follow_best_distance = self._follow_entry_distance
            self._follow_entry_position = (x, y)

            greedy_alt = best_greedy_heading((x, y), blocked_heading)
            if greedy_alt == left_of[blocked_heading]:
                self._follow_side = 0
            elif greedy_alt == right_of[blocked_heading]:
                self._follow_side = 1
            else:
                self._follow_side = self._turn_bias

        if not hasattr(self, "_blocked_edges"):
            self._blocked_edges = set()
        if not hasattr(self, "_visit_counts"):
            self._visit_counts = {}
        if not hasattr(self, "_recent_positions"):
            self._recent_positions = []
        if not hasattr(self, "_last_position"):
            self._last_position = (x, y)
        if not hasattr(self, "_last_heading"):
            self._last_heading = heading
        if not hasattr(self, "_last_action"):
            self._last_action = Action.WAIT
        if not hasattr(self, "_mode"):
            self._mode = 0
        if not hasattr(self, "_follow_side"):
            self._follow_side = 0
        if not hasattr(self, "_follow_steps"):
            self._follow_steps = 0
        if not hasattr(self, "_follow_fails"):
            self._follow_fails = 0
        if not hasattr(self, "_follow_entry_distance"):
            self._follow_entry_distance = distance((x, y))
        if not hasattr(self, "_follow_best_distance"):
            self._follow_best_distance = distance((x, y))
        if not hasattr(self, "_follow_entry_position"):
            self._follow_entry_position = (x, y)
        if not hasattr(self, "_turn_bias"):
            self._turn_bias = 0

        blocked_forward = False
        if self._last_action == Action.FORWARD and (x, y) == self._last_position:
            blocked_forward = True
            self._blocked_edges.add(edge_key(self._last_position, self._last_heading))
            if len(self._blocked_edges) > 128:
                trimmed = set()
                keep = list(self._blocked_edges)
                start = len(keep) - 128
                if start < 0:
                    start = 0
                i = start
                while i < len(keep):
                    trimmed.add(keep[i])
                    i += 1
                self._blocked_edges = trimmed

        note_visit((x, y))

        if (x, y) == (goal_x, goal_y):
            self._mode = 0
            self._last_position = (x, y)
            self._last_heading = heading
            self._last_action = Action.WAIT
            return Action.WAIT

        if blocked_forward:
            if self._mode == 1:
                self._follow_fails += 1
            else:
                start_follow_mode(self._last_heading)

        current_dist = distance((x, y))

        if self._mode == 1:
            if current_dist < self._follow_best_distance:
                self._follow_best_distance = current_dist

            min_commit = 5
            should_exit = False

            if self._follow_steps >= min_commit:
                greedy_heading = best_greedy_heading((x, y), heading)
                greedy_next = step((x, y), greedy_heading)
                greedy_ok = not is_blocked((x, y), greedy_heading)

                if greedy_ok and current_dist < self._follow_entry_distance:
                    should_exit = True
                elif greedy_ok and current_dist <= self._follow_best_distance and greedy_next not in self._recent_positions[-4:]:
                    should_exit = True

            if should_exit:
                self._mode = 0
                self._follow_steps = 0
                self._follow_fails = 0

        if self._mode == 1:
            if self._follow_steps >= 10:
                stagnating = current_dist >= self._follow_best_distance
                repeated_here = recent_count((x, y)) >= 3
                if self._follow_fails >= 2 and (stagnating or repeated_here):
                    if self._follow_side == 0:
                        self._follow_side = 1
                    else:
                        self._follow_side = 0
                    self._follow_steps = 0
                    self._follow_fails = 0
                    self._follow_entry_distance = current_dist
                    self._follow_best_distance = current_dist
                    self._follow_entry_position = (x, y)

        if self._mode == 0:
            target_heading = best_greedy_heading((x, y), heading)
        else:
            target_heading = choose_follow_heading((x, y), heading, self._follow_side)

        if target_heading not in heading_order:
            target_heading = heading

        action = turn_toward(heading, target_heading)

        if action == Action.FORWARD and is_blocked((x, y), heading):
            if self._mode == 0:
                start_follow_mode(heading)
                target_heading = choose_follow_heading((x, y), heading, self._follow_side)
                action = turn_toward(heading, target_heading)
            else:
                alt_heading = choose_follow_heading((x, y), heading, self._follow_side)
                if alt_heading == heading and is_blocked((x, y), alt_heading):
                    alt_heading = opposite_of[heading]
                action = turn_toward(heading, alt_heading)

        if action == Action.TURN_LEFT:
            self._turn_bias = 0
        elif action == Action.TURN_RIGHT:
            self._turn_bias = 1

        if self._mode == 1 and action in (Action.FORWARD, Action.TURN_LEFT, Action.TURN_RIGHT):
            self._follow_steps += 1

        if action not in (Action.FORWARD, Action.TURN_LEFT, Action.TURN_RIGHT, Action.WAIT):
            action = Action.WAIT

        self._last_position = (x, y)
        self._last_heading = heading
        self._last_action = action
        return action
