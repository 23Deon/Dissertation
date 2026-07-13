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
    """Second deterministic benchmark suite plus analysis metadata."""

    scenario_id: int
    name: str
    difficulty: Difficulty
    challenge_type: ChallengeType
    description: str
    scenario: Scenario
    step_budget: int


def _filled_except(
    *,
    width: int,
    height: int,
    open_cells: Iterable[tuple[int, int]],
) -> set[tuple[int, int]]:
    open_set = set(open_cells)
    return {
        (x, y)
        for x in range(width)
        for y in range(height)
        if (x, y) not in open_set
    }


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


def get_benchmark_suite_2() -> list[ScenarioSpec]:
    """Return an additional deterministic scenario suite for controller evaluation."""

    return [
        _spec(
            scenario_id=101,
            name="suite2_open_midline",
            difficulty="easy",
            challenge_type="straight_line",
            description="Open midline run with no obstacles between start and goal.",
            width=6,
            height=5,
            obstacles=[],
            start=(0, 2),
            goal=(5, 2),
            step_budget=16,
        ),
        _spec(
            scenario_id=102,
            name="suite2_single_center_detour",
            difficulty="easy",
            challenge_type="single_detour",
            description="Single obstacle interrupts the direct line and requires one local detour.",
            width=6,
            height=5,
            obstacles=[(2, 2)],
            start=(0, 2),
            goal=(5, 2),
            step_budget=18,
        ),
        _spec(
            scenario_id=103,
            name="suite2_bent_corridor",
            difficulty="medium",
            challenge_type="corridor",
            description="One-cell corridor bends once before reaching the goal.",
            width=7,
            height=5,
            obstacles=_filled_except(
                width=7,
                height=5,
                open_cells=[
                    (0, 1),
                    (1, 1),
                    (2, 1),
                    (3, 1),
                    (4, 1),
                    (4, 2),
                    (4, 3),
                    (5, 3),
                    (6, 3),
                ],
            ),
            start=(0, 1),
            goal=(6, 3),
            step_budget=20,
        ),
        _spec(
            scenario_id=104,
            name="suite2_fork_with_dead_end",
            difficulty="medium",
            challenge_type="dead_end",
            description="A trunk corridor splits into a short dead end and a longer goal-reaching branch.",
            width=8,
            height=6,
            obstacles=_filled_except(
                width=8,
                height=6,
                open_cells=[
                    (0, 2),
                    (1, 2),
                    (2, 2),
                    (3, 2),
                    (3, 1),
                    (4, 1),
                    (5, 1),
                    (3, 3),
                    (4, 3),
                    (5, 3),
                    (6, 3),
                    (6, 4),
                    (7, 4),
                ],
            ),
            start=(0, 2),
            goal=(7, 4),
            step_budget=22,
        ),
        _spec(
            scenario_id=105,
            name="suite2_row_block_move_away",
            difficulty="medium",
            challenge_type="counterintuitive",
            description="The goal is nearby on the same row, but the route requires moving away before looping back.",
            width=8,
            height=6,
            obstacles=_filled_except(
                width=8,
                height=6,
                open_cells=[
                    (1, 1),
                    (2, 1),
                    (3, 1),
                    (3, 2),
                    (3, 3),
                    (3, 4),
                    (4, 4),
                    (5, 4),
                    (6, 4),
                    (6, 3),
                    (6, 2),
                    (6, 1),
                ],
            ),
            start=(1, 1),
            goal=(6, 1),
            step_budget=24,
        ),
        _spec(
            scenario_id=106,
            name="suite2_long_corridor_with_pocket",
            difficulty="hard",
            challenge_type="corridor",
            description="Long corridor with a side pocket that does not help reach the goal.",
            width=9,
            height=7,
            obstacles=_filled_except(
                width=9,
                height=7,
                open_cells=[
                    (0, 5),
                    (1, 5),
                    (2, 5),
                    (3, 5),
                    (3, 4),
                    (3, 3),
                    (3, 2),
                    (4, 2),
                    (5, 2),
                    (5, 3),
                    (6, 2),
                    (6, 3),
                    (7, 2),
                    (8, 2),
                    (8, 1),
                ],
            ),
            start=(0, 5),
            goal=(8, 1),
            step_budget=26,
        ),
        _spec(
            scenario_id=107,
            name="suite2_reverse_then_branch",
            difficulty="hard",
            challenge_type="counterintuitive",
            description="The tempting branch heads toward the goal too early; the successful route first moves away and loops around.",
            width=9,
            height=7,
            obstacles=_filled_except(
                width=9,
                height=7,
                open_cells=[
                    (4, 6),
                    (4, 5),
                    (4, 4),
                    (4, 3),
                    (5, 3),
                    (6, 3),
                    (7, 3),
                    (3, 3),
                    (2, 3),
                    (2, 2),
                    (2, 1),
                    (3, 1),
                    (4, 1),
                    (5, 1),
                    (6, 1),
                    (7, 1),
                    (8, 1),
                    (8, 2),
                ],
            ),
            start=(4, 6),
            goal=(8, 2),
            step_budget=28,
        ),
    ]


def validate_benchmark_suite_2(specs: list[ScenarioSpec]) -> None:
    """Fail fast if the second benchmark suite becomes internally inconsistent."""

    if len(specs) != 7:
        raise ValueError(f"Expected 7 benchmark scenarios, found {len(specs)}")

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
