from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Protocol

from gridbot.eval.record import ScenarioRunRecord


class ScenarioSpecLike(Protocol):
    scenario_id: int
    name: str
    difficulty: str
    challenge_type: str
    description: str
    step_budget: int


@dataclass(frozen=True)
class ResultRow:
    approach: str
    version: int
    controller_path: str
    scenario_id: int
    scenario_name: str
    difficulty: str
    challenge_type: str
    description: str
    step_budget: int
    event: str
    steps: int
    trace_len: int
    action_trace: str
    position_trace: str
    heading_trace: str
    error: str


def record_to_row(
    *,
    approach: str,
    version: int,
    controller_path: str,
    spec: ScenarioSpecLike,
    record: ScenarioRunRecord,
) -> ResultRow:
    return ResultRow(
        approach=approach,
        version=version,
        controller_path=controller_path,
        scenario_id=spec.scenario_id,
        scenario_name=spec.name,
        difficulty=spec.difficulty,
        challenge_type=spec.challenge_type,
        description=spec.description,
        step_budget=spec.step_budget,
        event=str(record.event),
        steps=int(record.steps),
        trace_len=record.trace.trace_len,
        action_trace=json.dumps([str(action) for action in record.trace.actions]),
        position_trace=json.dumps([list(position) for position in record.trace.positions]),
        heading_trace=json.dumps([str(heading) for heading in record.trace.headings]),
        error="",
    )


def invalid_controller_row(
    *,
    approach: str,
    version: int,
    controller_path: str,
    spec: ScenarioSpecLike,
    error: str,
) -> ResultRow:
    return ResultRow(
        approach=approach,
        version=version,
        controller_path=controller_path,
        scenario_id=spec.scenario_id,
        scenario_name=spec.name,
        difficulty=spec.difficulty,
        challenge_type=spec.challenge_type,
        description=spec.description,
        step_budget=spec.step_budget,
        event="INVALID_CONTROLLER",
        steps=0,
        trace_len=0,
        action_trace="[]",
        position_trace="[]",
        heading_trace="[]",
        error=error,
    )


def timed_out_row(
    *,
    approach: str,
    version: int,
    controller_path: str,
    spec: ScenarioSpecLike,
    error: str,
) -> ResultRow:
    return ResultRow(
        approach=approach,
        version=version,
        controller_path=controller_path,
        scenario_id=spec.scenario_id,
        scenario_name=spec.name,
        difficulty=spec.difficulty,
        challenge_type=spec.challenge_type,
        description=spec.description,
        step_budget=spec.step_budget,
        event="TIMEOUT",
        steps=spec.step_budget,
        trace_len=0,
        action_trace="[]",
        position_trace="[]",
        heading_trace="[]",
        error=error,
    )


def save_results(rows: Iterable[ResultRow], csv_path: str | Path) -> Path:
    rows = list(rows)
    if not rows:
        raise ValueError("No results to save")

    output_path = Path(csv_path)
    fieldnames = list(asdict(rows[0]).keys())

    try:
        _write_rows(output_path, rows, fieldnames)
    except PermissionError:
        fallback_path = output_path.with_name(f"{output_path.stem}.generated{output_path.suffix}")
        _write_rows(fallback_path, rows, fieldnames)
        return fallback_path

    return output_path


def _write_rows(path: Path, rows: list[ResultRow], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))
