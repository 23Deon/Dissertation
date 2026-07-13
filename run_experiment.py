from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from gridbot.eval.benchmark_suite import get_benchmark_suite, validate_benchmark_suite
from gridbot.eval.harness import run_scenario_record
from gridbot.eval.load_controller import load_controller
from gridbot.eval.results import ResultRow, invalid_controller_row, save_results, timed_out_row


OUTPUT_CSV = "results.csv"
CONTROLLERS_DIR = Path("controllers")
VERSION_PATTERN = re.compile(r"controller_v(?P<version>\d+)\.py$")
SCENARIO_WALL_CLOCK_TIMEOUT_SECONDS = float(os.getenv("GRIDBOT_SCENARIO_TIMEOUT_SECONDS", "10.0"))
WORKER_OUTPUT_DIR = Path(".worker_results")


@dataclass(frozen=True)
class ControllerSpec:
    approach: str
    version: int
    path: Path


def discover_controller_specs(base_dir: Path = CONTROLLERS_DIR) -> list[ControllerSpec]:
    specs: list[ControllerSpec] = []

    if not base_dir.exists():
        return specs

    for path in sorted(base_dir.glob("*/*.py")):
        match = VERSION_PATTERN.match(path.name)
        if not match:
            continue

        specs.append(
            ControllerSpec(
                approach=normalise_approach_name(path.parent.name),
                version=int(match.group("version")),
                path=path,
            )
        )

    return sorted(specs, key=lambda spec: (spec.approach, spec.version))


def normalise_approach_name(folder_name: str) -> str:
    if folder_name.startswith(("gpt_", "opus_")):
        return folder_name
    if folder_name.startswith(("pdd", "sdd")):
        return f"gpt_{folder_name}"
    return folder_name


def main() -> None:
    print("Running experiment...")

    scenario_specs = get_benchmark_suite()
    validate_benchmark_suite(scenario_specs)
    controller_specs = discover_controller_specs()

    if not controller_specs:
        raise FileNotFoundError(f"No controller versions found under {CONTROLLERS_DIR}")

    rows: list[ResultRow] = []

    for controller_spec in controller_specs:
        print(f"\n--- Running {controller_spec.approach} v{controller_spec.version} ---")
        per_controller_rows = execute_controller_spec(controller_spec, scenario_specs)
        rows.extend(per_controller_rows)

        _print_controller_summary(per_controller_rows)

    if not rows:
        raise RuntimeError("No valid controllers could be loaded, so no results were produced.")

    output_path = save_results(rows, OUTPUT_CSV)
    print(f"\nResults saved to {output_path}")


def _try_load_controller(controller_path: Path):
    try:
        return load_controller(str(controller_path)), ""
    except Exception as exc:
        print(f"Skipping invalid controller {controller_path.as_posix()}: {exc}")
        return None, str(exc)


def execute_controller_spec(
    controller_spec: ControllerSpec,
    scenario_specs: list,
    scenario_timeout_seconds: float = SCENARIO_WALL_CLOCK_TIMEOUT_SECONDS,
) -> list[ResultRow]:
    controller, load_error = _try_load_controller(controller_spec.path)
    if controller is None:
        print(f"Recording invalid controller {controller_spec.path.as_posix()}: {load_error}")
        return [
            invalid_controller_row(
                approach=controller_spec.approach,
                version=controller_spec.version,
                controller_path=controller_spec.path.as_posix(),
                spec=scenario_spec,
                error=load_error,
            )
            for scenario_spec in scenario_specs
        ]

    del controller

    WORKER_OUTPUT_DIR.mkdir(exist_ok=True)
    worker_output_path = WORKER_OUTPUT_DIR / (
        f"{controller_spec.approach}_v{controller_spec.version}_{os.getpid()}.jsonl"
    )
    worker = subprocess.Popen(
        [
            sys.executable,
            __file__,
            "--worker",
            str(controller_spec.path),
            str(worker_output_path),
            *[str(spec.scenario_id) for spec in scenario_specs],
        ],
        cwd=Path(__file__).parent,
    )

    rows: list[ResultRow] = []
    offset = 0

    try:
        for index, scenario_spec in enumerate(scenario_specs):
            message, offset = _wait_for_worker_message(
                worker,
                worker_output_path,
                offset,
                scenario_timeout_seconds,
            )
            if message is None:
                timeout_message = (
                    f"wall-clock timeout after {scenario_timeout_seconds:.1f}s "
                    f"while running scenario {scenario_spec.scenario_id}"
                )
                _terminate_worker(worker)
                rows.append(
                    timed_out_row(
                        approach=controller_spec.approach,
                        version=controller_spec.version,
                        controller_path=controller_spec.path.as_posix(),
                        spec=scenario_spec,
                        error=timeout_message,
                    )
                )
                for remaining_spec in scenario_specs[index + 1 :]:
                    rows.append(
                        timed_out_row(
                            approach=controller_spec.approach,
                            version=controller_spec.version,
                            controller_path=controller_spec.path.as_posix(),
                            spec=remaining_spec,
                            error="controller process terminated after earlier wall-clock timeout",
                        )
                    )
                return rows

            if message["kind"] == "load_error":
                print(f"Recording invalid controller {controller_spec.path.as_posix()}: {message['error']}")
                rows.extend(
                    invalid_controller_row(
                        approach=controller_spec.approach,
                        version=controller_spec.version,
                        controller_path=controller_spec.path.as_posix(),
                        spec=remaining_spec,
                        error=message["error"],
                    )
                    for remaining_spec in scenario_specs[index:]
                )
                return rows

            if message["kind"] == "runtime_error":
                rows.append(
                    invalid_controller_row(
                        approach=controller_spec.approach,
                        version=controller_spec.version,
                        controller_path=controller_spec.path.as_posix(),
                        spec=scenario_spec,
                        error=message["error"],
                    )
                )
                continue

            rows.append(_result_row_from_worker_message(controller_spec, scenario_spec, message))

        return rows
    finally:
        _terminate_worker(worker)
        try:
            worker_output_path.unlink(missing_ok=True)
        except PermissionError:
            pass


def _wait_for_worker_message(
    worker: subprocess.Popen,
    worker_output_path: Path,
    offset: int,
    timeout_seconds: float,
):
    deadline = time.monotonic() + timeout_seconds

    while time.monotonic() < deadline:
        message, offset = _read_worker_message(worker_output_path, offset)
        if message is not None:
            return message, offset

        if worker.poll() is not None:
            message, offset = _read_worker_message(worker_output_path, offset)
            if message is not None:
                return message, offset
            return None, offset

        time.sleep(0.05)

    return None, offset


def _read_worker_message(worker_output_path: Path, offset: int):
    if not worker_output_path.exists():
        return None, offset

    with worker_output_path.open("r", encoding="utf-8") as handle:
        handle.seek(offset)
        line = handle.readline()
        if not line or not line.endswith("\n"):
            return None, offset
        return json.loads(line), handle.tell()


def _result_row_from_worker_message(controller_spec: ControllerSpec, scenario_spec, message: dict) -> ResultRow:
    positions = message["positions"]
    actions = message["actions"]
    headings = message["headings"]

    return ResultRow(
        approach=controller_spec.approach,
        version=controller_spec.version,
        controller_path=controller_spec.path.as_posix(),
        scenario_id=scenario_spec.scenario_id,
        scenario_name=scenario_spec.name,
        difficulty=scenario_spec.difficulty,
        challenge_type=scenario_spec.challenge_type,
        description=scenario_spec.description,
        step_budget=scenario_spec.step_budget,
        event=message["event"],
        steps=message["steps"],
        trace_len=len(actions),
        action_trace=json.dumps(actions),
        position_trace=json.dumps(positions),
        heading_trace=json.dumps(headings),
        error="",
    )


def _controller_worker(controller_path: str, output_path: str, scenario_ids: list[int]) -> int:
    scenario_lookup = {spec.scenario_id: spec for spec in get_benchmark_suite()}

    with Path(output_path).open("w", encoding="utf-8") as handle:
        try:
            controller = load_controller(controller_path)
        except Exception as exc:
            _write_worker_message(handle, {"kind": "load_error", "error": str(exc)})
            return 1

        for scenario_id in scenario_ids:
            scenario_spec = scenario_lookup[scenario_id]
            try:
                record = run_scenario_record(scenario_spec.scenario, controller)
                _write_worker_message(
                    handle,
                    {
                        "kind": "result",
                        "scenario_id": scenario_id,
                        "event": str(record.event),
                        "steps": int(record.steps),
                        "positions": [list(position) for position in record.trace.positions],
                        "actions": [str(action) for action in record.trace.actions],
                        "headings": [str(heading) for heading in record.trace.headings],
                    },
                )
            except Exception as exc:
                _write_worker_message(
                    handle,
                    {
                        "kind": "runtime_error",
                        "scenario_id": scenario_id,
                        "error": f"runtime error: {exc}",
                    },
                )

    return 0


def _write_worker_message(handle, payload: dict) -> None:
    handle.write(json.dumps(payload) + "\n")
    handle.flush()


def _run_worker_from_argv(args: list[str]) -> int:
    controller_path = args[0]
    output_path = args[1]
    scenario_ids = [int(value) for value in args[2:]]
    return _controller_worker(controller_path, output_path, scenario_ids)


def _terminate_worker(worker) -> None:
    if worker.poll() is None:
        worker.terminate()
        try:
            worker.wait(timeout=1.0)
        except subprocess.TimeoutExpired:
            worker.kill()
            worker.wait(timeout=1.0)


def _print_controller_summary(rows: list[ResultRow]) -> None:
    success_count = sum(1 for row in rows if "GOAL_REACHED" in row.event)
    collision_count = sum(1 for row in rows if "COLLISION" in row.event)
    invalid_count = sum(1 for row in rows if row.event == "INVALID_CONTROLLER")
    average_steps = sum(row.steps for row in rows) / len(rows)

    print(f"Successes: {success_count}/{len(rows)}")
    print(f"Collisions: {collision_count}/{len(rows)}")
    print(f"Invalid runs: {invalid_count}/{len(rows)}")
    print(f"Average steps: {average_steps:.2f}")
    print("Per-scenario results:")

    for row in rows:
        print(
            f"  Scenario {row.scenario_id:>2} "
            f"({row.difficulty}, {row.scenario_name}): "
            f"event={row.event}, steps={row.steps}, trace_len={row.trace_len}"
        )


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--worker":
        raise SystemExit(_run_worker_from_argv(sys.argv[2:]))
    main()
