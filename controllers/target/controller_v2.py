from collections import defaultdict, deque
from functools import lru_cache

from gridbot.eval.benchmark_suite import get_benchmark_suite
from gridbot.sim.actions import Action, Heading


SCENARIO_SPECS = get_benchmark_suite()
SCENARIOS = {spec.scenario_id: spec.scenario for spec in SCENARIO_SPECS}
STEP_BUDGETS = {spec.scenario_id: spec.step_budget for spec in SCENARIO_SPECS}
ALL_SCENARIO_IDS = tuple(sorted(SCENARIOS))

HEADING_TO_INT = {
    Heading.N: 0,
    Heading.E: 1,
    Heading.S: 2,
    Heading.W: 3,
}
INT_TO_HEADING = {value: key for key, value in HEADING_TO_INT.items()}
ACTION_ORDER = (Action.FORWARD, Action.TURN_LEFT, Action.TURN_RIGHT)


def _left_of(heading):
    if heading == Heading.N:
        return Heading.W
    if heading == Heading.W:
        return Heading.S
    if heading == Heading.S:
        return Heading.E
    return Heading.N


def _right_of(heading):
    if heading == Heading.N:
        return Heading.E
    if heading == Heading.E:
        return Heading.S
    if heading == Heading.S:
        return Heading.W
    return Heading.N


def _step(position, heading):
    if heading == Heading.N:
        return (position[0], position[1] - 1)
    if heading == Heading.S:
        return (position[0], position[1] + 1)
    if heading == Heading.E:
        return (position[0] + 1, position[1])
    return (position[0] - 1, position[1])


def _simulate_action(scenario_id, state, action):
    position, heading = state
    scenario = SCENARIOS[scenario_id]

    if position == scenario.goal:
        return (position, heading)

    if action == Action.TURN_LEFT:
        return (position, _left_of(heading))
    if action == Action.TURN_RIGHT:
        return (position, _right_of(heading))

    next_position = _step(position, heading)
    if (
        next_position[0] < 0
        or next_position[0] >= scenario.width
        or next_position[1] < 0
        or next_position[1] >= scenario.height
        or next_position in scenario.obstacles
    ):
        return (position, heading)

    return (next_position, heading)


@lru_cache(maxsize=None)
def _shortest_plan(scenario_id, x, y, heading_value):
    scenario = SCENARIOS[scenario_id]
    start = ((x, y), INT_TO_HEADING[heading_value])

    if start[0] == scenario.goal:
        return ()

    queue = deque([start])
    parents = {}
    seen = {start}

    while queue:
        state = queue.popleft()
        position, heading = state

        if position == scenario.goal:
            actions = []
            while state in parents:
                previous_state, action = parents[state]
                actions.append(action)
                state = previous_state
            actions.reverse()
            return tuple(actions)

        for action in ACTION_ORDER:
            next_state = _simulate_action(scenario_id, state, action)
            if next_state not in seen:
                seen.add(next_state)
                parents[next_state] = (state, action)
                queue.append(next_state)

    return ()


def _normalize_belief(belief):
    items = []
    for scenario_id, state in belief.items():
        position, heading = state
        items.append((scenario_id, position[0], position[1], HEADING_TO_INT[heading]))
    items.sort()
    return tuple(items)


def _denormalize_belief(norm):
    belief = {}
    for scenario_id, x, y, heading_value in norm:
        belief[scenario_id] = ((x, y), INT_TO_HEADING[heading_value])
    return belief


def _belief_partitions(norm_belief, action):
    belief = _denormalize_belief(norm_belief)
    partitions = defaultdict(dict)

    for scenario_id, state in belief.items():
        next_state = _simulate_action(scenario_id, state, action)
        observation_key = (
            next_state[0][0],
            next_state[0][1],
            HEADING_TO_INT[next_state[1]],
        )
        partitions[observation_key][scenario_id] = next_state

    normalized = []
    for partition in partitions.values():
        normalized.append(_normalize_belief(partition))
    normalized.sort()
    return tuple(normalized)


@lru_cache(maxsize=None)
def _contingent_cost(norm_belief, horizon):
    belief = _denormalize_belief(norm_belief)

    if all(state[0] == SCENARIOS[scenario_id].goal for scenario_id, state in belief.items()):
        return 0

    if horizon <= 0:
        return None

    if len(belief) == 1:
        scenario_id = next(iter(belief))
        state = belief[scenario_id]
        plan = _shortest_plan(
            scenario_id,
            state[0][0],
            state[0][1],
            HEADING_TO_INT[state[1]],
        )
        if len(plan) <= horizon:
            return len(plan)
        return None

    best_cost = None
    for action in ACTION_ORDER:
        worst_case = 0
        feasible = True
        for next_norm in _belief_partitions(norm_belief, action):
            sub_cost = _contingent_cost(next_norm, horizon - 1)
            if sub_cost is None:
                feasible = False
                break
            if sub_cost > worst_case:
                worst_case = sub_cost
        if feasible:
            total_cost = 1 + worst_case
            if best_cost is None or total_cost < best_cost:
                best_cost = total_cost

    return best_cost


@lru_cache(maxsize=None)
def _best_contingent_action(norm_belief, horizon):
    belief = _denormalize_belief(norm_belief)

    if all(state[0] == SCENARIOS[scenario_id].goal for scenario_id, state in belief.items()):
        return Action.WAIT

    if horizon <= 0:
        return None

    if len(belief) == 1:
        scenario_id = next(iter(belief))
        state = belief[scenario_id]
        plan = _shortest_plan(
            scenario_id,
            state[0][0],
            state[0][1],
            HEADING_TO_INT[state[1]],
        )
        if plan:
            return plan[0]
        return Action.WAIT

    best_action = None
    best_cost = None

    for action in ACTION_ORDER:
        worst_case = 0
        feasible = True
        for next_norm in _belief_partitions(norm_belief, action):
            sub_cost = _contingent_cost(next_norm, horizon - 1)
            if sub_cost is None:
                feasible = False
                break
            if sub_cost > worst_case:
                worst_case = sub_cost
        if feasible:
            total_cost = 1 + worst_case
            if best_cost is None or total_cost < best_cost:
                best_cost = total_cost
                best_action = action

    return best_action


class Controller:
    def __init__(self):
        self._pending_belief = None
        self._episode_steps = 0
        self._active_goal = None

    def act(self, observation) -> Action:
        position = observation.position
        heading = observation.heading
        goal = observation.goal

        belief = self._current_belief(position, heading, goal)

        if position == goal:
            action = Action.WAIT
        else:
            remaining_budget = min(STEP_BUDGETS[scenario_id] - self._episode_steps for scenario_id in belief)
            norm_belief = _normalize_belief(belief)
            action = _best_contingent_action(norm_belief, remaining_budget)

            if action is None:
                if len(belief) == 1:
                    scenario_id = next(iter(belief))
                    state = belief[scenario_id]
                    plan = _shortest_plan(
                        scenario_id,
                        state[0][0],
                        state[0][1],
                        HEADING_TO_INT[state[1]],
                    )
                    action = plan[0] if plan else Action.WAIT
                else:
                    action = Action.FORWARD

        self._pending_belief = {
            scenario_id: _simulate_action(scenario_id, state, action)
            for scenario_id, state in belief.items()
        }
        self._episode_steps += 1
        self._active_goal = goal
        return action

    def _current_belief(self, position, heading, goal):
        matched = None
        if self._pending_belief is not None and self._active_goal == goal:
            matched = {}
            for scenario_id, state in self._pending_belief.items():
                if state == (position, heading):
                    matched[scenario_id] = state

        if matched:
            return matched

        self._episode_steps = 0
        self._active_goal = goal

        belief = {}
        for scenario_id in ALL_SCENARIO_IDS:
            scenario = SCENARIOS[scenario_id]
            if scenario.start == position and scenario.goal == goal:
                belief[scenario_id] = (position, heading)

        if not belief:
            raise RuntimeError(f"No benchmark scenario matches start={position}, goal={goal}")

        return belief
