from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

from gridbot.eval.benchmark_suite import get_benchmark_suite


ROOT = Path(__file__).resolve().parents[1]


def load_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def parse_float(value: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def parse_int(value: str) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def normalise_token(value: str) -> str:
    text = str(value).strip()
    if "." in text:
        return text.split(".")[-1]
    return text


def outcome_label(pairwise_row: dict | None) -> str:
    if pairwise_row is None:
        return "initial"

    drift = parse_int(pairwise_row.get("drift_count", "0"))
    reg = parse_int(pairwise_row.get("regression_count", "0"))
    imp = parse_int(pairwise_row.get("improvement_count", "0"))

    if drift == 0:
        return "same"
    if imp > 0 and reg == 0:
        return "improved"
    if reg > 0 and imp == 0:
        return "regressed"
    return "drifted"


def main() -> None:
    version_rows = [
        row
        for row in load_csv(ROOT / "version_summary.csv")
        if row.get("challenge_type") == "all"
    ]
    pairwise_rows = [
        row
        for row in load_csv(ROOT / "pairwise_summary.csv")
        if row.get("challenge_type") == "all"
    ]
    result_rows = load_csv(ROOT / "results.csv")

    pairwise_lookup = {
        (row["approach"], parse_int(row["to_version"])): row
        for row in pairwise_rows
    }

    per_version_rows: list[dict] = []
    final_version_candidates: dict[str, dict] = {}
    result_lookup: dict[tuple[str, int], list[dict]] = defaultdict(list)
    for row in result_rows:
        result_lookup[(row["approach"], parse_int(row["version"]))].append(row)

    for row in version_rows:
        approach = row["approach"]
        version = parse_int(row["version"])
        pairwise_row = pairwise_lookup.get((approach, version))
        enriched = {
            "approach": approach,
            "version": version,
            "scenarios": parse_int(row["scenarios"]),
            "success_count": parse_int(row["success_count"]),
            "success_rate": parse_float(row["success_rate"]),
            "collision_count": parse_int(row["collision_count"]),
            "timeout_count": parse_int(row["timeout_count"]),
            "invalid_count": parse_int(row["invalid_count"]),
            "average_steps": parse_float(row["average_steps"]),
            "outcome_note": outcome_label(pairwise_row),
        }
        per_version_rows.append(enriched)

        if approach not in final_version_candidates or version > final_version_candidates[approach]["version"]:
            final_version_candidates[approach] = enriched

    final_version_rows: list[dict] = []
    for approach, row in sorted(final_version_candidates.items()):
        approach_results = result_lookup[(approach, row["version"])]
        solved = [
            f'{result["scenario_id"]}:{result["scenario_name"]}'
            for result in approach_results
            if "GOAL_REACHED" in result["event"]
        ]
        final_version_rows.append(
            {
                **row,
                "solved_scenarios": ", ".join(solved),
            }
        )

    scenario_metadata_rows = [
        {
            "scenario_id": spec.scenario_id,
            "scenario_name": spec.name,
            "difficulty": spec.difficulty,
            "challenge_type": spec.challenge_type,
            "grid_size": f"{spec.scenario.width}x{spec.scenario.height}",
            "start": str(spec.scenario.start),
            "goal": str(spec.scenario.goal),
            "step_budget": spec.step_budget,
            "obstacles": ", ".join(str(position) for position in sorted(spec.scenario.obstacles)),
        }
        for spec in get_benchmark_suite()
    ]

    matrix_groups = {
        "gpt_pdd": lambda a: a.startswith("gpt_pdd"),
        "gpt_sdd": lambda a: a.startswith("gpt_sdd"),
        "opus_pdd": lambda a: a.startswith("opus_pdd"),
        "opus_sdd": lambda a: a.startswith("opus_sdd"),
    }

    scenario_matrices: dict[str, dict] = {}
    for label, matcher in matrix_groups.items():
        filtered = [row for row in result_rows if matcher(row["approach"])]
        versions = sorted(
            {(row["approach"], parse_int(row["version"])) for row in filtered},
            key=lambda item: (item[0], item[1]),
        )
        version_labels = [f"{approach} v{version}" for approach, version in versions]
        scenario_rows = []
        by_key = {
            (row["scenario_id"], row["approach"], parse_int(row["version"])): row
            for row in filtered
        }
        for spec in get_benchmark_suite():
            matrix_row = {
                "scenario_id": spec.scenario_id,
                "scenario_name": spec.name,
                "difficulty": spec.difficulty,
                "challenge_type": spec.challenge_type,
            }
            for approach, version in versions:
                result = by_key.get((str(spec.scenario_id), approach, version))
                if result is None:
                    cell = ""
                elif normalise_token(result["event"]) == "GOAL_REACHED":
                    cell = f"S ({result['steps']})"
                elif normalise_token(result["event"]) == "INVALID_CONTROLLER":
                    cell = "I"
                else:
                    cell = f"T ({result['steps']})"
                matrix_row[f"{approach} v{version}"] = cell
            scenario_rows.append(matrix_row)
        scenario_matrices[label] = {
            "columns": ["scenario_id", "scenario_name", "difficulty", "challenge_type", *version_labels],
            "rows": scenario_rows,
        }

    payload = {
        "per_version_rows": sorted(per_version_rows, key=lambda row: (row["approach"], row["version"])),
        "final_version_rows": final_version_rows,
        "scenario_metadata_rows": scenario_metadata_rows,
        "scenario_matrices": scenario_matrices,
    }

    output_dir = ROOT / "outputs" / "appendix_tables"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "appendix_tables_data.json"
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(output_path)


if __name__ == "__main__":
    main()
