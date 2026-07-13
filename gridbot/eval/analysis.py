from __future__ import annotations

import csv
import json
from collections import defaultdict, deque
from functools import lru_cache
from pathlib import Path
from typing import Callable

from gridbot.eval.benchmark_suite import get_benchmark_suite
from gridbot.eval.benchmark_suite_2 import get_benchmark_suite_2
from gridbot.eval.drift import compare_runs
from gridbot.eval.record import ScenarioRunRecord, TraceRecord
from gridbot.sim.actions import Action, Heading
from gridbot.sim.types import Event


RESULT_COLUMNS = [
    "approach",
    "version",
    "controller_path",
    "scenario_id",
    "scenario_name",
    "difficulty",
    "challenge_type",
    "description",
    "step_budget",
    "event",
    "steps",
    "trace_len",
    "action_trace",
    "position_trace",
    "heading_trace",
]


def normalise_token(value: str) -> str:
    text = str(value).strip()
    if "." in text:
        return text.split(".")[-1]
    return text


def load_results(csv_path: str | Path) -> list[dict]:
    with Path(csv_path).open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        missing = set(RESULT_COLUMNS) - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Missing required columns: {sorted(missing)}")

        rows: list[dict] = []
        for row in reader:
            scenario_id = int(row["scenario_id"])
            event = normalise_token(row["event"])
            steps = int(row["steps"])
            optimal_steps = _optimal_steps_by_scenario_id().get(scenario_id)
            rows.append(
                {
                    "approach": row["approach"],
                    "version": int(row["version"]),
                    "controller_path": row["controller_path"],
                    "scenario_id": scenario_id,
                    "scenario_name": row["scenario_name"],
                    "difficulty": row["difficulty"],
                    "challenge_type": row["challenge_type"],
                    "description": row["description"],
                    "step_budget": int(row["step_budget"]),
                    "event": event,
                    "steps": steps,
                    "trace_len": int(row["trace_len"]),
                    "action_trace": json.loads(row["action_trace"]),
                    "position_trace": json.loads(row["position_trace"]),
                    "heading_trace": json.loads(row["heading_trace"]),
                    "optimal_steps": optimal_steps,
                    "efficiency_score": _compute_efficiency_score(event, steps, optimal_steps),
                    "error": row.get("error", ""),
                }
            )

    return rows


def build_version_summary(rows: list[dict]) -> list[dict]:
    grouped: dict[tuple[str, int], list[dict]] = defaultdict(list)
    for row in rows:
        grouped[(row["approach"], row["version"])].append(row)

    summary_rows: list[dict] = []
    for (approach, version), group in sorted(grouped.items()):
        scenario_count = len(group)
        success_count = sum(1 for row in group if row["event"] == Event.GOAL_REACHED.value)
        collision_count = sum(1 for row in group if row["event"] == Event.COLLISION.value)
        timeout_count = sum(1 for row in group if row["event"] == Event.TIMEOUT.value)
        invalid_count = sum(1 for row in group if row["event"] == "INVALID_CONTROLLER")

        summary_rows.append(
            {
                "approach": approach,
                "version": version,
                "challenge_type": "all",
                "scenarios": scenario_count,
                "success_count": success_count,
                "success_rate": round(success_count / scenario_count, 3),
                "collision_count": collision_count,
                "collision_rate": round(collision_count / scenario_count, 3),
                "timeout_count": timeout_count,
                "timeout_rate": round(timeout_count / scenario_count, 3),
                "invalid_count": invalid_count,
                "invalid_rate": round(invalid_count / scenario_count, 3),
                "average_steps": round(sum(row["steps"] for row in group) / scenario_count, 3),
                "average_optimal_steps": _average_optional([_row_optimal_steps(row) for row in group]),
                "efficiency_score": _average_optional([_row_efficiency_score(row) for row in group]),
            }
        )

    return summary_rows


def build_chain_summary(rows: list[dict]) -> list[dict]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[row["approach"]].append(row)

    summary_rows: list[dict] = []
    for approach, group in sorted(grouped.items()):
        runs = len(group)
        success_count = _count(group, lambda row: row["event"] == Event.GOAL_REACHED.value)
        collision_count = _count(group, lambda row: row["event"] == Event.COLLISION.value)
        timeout_count = _count(group, lambda row: row["event"] == Event.TIMEOUT.value)
        invalid_count = _count(group, lambda row: row["event"] == "INVALID_CONTROLLER")

        summary_rows.append(
            {
                "approach": approach,
                "development_method": _approach_method(approach),
                "versions_seen": len({row["version"] for row in group}),
                "runs": runs,
                "success_rate": round(success_count / runs, 3),
                "collision_rate": round(collision_count / runs, 3),
                "timeout_rate": round(timeout_count / runs, 3),
                "invalid_rate": round(invalid_count / runs, 3),
                "average_steps": round(sum(row["steps"] for row in group) / runs, 3),
                "average_optimal_steps": _average_optional([_row_optimal_steps(row) for row in group]),
                "efficiency_score": _average_optional([_row_efficiency_score(row) for row in group]),
            }
        )

    return summary_rows


def build_pairwise_changes(rows: list[dict]) -> list[dict]:
    grouped_by_approach: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped_by_approach[row["approach"]].append(row)

    pairwise_rows: list[dict] = []

    for approach in sorted(grouped_by_approach):
        approach_rows = grouped_by_approach[approach]
        versions = sorted({row["version"] for row in approach_rows})

        for index in range(1, len(versions)):
            from_version = versions[index - 1]
            to_version = versions[index]
            prev_rows = {
                row["scenario_id"]: row
                for row in approach_rows
                if row["version"] == from_version
            }
            curr_rows = {
                row["scenario_id"]: row
                for row in approach_rows
                if row["version"] == to_version
            }

            for scenario_id in sorted(set(prev_rows) & set(curr_rows)):
                prev_row = prev_rows[scenario_id]
                curr_row = curr_rows[scenario_id]
                drift = _compare_rows(prev_row, curr_row)

                pairwise_rows.append(
                    {
                        "approach": approach,
                        "from_version": from_version,
                        "to_version": to_version,
                        "scenario_id": scenario_id,
                        "scenario_name": prev_row["scenario_name"],
                        "difficulty": prev_row["difficulty"],
                        "challenge_type": prev_row["challenge_type"],
                        "description": prev_row["description"],
                        "step_budget": prev_row["step_budget"],
                        "event_prev": prev_row["event"],
                        "event_curr": curr_row["event"],
                        "steps_prev": prev_row["steps"],
                        "steps_curr": curr_row["steps"],
                        "step_delta": drift.step_delta,
                        "trace_changed": drift.trace_changed,
                        "event_changed": drift.event_changed,
                        "steps_changed": drift.steps_changed,
                        "pure_trace_drift": _is_pure_trace_drift_flags(
                            drift.trace_changed,
                            drift.event_changed,
                            drift.steps_changed,
                        ),
                        "outcome_drift": drift.event_changed,
                        "change_type": drift.change_type,
                    }
                )

    return pairwise_rows


def build_pairwise_summary(pairwise_rows: list[dict]) -> list[dict]:
    grouped: dict[tuple[str, int, int], list[dict]] = defaultdict(list)
    for row in pairwise_rows:
        grouped[(row["approach"], row["from_version"], row["to_version"])].append(row)

    summary_rows: list[dict] = []
    for (approach, from_version, to_version), group in sorted(grouped.items()):
        comparisons = len(group)
        drift_count = _count(group, lambda row: row["change_type"] in {"drift", "regression", "improvement"})
        regression_count = _count(group, lambda row: row["change_type"] == "regression")
        improvement_count = _count(group, lambda row: row["change_type"] == "improvement")
        pure_trace_drift_count = _count(group, lambda row: row["pure_trace_drift"])
        outcome_drift_count = _count(group, lambda row: row["outcome_drift"])

        summary_rows.append(
            {
                "approach": approach,
                "from_version": from_version,
                "to_version": to_version,
                "challenge_type": "all",
                "comparisons": comparisons,
                "drift_count": drift_count,
                "drift_rate": round(drift_count / comparisons, 3),
                "regression_count": regression_count,
                "regression_rate": round(regression_count / comparisons, 3),
                "improvement_count": improvement_count,
                "improvement_rate": round(improvement_count / comparisons, 3),
                "outcome_drift_count": outcome_drift_count,
                "outcome_drift_rate": round(outcome_drift_count / comparisons, 3),
                "pure_trace_drift_count": pure_trace_drift_count,
                "pure_trace_drift_rate": round(pure_trace_drift_count / comparisons, 3),
            }
        )

    return summary_rows


def build_difficulty_summary(rows: list[dict], pairwise_rows: list[dict]) -> list[dict]:
    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in rows:
        grouped[(row["approach"], row["difficulty"])].append(row)

    pairwise_grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in pairwise_rows:
        pairwise_grouped[(row["approach"], row["difficulty"])].append(row)

    summary_rows: list[dict] = []
    for (approach, difficulty), group in sorted(grouped.items()):
        runs = len(group)
        difficulty_pairwise = pairwise_grouped.get((approach, difficulty), [])
        success_count = _count(group, lambda row: row["event"] == Event.GOAL_REACHED.value)
        collision_count = _count(group, lambda row: row["event"] == Event.COLLISION.value)
        invalid_count = _count(group, lambda row: row["event"] == "INVALID_CONTROLLER")
        timeout_count = _count(group, lambda row: row["event"] == Event.TIMEOUT.value)

        summary_rows.append(
            {
                "approach": approach,
                "difficulty": difficulty,
                "challenge_type": "all",
                "versions_seen": len({row["version"] for row in group}),
                "runs": runs,
                "success_rate": round(success_count / runs, 3),
                "collision_rate": round(collision_count / runs, 3),
                "timeout_rate": round(timeout_count / runs, 3),
                "invalid_rate": round(invalid_count / runs, 3),
                "average_steps": round(sum(row["steps"] for row in group) / runs, 3),
                "average_optimal_steps": _average_optional([_row_optimal_steps(row) for row in group]),
                "efficiency_score": _average_optional([_row_efficiency_score(row) for row in group]),
                "drift_rate": _rate(
                    difficulty_pairwise,
                    lambda row: row["change_type"] in {"drift", "regression", "improvement"},
                ),
                "regression_rate": _rate(difficulty_pairwise, lambda row: row["change_type"] == "regression"),
                "improvement_rate": _rate(difficulty_pairwise, lambda row: row["change_type"] == "improvement"),
                "pure_trace_drift_rate": _rate(
                    difficulty_pairwise,
                    lambda row: row["pure_trace_drift"],
                ),
            }
        )

    return summary_rows


def build_challenge_type_summary(rows: list[dict], pairwise_rows: list[dict]) -> list[dict]:
    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in rows:
        grouped[(row["approach"], row["challenge_type"])].append(row)

    pairwise_grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in pairwise_rows:
        pairwise_grouped[(row["approach"], row["challenge_type"])].append(row)

    summary_rows: list[dict] = []
    for (approach, challenge_type), group in sorted(grouped.items()):
        challenge_pairwise = pairwise_grouped.get((approach, challenge_type), [])
        runs = len(group)
        success_count = _count(group, lambda row: row["event"] == Event.GOAL_REACHED.value)
        collision_count = _count(group, lambda row: row["event"] == Event.COLLISION.value)
        timeout_count = _count(group, lambda row: row["event"] == Event.TIMEOUT.value)
        invalid_count = _count(group, lambda row: row["event"] == "INVALID_CONTROLLER")

        summary_rows.append(
            {
                "approach": approach,
                "challenge_type": challenge_type,
                "versions_seen": len({row["version"] for row in group}),
                "runs": runs,
                "success_rate": round(success_count / runs, 3),
                "collision_rate": round(collision_count / runs, 3),
                "timeout_rate": round(timeout_count / runs, 3),
                "invalid_rate": round(invalid_count / runs, 3),
                "average_steps": round(sum(row["steps"] for row in group) / runs, 3),
                "average_optimal_steps": _average_optional([_row_optimal_steps(row) for row in group]),
                "efficiency_score": _average_optional([_row_efficiency_score(row) for row in group]),
                "drift_rate": _rate(
                    challenge_pairwise,
                    lambda row: row["change_type"] in {"drift", "regression", "improvement"},
                ),
                "regression_rate": _rate(
                    challenge_pairwise,
                    lambda row: row["change_type"] == "regression",
                ),
                "improvement_rate": _rate(
                    challenge_pairwise,
                    lambda row: row["change_type"] == "improvement",
                ),
                "pure_trace_drift_rate": _rate(
                    challenge_pairwise,
                    lambda row: row["pure_trace_drift"],
                ),
            }
        )

    return summary_rows


def build_consistency_summary(rows: list[dict]) -> list[dict]:
    grouped: dict[tuple[str, int, str], list[dict]] = defaultdict(list)
    for row in rows:
        grouped[(row["approach"], row["scenario_id"], row["scenario_name"])].append(row)

    summary_rows: list[dict] = []
    for (approach, scenario_id, scenario_name), group in sorted(grouped.items()):
        outcome_counts: dict[str, int] = defaultdict(int)
        for row in group:
            outcome_counts[str(row["event"])] += 1

        dominant_outcome, dominant_count = min(
            outcome_counts.items(),
            key=lambda item: (-item[1], item[0]),
        )

        summary_rows.append(
            {
                "approach": approach,
                "scenario_id": scenario_id,
                "scenario_name": scenario_name,
                "dominant_outcome": dominant_outcome,
                "consistency_score": round(dominant_count / len(group), 3),
                "consistency_interpretation": _consistency_interpretation(
                    dominant_outcome,
                    dominant_count / len(group),
                ),
            }
        )

    return summary_rows


def build_success_preservation_summary(rows: list[dict]) -> list[dict]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[row["approach"]].append(row)

    summary_rows: list[dict] = []
    for approach, group in sorted(grouped.items()):
        versions = sorted({row["version"] for row in group})
        by_scenario: dict[int, dict[int, dict]] = defaultdict(dict)
        scenario_meta: dict[int, dict] = {}

        for row in group:
            by_scenario[row["scenario_id"]][row["version"]] = row
            scenario_meta[row["scenario_id"]] = row

        for scenario_id in sorted(by_scenario):
            version_rows = by_scenario[scenario_id]
            meta = scenario_meta[scenario_id]

            for from_version in versions:
                current_row = version_rows.get(from_version)
                if current_row is None or current_row["event"] != Event.GOAL_REACHED.value:
                    continue

                later_rows = [
                    version_rows[version]
                    for version in versions
                    if version > from_version and version in version_rows
                ]
                preserved_success_count = _count(
                    later_rows,
                    lambda row: row["event"] == Event.GOAL_REACHED.value,
                )
                later_versions = len(later_rows)

                summary_rows.append(
                    {
                        "approach": approach,
                        "scenario_id": scenario_id,
                        "scenario_name": meta["scenario_name"],
                        "difficulty": meta["difficulty"],
                        "challenge_type": meta["challenge_type"],
                        "from_version": from_version,
                        "later_versions": later_versions,
                        "preserved_success_count": preserved_success_count,
                        "success_preservation_rate": (
                            round(preserved_success_count / later_versions, 3)
                            if later_versions
                            else None
                        ),
                    }
                )

    return summary_rows


def build_experiment_log(rows: list[dict]) -> list[dict]:
    grouped: dict[tuple[str, int], list[dict]] = defaultdict(list)
    for row in rows:
        grouped[(row["approach"], row["version"])].append(row)

    log_rows: list[dict] = []
    for (approach, version), group in sorted(grouped.items()):
        scenarios = len(group)
        success_count = _count(group, lambda row: row["event"] == Event.GOAL_REACHED.value)
        collision_count = _count(group, lambda row: row["event"] == Event.COLLISION.value)
        timeout_count = _count(group, lambda row: row["event"] == Event.TIMEOUT.value)
        invalid_count = _count(group, lambda row: row["event"] == "INVALID_CONTROLLER")

        log_rows.append(
            {
                "chain": approach,
                "development_method": _approach_method(approach),
                "version": version,
                "validity_status": _validity_status(scenarios, invalid_count),
                "controller_path": group[0]["controller_path"],
                "scenarios": scenarios,
                "success_count": success_count,
                "success_rate": round(success_count / scenarios, 3),
                "collision_count": collision_count,
                "collision_rate": round(collision_count / scenarios, 3),
                "timeout_count": timeout_count,
                "timeout_rate": round(timeout_count / scenarios, 3),
                "invalid_count": invalid_count,
                "invalid_rate": round(invalid_count / scenarios, 3),
                "average_steps": round(sum(row["steps"] for row in group) / scenarios, 3),
                "average_optimal_steps": _average_optional([_row_optimal_steps(row) for row in group]),
                "efficiency_score": _average_optional([_row_efficiency_score(row) for row in group]),
            }
        )

    return log_rows


def filter_rows(
    rows: list[dict],
    *,
    approaches: set[str] | None = None,
    prefix: str | None = None,
) -> list[dict]:
    filtered_rows = rows

    if approaches is not None:
        filtered_rows = [row for row in filtered_rows if row["approach"] in approaches]

    if prefix is not None:
        filtered_rows = [row for row in filtered_rows if row["approach"].startswith(prefix)]

    return filtered_rows


def distinct_approaches(rows: list[dict]) -> list[str]:
    return sorted({row["approach"] for row in rows})


def save_analysis_outputs(output_dir: str | Path, **tables: list[dict]) -> list[Path]:
    output_dir = Path(output_dir)
    saved_paths: list[Path] = []

    for filename, rows in tables.items():
        output_path = output_dir / filename
        fieldnames = list(rows[0].keys()) if rows else []
        with output_path.open("w", newline="", encoding="utf-8") as handle:
            if fieldnames:
                writer = csv.DictWriter(handle, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
        saved_paths.append(output_path)

    return saved_paths


def format_table(rows: list[dict]) -> str:
    if not rows:
        return "(none)"

    headers = list(rows[0].keys())
    widths = {
        header: max(len(header), *(len(str(row[header])) for row in rows))
        for header in headers
    }

    lines = [
        " ".join(header.ljust(widths[header]) for header in headers),
        " ".join("-" * widths[header] for header in headers),
    ]

    for row in rows:
        lines.append(" ".join(str(row[header]).ljust(widths[header]) for header in headers))

    return "\n".join(lines)


def _count(rows: list[dict], predicate: Callable[[dict], bool]) -> int:
    return sum(1 for row in rows if predicate(row))


def _rate(rows: list[dict], predicate: Callable[[dict], bool]) -> float | None:
    if not rows:
        return None
    return round(_count(rows, predicate) / len(rows), 3)


def _average_optional(values: list[float | int | None]) -> float | None:
    present = [float(value) for value in values if value is not None]
    if not present:
        return None
    return round(sum(present) / len(present), 3)


def _row_optimal_steps(row: dict) -> int | None:
    optimal_steps = row.get("optimal_steps")
    if optimal_steps is not None:
        return int(optimal_steps)
    return _optimal_steps_by_scenario_id().get(int(row["scenario_id"]))


def _row_efficiency_score(row: dict) -> float | None:
    efficiency_score = row.get("efficiency_score")
    if efficiency_score is not None:
        return float(efficiency_score)
    return _compute_efficiency_score(
        str(row["event"]),
        int(row["steps"]),
        _row_optimal_steps(row),
    )


def _is_pure_trace_drift_flags(trace_changed: bool, event_changed: bool, steps_changed: bool) -> bool:
    return trace_changed and not event_changed and not steps_changed


def _approach_method(approach: str) -> str:
    base_name = _approach_base_name(approach)
    if base_name.startswith("pdd"):
        return "PDD"
    if base_name.startswith("sdd"):
        return "SDD"
    return "OTHER"


def _validity_status(scenarios: int, invalid_count: int) -> str:
    if invalid_count == 0:
        return "valid"
    if invalid_count == scenarios:
        return "all_invalid"
    return "partially_invalid"


def _consistency_interpretation(dominant_outcome: str, consistency_score: float) -> str:
    if consistency_score >= 0.8 and dominant_outcome == Event.GOAL_REACHED.value:
        return "high_consistency_reliable_success"
    if consistency_score >= 0.8:
        return "high_consistency_stagnation"
    return "mixed_or_variable"


def _approach_provider(approach: str) -> str | None:
    if approach.startswith("gpt_"):
        return "gpt"
    if approach.startswith("opus_"):
        return "opus"
    return None


def _approach_base_name(approach: str) -> str:
    provider = _approach_provider(approach)
    if provider is None:
        return approach
    return approach[len(provider) + 1 :]


def _compare_rows(prev_row: dict, curr_row: dict):
    if prev_row["event"] != "INVALID_CONTROLLER" and curr_row["event"] != "INVALID_CONTROLLER":
        return compare_runs(_row_to_record(prev_row), _row_to_record(curr_row))

    return _InvalidDrift(prev_row, curr_row)


class _InvalidDrift:
    def __init__(self, prev_row: dict, curr_row: dict):
        self.step_delta = curr_row["steps"] - prev_row["steps"]
        self.trace_changed = False
        self.event_changed = prev_row["event"] != curr_row["event"]
        self.steps_changed = self.step_delta != 0

        prev_invalid = prev_row["event"] == "INVALID_CONTROLLER"
        curr_invalid = curr_row["event"] == "INVALID_CONTROLLER"

        if not prev_invalid and curr_invalid:
            self.change_type = "regression"
        elif prev_invalid and not curr_invalid:
            self.change_type = "improvement"
        elif prev_invalid and curr_invalid and prev_row.get("error") == curr_row.get("error"):
            self.change_type = "same"
        else:
            self.change_type = "drift"


def _row_to_record(row: dict) -> ScenarioRunRecord:
    return ScenarioRunRecord(
        event=Event(normalise_token(row["event"])),
        steps=int(row["steps"]),
        trace=TraceRecord(
            positions=[tuple(position) for position in row["position_trace"]],
            actions=[Action(normalise_token(action)) for action in row["action_trace"]],
            headings=[Heading(normalise_token(heading)) for heading in row["heading_trace"]],
        ),
    )


def _compute_efficiency_score(event: str, steps: int, optimal_steps: int | None) -> float | None:
    if optimal_steps is None:
        return None
    if event != Event.GOAL_REACHED.value or steps <= 0:
        return 0.0
    return round(min(1.0, optimal_steps / steps), 3)


@lru_cache(maxsize=1)
def _optimal_steps_by_scenario_id() -> dict[int, int]:
    specs = list(get_benchmark_suite()) + list(get_benchmark_suite_2())
    return {
        spec.scenario_id: _bfs_optimal_steps(
            width=spec.scenario.width,
            height=spec.scenario.height,
            start=spec.scenario.start,
            goal=spec.scenario.goal,
            obstacles=spec.scenario.obstacles,
        )
        for spec in specs
    }


def _bfs_optimal_steps(
    *,
    width: int,
    height: int,
    start: tuple[int, int],
    goal: tuple[int, int],
    obstacles: set[tuple[int, int]],
) -> int | None:
    queue = deque([(start, 0)])
    visited = {start}

    while queue:
        (x, y), distance = queue.popleft()
        if (x, y) == goal:
            return distance

        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            nxt = (nx, ny)
            if not (0 <= nx < width and 0 <= ny < height):
                continue
            if nxt in obstacles or nxt in visited:
                continue
            visited.add(nxt)
            queue.append((nxt, distance + 1))

    return None
