from gridbot.sim.actions import Action, Heading


class Controller:
    _CW = [Heading.N, Heading.E, Heading.S, Heading.W]

    def __init__(self):
        self._prev_pos = None
        self._prev_action = None
        self._mode = "greedy"
        self._greedy_blocks = 0
        self._best_dist = None
        self._steps_no_prog = 0
        self._wall_side = "right"
        self._wall_side_locked = False
        self._wall_intended = Heading.N
        self._wall_prio = 0
        self._wall_steps = 0
        self._wall_entry_dist = 0
        self._wall_last_pos = None

    def act(self, observation) -> Action:
        pos = observation.position
        if isinstance(pos, list):
            pos = tuple(pos)
        heading = observation.heading
        goal = observation.goal
        if isinstance(goal, list):
            goal = tuple(goal)

        if pos[0] == goal[0] and pos[1] == goal[1]:
            self._prev_pos = pos
            self._prev_action = Action.WAIT
            return Action.WAIT

        dist = abs(goal[0] - pos[0]) + abs(goal[1] - pos[1])
        if self._best_dist is None or dist < self._best_dist:
            self._best_dist = dist
            self._steps_no_prog = 0
        else:
            self._steps_no_prog += 1

        blocked = (
            self._prev_action == Action.FORWARD
            and self._prev_pos is not None
            and self._prev_pos == pos
        )

        if self._mode == "greedy":
            action = self._greedy(pos, heading, goal, blocked)
        else:
            action = self._wall(pos, heading, goal, blocked)

        self._prev_pos = pos
        self._prev_action = action
        return action

    def _greedy(self, pos, heading, goal, blocked):
        if blocked:
            self._greedy_blocks += 1
        elif self._prev_action == Action.FORWARD:
            self._greedy_blocks = 0

        if self._greedy_blocks >= 2 or self._steps_no_prog >= 20:
            self._enter_wall(pos, heading, goal)
            return self._wall(pos, heading, goal, blocked=False)

        dx = goal[0] - pos[0]
        dy = goal[1] - pos[1]
        ranked = self._ranked(dx, dy)
        index = min(self._greedy_blocks, len(ranked) - 1)
        desired = ranked[index]

        if heading == desired:
            return Action.FORWARD
        return self._turn(heading, desired)

    def _enter_wall(self, pos, heading, goal):
        self._mode = "wall"
        self._wall_steps = 0
        self._wall_entry_dist = abs(goal[0] - pos[0]) + abs(goal[1] - pos[1])
        self._wall_last_pos = pos
        self._greedy_blocks = 0
        self._steps_no_prog = 0
        self._best_dist = self._wall_entry_dist

        if not self._wall_side_locked:
            dx = goal[0] - pos[0]
            dy = goal[1] - pos[1]
            left_p = self._rot(heading, -1)
            right_p = self._rot(heading, 1)

            def score(candidate):
                if candidate == Heading.E:
                    return dx
                if candidate == Heading.W:
                    return -dx
                if candidate == Heading.S:
                    return dy
                if candidate == Heading.N:
                    return -dy
                return 0

            if score(left_p) >= score(right_p):
                self._wall_side = "right"
            else:
                self._wall_side = "left"
            self._wall_side_locked = True

        if self._wall_side == "right":
            self._wall_intended = self._rot(heading, -1)
        else:
            self._wall_intended = self._rot(heading, 1)

        self._wall_prio = 1

    def _wall(self, pos, heading, goal, blocked):
        self._wall_steps += 1
        dist = abs(goal[0] - pos[0]) + abs(goal[1] - pos[1])

        moved = pos != self._wall_last_pos
        if moved and self._prev_action == Action.FORWARD:
            self._wall_intended = heading
            self._wall_prio = 0
            self._wall_last_pos = pos
        elif blocked:
            self._wall_prio = min(self._wall_prio + 1, 3)

        if (
            self._wall_steps >= 4
            and dist < self._wall_entry_dist
            and moved
            and self._wall_prio == 0
        ):
            self._mode = "greedy"
            self._greedy_blocks = 0
            self._steps_no_prog = 0
            self._best_dist = dist
            return self._greedy(pos, heading, goal, blocked=False)

        if self._wall_steps > 400:
            self._mode = "greedy"
            self._greedy_blocks = 0
            self._steps_no_prog = 0
            self._best_dist = dist
            self._wall_side = "left" if self._wall_side == "right" else "right"
            return self._greedy(pos, heading, goal, blocked=False)

        if self._wall_side == "right":
            offsets = [1, 0, -1, 2]
        else:
            offsets = [-1, 0, 1, 2]

        desired = self._rot(self._wall_intended, offsets[self._wall_prio])

        if self._wall_steps == 1 and not blocked:
            desired = self._rot(self._wall_intended, offsets[0])

        if heading == desired:
            return Action.FORWARD
        return self._turn(heading, desired)

    def _rot(self, heading, steps):
        index = self._CW.index(heading)
        return self._CW[(index + steps) % 4]

    def _ranked(self, dx, dy):
        if dx >= 0:
            xt, xa = Heading.E, Heading.W
        else:
            xt, xa = Heading.W, Heading.E
        if dy >= 0:
            yt, ya = Heading.S, Heading.N
        else:
            yt, ya = Heading.N, Heading.S
        if abs(dx) >= abs(dy):
            return [xt, yt, ya, xa]
        return [yt, xt, xa, ya]

    def _turn(self, current, desired):
        ci = self._CW.index(current)
        di = self._CW.index(desired)
        diff = (di - ci) % 4
        if diff == 1:
            return Action.TURN_RIGHT
        if diff == 3:
            return Action.TURN_LEFT
        return Action.TURN_RIGHT
