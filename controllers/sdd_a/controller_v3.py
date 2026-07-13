from gridbot.sim.actions import Action, Heading


class Controller:
    def act(self, observation) -> Action:
        x, y = observation.position
        goal_x, goal_y = observation.goal
        heading = observation.heading

        if not hasattr(self, "_blocked"):
            self._blocked = set()
        if not hasattr(self, "_last_position"):
            self._last_position = (x, y)
        if not hasattr(self, "_last_heading"):
            self._last_heading = heading
        if not hasattr(self, "_last_action"):
            self._last_action = Action.WAIT
        if not hasattr(self, "_known_points"):
            self._known_points = {(x, y), (goal_x, goal_y)}
        if not hasattr(self, "_turn_bias"):
            self._turn_bias = 0

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
        delta_of = {
            Heading.N: (0, -1),
            Heading.E: (1, 0),
            Heading.S: (0, 1),
            Heading.W: (-1, 0),
        }
        headings = (Heading.N, Heading.E, Heading.S, Heading.W)

        def step(pos, hdg):
            dx, dy = delta_of[hdg]
            return (pos[0] + dx, pos[1] + dy)

        def manhattan(a, b):
            return abs(a[0] - b[0]) + abs(a[1] - b[1])

        def edge_key(pos, hdg):
            return (pos[0], pos[1], hdg)

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

        if self._last_action == Action.FORWARD:
            if (x, y) == self._last_position:
                self._blocked.add(edge_key(self._last_position, self._last_heading))
                blocked_neighbor = step(self._last_position, self._last_heading)
                self._known_points.add(self._last_position)
                self._known_points.add(blocked_neighbor)
            else:
                self._known_points.add((x, y))
                self._known_points.add(self._last_position)
        else:
            self._known_points.add((x, y))

        self._known_points.add((goal_x, goal_y))

        if (x, y) == (goal_x, goal_y):
            self._last_position = (x, y)
            self._last_heading = heading
            self._last_action = Action.WAIT
            return Action.WAIT

        def preferred_heading_from(pos):
            dx = goal_x - pos[0]
            dy = goal_y - pos[1]
            if abs(dx) >= abs(dy):
                if dx > 0:
                    primary = Heading.E
                elif dx < 0:
                    primary = Heading.W
                else:
                    primary = None
                if dy > 0:
                    secondary = Heading.S
                elif dy < 0:
                    secondary = Heading.N
                else:
                    secondary = None
            else:
                if dy > 0:
                    primary = Heading.S
                elif dy < 0:
                    primary = Heading.N
                else:
                    primary = None
                if dx > 0:
                    secondary = Heading.E
                elif dx < 0:
                    secondary = Heading.W
                else:
                    secondary = None

            ordered = []
            if primary is not None:
                ordered.append(primary)
            if secondary is not None and secondary != primary:
                ordered.append(secondary)
            for hdg in headings:
                if hdg not in ordered:
                    ordered.append(hdg)
            return ordered

        def heading_priority(pos, hdg):
            ordered = preferred_heading_from(pos)
            for i, candidate in enumerate(ordered):
                if candidate == hdg:
                    return i
            return 4

        def find_path(start, goal):
            points = list(self._known_points)
            min_x = min([start[0], goal[0]] + [p[0] for p in points]) - 8
            max_x = max([start[0], goal[0]] + [p[0] for p in points]) + 8
            min_y = min([start[1], goal[1]] + [p[1] for p in points]) - 8
            max_y = max([start[1], goal[1]] + [p[1] for p in points]) + 8

            blocked_count = len(self._blocked)
            margin = blocked_count + 8
            if margin > 40:
                margin = 40

            gx0 = min(start[0], goal[0]) - margin
            gx1 = max(start[0], goal[0]) + margin
            gy0 = min(start[1], goal[1]) - margin
            gy1 = max(start[1], goal[1]) + margin

            if gx0 < min_x:
                min_x = gx0
            if gx1 > max_x:
                max_x = gx1
            if gy0 < min_y:
                min_y = gy0
            if gy1 > max_y:
                max_y = gy1

            open_list = [(manhattan(start, goal), 0, start)]
            came_from = {}
            g_score = {start: 0}
            closed = set()

            while open_list:
                best_i = 0
                best_item = open_list[0]
                i = 1
                while i < len(open_list):
                    item = open_list[i]
                    if item[0] < best_item[0] or (
                        item[0] == best_item[0]
                        and (item[1] < best_item[1] or (item[1] == best_item[1] and item[2] < best_item[2]))
                    ):
                        best_i = i
                        best_item = item
                    i += 1

                _, current_g, current = open_list.pop(best_i)
                if current in closed:
                    continue
                closed.add(current)

                if current == goal:
                    path = [current]
                    while current in came_from:
                        current = came_from[current]
                        path.append(current)
                    path.reverse()
                    return path

                ordered = preferred_heading_from(current)
                for hdg in ordered:
                    if edge_key(current, hdg) in self._blocked:
                        continue
                    nxt = step(current, hdg)
                    if nxt[0] < min_x or nxt[0] > max_x or nxt[1] < min_y or nxt[1] > max_y:
                        continue

                    tentative_g = current_g + 1
                    old_g = g_score.get(nxt)
                    if old_g is None or tentative_g < old_g:
                        g_score[nxt] = tentative_g
                        came_from[nxt] = current
                        bias = heading_priority(current, hdg)
                        f = tentative_g + manhattan(nxt, goal) * 2 + bias
                        open_list.append((f, tentative_g, nxt))

            return None

        path = find_path((x, y), (goal_x, goal_y))

        if path is not None and len(path) >= 2:
            nx, ny = path[1]
            if nx > x:
                target_heading = Heading.E
            elif nx < x:
                target_heading = Heading.W
            elif ny > y:
                target_heading = Heading.S
            elif ny < y:
                target_heading = Heading.N
            else:
                target_heading = heading
        else:
            ordered = preferred_heading_from((x, y))
            target_heading = None
            for hdg in ordered:
                if edge_key((x, y), hdg) not in self._blocked:
                    target_heading = hdg
                    break
            if target_heading is None:
                target_heading = heading

        action = turn_toward(heading, target_heading)

        if action == Action.FORWARD and edge_key((x, y), heading) in self._blocked:
            ordered = preferred_heading_from((x, y))
            fallback_heading = None
            for hdg in ordered:
                if edge_key((x, y), hdg) not in self._blocked:
                    fallback_heading = hdg
                    break
            if fallback_heading is None:
                action = Action.WAIT
            else:
                action = turn_toward(heading, fallback_heading)

        if action == Action.TURN_RIGHT:
            self._turn_bias = 1
        elif action == Action.TURN_LEFT:
            self._turn_bias = 0

        if action not in (Action.FORWARD, Action.TURN_LEFT, Action.TURN_RIGHT, Action.WAIT):
            action = Action.WAIT

        self._last_position = (x, y)
        self._last_heading = heading
        self._last_action = action
        return action
