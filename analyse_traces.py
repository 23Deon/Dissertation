from __future__ import annotations

from pathlib import Path

from gridbot.eval.analysis import (
    _approach_base_name,
    _approach_method,
    _approach_provider,
    build_chain_summary,
    build_challenge_type_summary,
    build_consistency_summary,
    build_difficulty_summary,
    build_experiment_log,
    build_pairwise_changes,
    build_pairwise_summary,
    build_success_preservation_summary,
    build_version_summary,
    filter_rows,
    format_table,
    load_results,
    save_analysis_outputs,
)


RESULTS_FILE = "results.csv"
FALLBACK_RESULTS_FILE = "results.generated.csv"


def main() -> None:
    csv_path = _find_results_file()

    results_df = load_results(csv_path)
    chain_summary = build_chain_summary(results_df)
    version_summary = build_version_summary(results_df)
    pairwise_changes = build_pairwise_changes(results_df)
    pairwise_summary = build_pairwise_summary(pairwise_changes)
    difficulty_summary = build_difficulty_summary(results_df, pairwise_changes)
    challenge_type_summary = build_challenge_type_summary(results_df, pairwise_changes)
    consistency_summary = build_consistency_summary(results_df)
    success_preservation_summary = build_success_preservation_summary(results_df)
    experiment_log = build_experiment_log(results_df)

    print("\n=== CHAIN SUMMARY ===")
    print(format_table(chain_summary))

    print("\n=== VERSION SUMMARY ===")
    print(format_table(version_summary))

    print("\n=== VERSION-TO-VERSION SUMMARY ===")
    if not pairwise_summary:
        print("Not enough versions to compare.")
    else:
        print(format_table(pairwise_summary))

    print("\n=== DIFFICULTY SUMMARY ===")
    print(format_table(difficulty_summary))

    print("\n=== CHALLENGE TYPE SUMMARY ===")
    print(format_table(challenge_type_summary))

    print("\n=== CONSISTENCY SUMMARY ===")
    print(format_table(consistency_summary))

    print("\n=== SUCCESS PRESERVATION SUMMARY ===")
    print(format_table(success_preservation_summary))

    print("\n=== SCENARIO-LEVEL PAIRWISE CHANGES ===")
    if not pairwise_changes:
        print("Not enough versions to compare.")
    else:
        print(format_table(pairwise_changes))

    saved_paths = save_analysis_outputs(
        ".",
        **{
            "chain_summary.csv": chain_summary,
            "version_summary.csv": version_summary,
            "pairwise_changes.csv": pairwise_changes,
            "pairwise_summary.csv": pairwise_summary,
            "difficulty_summary.csv": difficulty_summary,
            "challenge_type_summary.csv": challenge_type_summary,
            "consistency_summary.csv": consistency_summary,
            "success_preservation_summary.csv": success_preservation_summary,
            "experiment_log.csv": experiment_log,
        },
    )

    scoped_paths = _save_scoped_outputs(results_df)
    saved_paths.extend(scoped_paths)

    print("\nSaved:")
    for path in saved_paths:
        print(f"- {path.name}")


def _find_results_file() -> Path:
    primary = Path(RESULTS_FILE)
    fallback = Path(FALLBACK_RESULTS_FILE)

    if primary.exists():
        return primary
    if fallback.exists():
        return fallback

    if not primary.exists() and not fallback.exists():
        raise FileNotFoundError(
            f"Could not find {RESULTS_FILE} or {FALLBACK_RESULTS_FILE} in the current folder."
        )
    return fallback


def _save_scoped_outputs(rows: list[dict]) -> list[Path]:
    saved_paths: list[Path] = []

    scopes: list[tuple[str, list[dict]]] = []

    all_approaches = sorted({row["approach"] for row in rows})
    generated_approaches = [approach for approach in all_approaches if _approach_method(approach) in {"PDD", "SDD"}]

    by_method: dict[str, list[str]] = {}
    by_provider_method: dict[tuple[str, str], list[str]] = {}
    by_base_name: dict[str, list[str]] = {}

    for approach in generated_approaches:
        method = _approach_method(approach).lower()
        provider = _approach_provider(approach)
        base_name = _approach_base_name(approach)

        by_method.setdefault(method, []).append(approach)
        by_base_name.setdefault(base_name, []).append(approach)
        if provider is not None:
            by_provider_method.setdefault((provider, method), []).append(approach)

    for method, approaches in sorted(by_method.items()):
        scopes.append((method, filter_rows(rows, approaches=set(approaches))))

    for (provider, method), approaches in sorted(by_provider_method.items()):
        scopes.append((f"{provider}_{method}_all", filter_rows(rows, approaches=set(approaches))))

    for base_name, approaches in sorted(by_base_name.items()):
        scopes.append((base_name, filter_rows(rows, approaches=set(approaches))))

    for approach in generated_approaches:
        scopes.append((approach, filter_rows(rows, approaches={approach})))

    for label, scoped_rows in scopes:
        if not scoped_rows:
            continue

        version_summary = build_version_summary(scoped_rows)
        pairwise_changes = build_pairwise_changes(scoped_rows)
        pairwise_summary = build_pairwise_summary(pairwise_changes)
        difficulty_summary = build_difficulty_summary(scoped_rows, pairwise_changes)
        challenge_type_summary = build_challenge_type_summary(scoped_rows, pairwise_changes)
        consistency_summary = build_consistency_summary(scoped_rows)
        success_preservation_summary = build_success_preservation_summary(scoped_rows)
        experiment_log = build_experiment_log(scoped_rows)
        chain_summary = build_chain_summary(scoped_rows)

        saved_paths.extend(
            save_analysis_outputs(
                ".",
                **{
                    f"{label}_chain_summary.csv": chain_summary,
                    f"{label}_version_summary.csv": version_summary,
                    f"{label}_pairwise_changes.csv": pairwise_changes,
                    f"{label}_pairwise_summary.csv": pairwise_summary,
                    f"{label}_difficulty_summary.csv": difficulty_summary,
                    f"{label}_challenge_type_summary.csv": challenge_type_summary,
                    f"{label}_consistency_summary.csv": consistency_summary,
                    f"{label}_success_preservation_summary.csv": success_preservation_summary,
                    f"{label}_experiment_log.csv": experiment_log,
                },
            )
        )

    return saved_paths


if __name__ == "__main__":
    main()
