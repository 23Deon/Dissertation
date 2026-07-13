from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Literal

from gridbot.eval.scenario import Scenario


Difficulty = Literal["easy", "medium", "hard"]
ChallengeType = Literal["straight_line", "single_detour", "dead_end", "corridor", "counterintuitive"]
VALID_CHALLENGE_TYPES = {
    "straight_line",
    "single_detour",
    "dead_end",
    "corridor",
    "counterintuitive",
}


@dataclass(frozen=True)
class ScenarioSpec:
    """Deterministic benchmark scenario plus analysis metadata."""

    scenario_id: int
    name: str
    difficulty: Difficulty
    challenge_type: ChallengeType
    description: str
    scenario: Scenario
    step_budget: int


def _spec(
    *,
    scenario_id: int,
    name: str,
    difficulty: Difficulty,
    challenge_type: ChallengeType,
    description: str,
    width: int,
    height: int,
    obstacles: Iterable[tuple[int, int]],
    start: tuple[int, int],
    goal: tuple[int, int],
    step_budget: int,
) -> ScenarioSpec:
    return ScenarioSpec(
        scenario_id=scenario_id,
        name=name,
        difficulty=difficulty,
        challenge_type=challenge_type,
        description=description,
        scenario=Scenario(
            width=width,
            height=height,
            obstacles=set(obstacles),
            start=start,
            goal=goal,
            max_steps=step_budget,
        ),
        step_budget=step_budget,
    )


def get_benchmark_suite() -> list[ScenarioSpec]:
    """Return the canonical deterministic scenario suite for controller evaluation."""

    return [
        _spec(
            scenario_id=1,
            name="easy_open_short_path",
            difficulty="easy",
            challenge_type="straight_line",
            description="Open grid, no obstacles, short path.",
            width=5,
            height=3,
            obstacles=[],
            start=(0, 1),
            goal=(4, 1),
            step_budget=20,
        ),
        _spec(
            scenario_id=2,
            name="easy_single_obstacle_detour",
            difficulty="easy",
            challenge_type="single_detour",
            description="Single obstacle on the direct path requiring one simple detour.",
            width=5,
            height=4,
            obstacles=[(2, 1)],
            start=(0, 1),
            goal=(4, 1),
            step_budget=24,
        ),
        _spec(
            scenario_id=3,
            name="easy_l_wall_one_turn",
            difficulty="easy",
            challenge_type="single_detour",
            description="L-shaped wall forcing a simple route with one major turn.",
            width=6,
            height=5,
            obstacles=[(1, 1), (2, 1), (3, 1), (3, 2), (3, 3)],
            start=(0, 0),
            goal=(5, 4),
            step_budget=28,
        ),
        _spec(
            scenario_id=4,
            name="easy_corner_goal_blocked",
            difficulty="easy",
            challenge_type="single_detour",
            description="Goal is in a corner with one obstacle blocking the most direct route.",
            width=5,
            height=5,
            obstacles=[(4, 4)],
            start=(0, 4),
            goal=(4, 0),
            step_budget=26,
        ),
        _spec(
            scenario_id=5,
            name="easy_two_isolated_obstacles",
            difficulty="easy",
            challenge_type="single_detour",
            description="Slightly longer path with two isolated obstacles on the direct route.",
            width=7,
            height=5,
            obstacles=[(2, 2), (4, 2)],
            start=(0, 2),
            goal=(6, 2),
            step_budget=30,
        ),
        _spec(
            scenario_id=6,
            name="medium_straight_narrow_corridor",
            difficulty="medium",
            challenge_type="corridor",
            description="Narrow one-cell-wide corridor running straight through the map.",
            width=8,
            height=5,
            obstacles=[
                (1, 1),
                (1, 3),
                (2, 1),
                (2, 3),
                (3, 1),
                (3, 3),
                (4, 1),
                (4, 3),
                (5, 1),
                (5, 3),
                (6, 1),
                (6, 3),
            ],
            start=(0, 2),
            goal=(7, 2),
            step_budget=15,
        ),
        _spec(
            scenario_id=7,
            name="medium_s_shaped_path",
            difficulty="medium",
            challenge_type="corridor",
            description="S-shaped corridor with two forced turns.",
            width=6,
            height=5,
            obstacles=[
                (5, 0),
                (0, 1),
                (1, 1),
                (2, 1),
                (3, 1),
                (5, 1),
                (0, 2),
                (5, 2),
                (0, 3),
                (2, 3),
                (3, 3),
                (4, 3),
                (5, 3),
                (0, 4),
            ],
            start=(0, 0),
            goal=(5, 4),
            step_budget=20,
        ),
        _spec(
            scenario_id=8,
            name="medium_central_obstacle",
            difficulty="medium",
            challenge_type="single_detour",
            description="Large central obstacle can be navigated around either side.",
            width=7,
            height=7,
            obstacles=[
                (2, 2),
                (2, 3),
                (2, 4),
                (3, 2),
                (3, 3),
                (3, 4),
                (4, 2),
                (4, 3),
                (4, 4),
            ],
            start=(0, 3),
            goal=(6, 3),
            step_budget=20,
        ),
        _spec(
            scenario_id=9,
            name="medium_single_valid_detour",
            difficulty="medium",
            challenge_type="single_detour",
            description="Direct route is blocked and only one detour gap is available.",
            width=7,
            height=5,
            obstacles=[(4, 0), (4, 1), (4, 2), (4, 3)],
            start=(0, 2),
            goal=(6, 2),
            step_budget=18,
        ),
        _spec(
            scenario_id=10,
            name="medium_dead_end_corridors",
            difficulty="medium",
            challenge_type="dead_end",
            description="Two corridor choices exist; one is a dead end and one reaches the goal.",
            width=8,
            height=5,
            obstacles=[(2, 0), (2, 2), (2, 4), (5, 0), (5, 1), (5, 2), (5, 4)],
            start=(0, 2),
            goal=(7, 2),
            step_budget=20,
        ),
        _spec(
            scenario_id=11,
            name="hard_maze_one_dead_end",
            difficulty="hard",
            challenge_type="dead_end",
            description="Maze-like layout with one dead end before the correct path.",
            width=8,
            height=6,
            obstacles=[
                (1, 1),
                (1, 2),
                (1, 4),
                (2, 1),
                (3, 1),
                (3, 3),
                (3, 4),
                (4, 1),
                (4, 3),
                (5, 1),
                (5, 2),
                (5, 4),
                (6, 2),
                (6, 4),
            ],
            start=(0, 0),
            goal=(7, 5),
            step_budget=24,
        ),
        _spec(
            scenario_id=12,
            name="hard_u_trap_goal",
            difficulty="hard",
            challenge_type="counterintuitive",
            description="U-shaped trap in front of the goal requiring the robot to go around.",
            width=7,
            height=7,
            obstacles=[
                (2, 1),
                (2, 2),
                (2, 3),
                (3, 3),
                (4, 1),
                (4, 2),
                (4, 3),
            ],
            start=(3, 6),
            goal=(3, 2),
            step_budget=24,
        ),
        _spec(
            scenario_id=13,
            name="hard_long_detour_budget",
            difficulty="hard",
            challenge_type="counterintuitive",
            description="Long detour required; naive direct movement exhausts the tight budget.",
            width=10,
            height=7,
            obstacles=[
                (1, 2),
                (2, 2),
                (3, 2),
                (4, 2),
                (5, 2),
                (6, 2),
                (7, 2),
                (8, 2),
                (1, 4),
                (2, 4),
                (3, 4),
                (4, 4),
                (5, 4),
                (6, 4),
                (7, 4),
                (8, 4),
                (8, 3),
            ],
            start=(0, 3),
            goal=(9, 3),
            step_budget=26,
        ),
        _spec(
            scenario_id=14,
            name="hard_two_dead_ends",
            difficulty="hard",
            challenge_type="dead_end",
            description="Two dead ends and one correct path, with the correct route initially counterintuitive.",
            width=9,
            height=7,
            obstacles=[
                (1, 1),
                (1, 2),
                (1, 4),
                (1, 5),
                (3, 0),
                (3, 1),
                (3, 3),
                (3, 5),
                (3, 6),
                (5, 1),
                (5, 2),
                (5, 3),
                (5, 5),
                (7, 0),
                (7, 1),
                (7, 3),
                (7, 4),
                (7, 5),
            ],
            start=(0, 3),
            goal=(8, 6),
            step_budget=28,
        ),
        _spec(
            scenario_id=15,
            name="hard_move_away_corridor",
            difficulty="hard",
            challenge_type="counterintuitive",
            description="Corridor forces the robot to move away from the nearby goal before reaching it.",
            width=8,
            height=5,
            obstacles=[(5, 1), (5, 3), (6, 1), (6, 2), (6, 3)],
            start=(5, 2),
            goal=(7, 2),
            step_budget=22,
        ),
    ]


def validate_benchmark_suite(specs: list[ScenarioSpec]) -> None:
    """Fail fast if the benchmark suite becomes internally inconsistent."""

    if not 12 <= len(specs) <= 15:
        raise ValueError(f"Expected 12-15 benchmark scenarios, found {len(specs)}")

    if len({spec.scenario_id for spec in specs}) != len(specs):
        raise ValueError("Scenario ids must be unique")

    if len({spec.name for spec in specs}) != len(specs):
        raise ValueError("Scenario names must be unique")

    for spec in specs:
        if spec.step_budget <= 0:
            raise ValueError(f"{spec.name} has a non-positive step budget")
        if spec.scenario.max_steps != spec.step_budget:
            raise ValueError(f"{spec.name} step_budget must match scenario.max_steps")
        if spec.challenge_type not in VALID_CHALLENGE_TYPES:
            raise ValueError(f"{spec.name} has invalid challenge_type {spec.challenge_type!r}")
        _validate_scenario_geometry(spec)


def _validate_scenario_geometry(spec: ScenarioSpec) -> None:
    scenario = spec.scenario

    if scenario.start in scenario.obstacles:
        raise ValueError(f"{spec.name} start cannot be an obstacle")

    if scenario.goal in scenario.obstacles:
        raise ValueError(f"{spec.name} goal cannot be an obstacle")

    for position in [scenario.start, scenario.goal, *scenario.obstacles]:
        x, y = position
        if not (0 <= x < scenario.width and 0 <= y < scenario.height):
            raise ValueError(f"{spec.name} contains out-of-bounds position {position}")
