import json
import textwrap
from pathlib import Path

from gridbot.eval.analysis import (
    _approach_base_name,
    _approach_method,
    _approach_provider,
    build_chain_summary,
    build_consistency_summary,
    build_difficulty_summary,
    build_experiment_log,
    build_pairwise_changes,
    build_pairwise_summary,
    build_success_preservation_summary,
    build_version_summary,
)
from gridbot.eval.benchmark_suite import get_benchmark_suite, validate_benchmark_suite
from gridbot.eval.drift import compare_runs
from gridbot.eval.harness import run_episode_record
from gridbot.eval.results import record_to_row
from gridbot.sim.actions import Action, Heading
from gridbot.sim.simulator import Simulator
from gridbot.sim.types import Event
from gridbot.world.grid import Grid
from run_experiment import ControllerSpec, execute_controller_spec, normalise_approach_name


class AlwaysForward:
    def act(self, observation):
        return Action.FORWARD


class AlwaysWait:
    def act(self, observation):
        return Action.WAIT


class TurnThenTurnBack:
    def __init__(self):
        self._turned = False

    def act(self, observation):
        if not self._turned:
            self._turned = True
            return Action.TURN_LEFT
        return Action.TURN_RIGHT


def test_benchmark_suite_is_valid():
    validate_benchmark_suite(get_benchmark_suite())


def test_run_episode_record_captures_start_state():
    grid = Grid(width=3, height=3, obstacles=set(), start=(0, 0), goal=(2, 0))
    sim = Simulator(grid, max_steps=10, start_heading=Heading.E)

    record = run_episode_record(sim, AlwaysForward())

    assert record.event == Event.GOAL_REACHED
    assert record.trace.positions == [(0, 0), (1, 0), (2, 0)]
    assert record.trace.headings == [Heading.E, Heading.E, Heading.E]
    assert record.trace.actions == [Action.FORWARD, Action.FORWARD]
    assert record.trace.trace_len == 2


def test_compare_runs_classifies_trace_only_change_as_drift():
    grid = Grid(width=3, height=3, obstacles=set(), start=(0, 0), goal=(2, 0))

    prev = run_episode_record(Simulator(grid, max_steps=2, start_heading=Heading.E), AlwaysWait())
    curr = run_episode_record(Simulator(grid, max_steps=2, start_heading=Heading.E), TurnThenTurnBack())

    drift = compare_runs(prev, curr)

    assert drift.change_type == "drift"
    assert drift.trace_changed is True
    assert drift.event_changed is False
    assert drift.steps_changed is False


def test_analysis_tables_include_requested_metrics():
    suite = get_benchmark_suite()
    base_record = run_episode_record(
        Simulator(Grid(3, 3, set(), (0, 0), (2, 0)), max_steps=10, start_heading=Heading.E),
        AlwaysForward(),
    )

    rows = [
        record_to_row(
            approach="pdd_static",
            version=1,
            controller_path="controllers/pdd_static/controller_v1.py",
            spec=suite[0],
            record=base_record,
        ),
        record_to_row(
            approach="pdd_static",
            version=2,
            controller_path="controllers/pdd_static/controller_v2.py",
            spec=suite[0],
            record=base_record,
        ),
    ]

    loaded_rows = [
        {
            **row.__dict__,
            "action_trace": json.loads(row.action_trace),
            "position_trace": json.loads(row.position_trace),
            "heading_trace": json.loads(row.heading_trace),
        }
        for row in rows
    ]

    version_summary = build_version_summary(loaded_rows)
    chain_summary = build_chain_summary(loaded_rows)
    pairwise_changes = build_pairwise_changes(loaded_rows)
    pairwise_summary = build_pairwise_summary(pairwise_changes)
    difficulty_summary = build_difficulty_summary(loaded_rows, pairwise_changes)

    assert "success_rate" in version_summary[0]
    assert "efficiency_score" in chain_summary[0]
    assert "drift_rate" in pairwise_summary[0]
    assert "outcome_drift_rate" in pairwise_summary[0]
    assert "pure_trace_drift_count" in pairwise_summary[0]
    assert "difficulty" in difficulty_summary[0]
    assert "efficiency_score" in difficulty_summary[0]
    assert pairwise_changes[0]["change_type"] == "same"


def test_consistency_summary_reports_dominant_outcome_share():
    rows = [
        {
            "approach": "demo",
            "version": 1,
            "scenario_id": 1,
            "scenario_name": "demo_scenario",
            "event": "TIMEOUT",
        },
        {
            "approach": "demo",
            "version": 2,
            "scenario_id": 1,
            "scenario_name": "demo_scenario",
            "event": "TIMEOUT",
        },
        {
            "approach": "demo",
            "version": 3,
            "scenario_id": 1,
            "scenario_name": "demo_scenario",
            "event": "GOAL_REACHED",
        },
    ]

    summary = build_consistency_summary(rows)

    assert summary == [
        {
            "approach": "demo",
            "scenario_id": 1,
            "scenario_name": "demo_scenario",
            "dominant_outcome": "TIMEOUT",
            "consistency_score": 0.667,
            "consistency_interpretation": "mixed_or_variable",
        }
    ]


def test_success_preservation_summary_tracks_later_successes():
    rows = [
        {
            "approach": "sdd_demo",
            "version": 1,
            "scenario_id": 1,
            "scenario_name": "demo_scenario",
            "difficulty": "easy",
            "challenge_type": "straight_line",
            "event": "GOAL_REACHED",
        },
        {
            "approach": "sdd_demo",
            "version": 2,
            "scenario_id": 1,
            "scenario_name": "demo_scenario",
            "difficulty": "easy",
            "challenge_type": "straight_line",
            "event": "GOAL_REACHED",
        },
        {
            "approach": "sdd_demo",
            "version": 3,
            "scenario_id": 1,
            "scenario_name": "demo_scenario",
            "difficulty": "easy",
            "challenge_type": "straight_line",
            "event": "TIMEOUT",
        },
    ]

    summary = build_success_preservation_summary(rows)

    assert summary == [
        {
            "approach": "sdd_demo",
            "scenario_id": 1,
            "scenario_name": "demo_scenario",
            "difficulty": "easy",
            "challenge_type": "straight_line",
            "from_version": 1,
            "later_versions": 2,
            "preserved_success_count": 1,
            "success_preservation_rate": 0.5,
        },
        {
            "approach": "sdd_demo",
            "scenario_id": 1,
            "scenario_name": "demo_scenario",
            "difficulty": "easy",
            "challenge_type": "straight_line",
            "from_version": 2,
            "later_versions": 1,
            "preserved_success_count": 0,
            "success_preservation_rate": 0.0,
        },
    ]


def test_experiment_log_reports_method_and_validity():
    rows = [
        {
            "approach": "pdd_demo",
            "version": 1,
            "controller_path": "controllers/pdd_demo/controller_v1.py",
            "scenario_id": 1,
            "event": "GOAL_REACHED",
            "steps": 6,
            "optimal_steps": 4,
            "efficiency_score": 0.667,
        },
        {
            "approach": "pdd_demo",
            "version": 1,
            "controller_path": "controllers/pdd_demo/controller_v1.py",
            "scenario_id": 2,
            "event": "TIMEOUT",
            "steps": 10,
            "optimal_steps": 5,
            "efficiency_score": 0.0,
        },
    ]

    summary = build_experiment_log(rows)

    assert summary == [
        {
            "chain": "pdd_demo",
            "development_method": "PDD",
            "version": 1,
            "validity_status": "valid",
            "controller_path": "controllers/pdd_demo/controller_v1.py",
            "scenarios": 2,
            "success_count": 1,
            "success_rate": 0.5,
            "collision_count": 0,
            "collision_rate": 0.0,
            "timeout_count": 1,
            "timeout_rate": 0.5,
            "invalid_count": 0,
            "invalid_rate": 0.0,
            "average_steps": 8.0,
            "average_optimal_steps": 4.5,
            "efficiency_score": 0.334,
        }
    ]


def test_generated_approaches_are_default_labelled_as_gpt():
    assert normalise_approach_name("pdd_group_b1") == "gpt_pdd_group_b1"
    assert normalise_approach_name("sdd_a") == "gpt_sdd_a"
    assert normalise_approach_name("oracle") == "oracle"
    assert normalise_approach_name("opus_pdd_group_b1") == "opus_pdd_group_b1"


def test_approach_provider_and_method_handle_prefixed_names():
    assert _approach_provider("gpt_pdd_group_b1") == "gpt"
    assert _approach_provider("opus_sdd_a") == "opus"
    assert _approach_base_name("gpt_pdd_group_b1") == "pdd_group_b1"
    assert _approach_method("gpt_pdd_group_b1") == "PDD"
    assert _approach_method("opus_sdd_a") == "SDD"


def test_execute_controller_spec_marks_wall_clock_timeouts():
    scratch_dir = Path("tests") / "_generated_timeout"
    scratch_dir.mkdir(exist_ok=True)
    controller_path = scratch_dir / "controller_v1.py"
    controller_path.write_text(
        textwrap.dedent(
            """
            from gridbot.sim.actions import Action

            class Controller:
                def act(self, observation):
                    while True:
                        pass
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    spec = ControllerSpec(
        approach="timeout_demo",
        version=1,
        path=controller_path,
    )

    rows = execute_controller_spec(spec, get_benchmark_suite()[:1], scenario_timeout_seconds=1.0)

    assert len(rows) == 1
    assert rows[0].event == "TIMEOUT"
    assert "wall-clock timeout" in rows[0].error

    try:
        controller_path.unlink(missing_ok=True)
    except PermissionError:
        pass
    try:
        scratch_dir.rmdir()
    except OSError:
        pass
