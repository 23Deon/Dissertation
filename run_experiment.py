print("Running experiment...")

import csv

from gridbot.eval.scenario import Scenario
from gridbot.eval.suite import run_suite
from gridbot.eval.load_controller import load_controller


def main():
    print("Setting up scenarios...")

    scenarios = [
    Scenario(3, 3, set(), (0, 0), (2, 0)),        # easy straight line
    Scenario(3, 3, set(), (0, 0), (0, 2)),        # requires turning south
    Scenario(3, 3, {(1, 0)}, (0, 0), (2, 0)),     # blocked directly ahead
    Scenario(4, 4, set(), (2, 2), (0, 2)),        # requires turning west
    Scenario(5, 5, set(), (1, 1), (1, 4)),   
    Scenario(6, 6, set(), (3, 3), (3, 0)),                    # long north route
    Scenario(6, 6, set(), (4, 1), (1, 1)),                    # long west route
    Scenario(6, 6, {(2, 1)}, (1, 1), (4, 1)),                 # obstacle on direct east path
    Scenario(6, 6, {(2, 2), (3, 2), (4, 2)}, (1, 2), (5, 2)), # obstacle wall across route
    Scenario(7, 7, {(3, 1), (3, 2), (3, 3)}, (1, 1), (5, 5)), # diagonal-style goal with blocking column     # longer vertical route
]

    controllers = {
        "PDD v1": "controllers/pdd/controller_v1.py",
        "PDD v2": "controllers/pdd/controller_v2.py",
        "PDD v3": "controllers/pdd/controller_v3.py",
        "PDD v4": "controllers/pdd/controller_v4.py",   
        "PDD v5": "controllers/pdd/controller_v5.py",
        "SDD v1": "controllers/sdd/controller_v1.py",
    }

    with open("results.csv", "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["controller", "scenario", "event", "steps", "trace_len"])

        for name, path in controllers.items():
            print(f"\n--- Running {name} ---")

            controller = load_controller(path)
            result = run_suite(scenarios, controller)

            print("Successes:", result.success_count)
            print("Collisions:", result.collision_count)
            print("Total steps:", result.total_steps)
            print("Average steps:", result.average_steps)

            print("Per-scenario results:")
            for i, scenario_result in enumerate(result.results, start=1):
                print(
                    f"  Scenario {i}: "
                    f"event={scenario_result.event}, "
                    f"steps={scenario_result.steps}, "
                    f"trace_len={scenario_result.trace_len}"
                )

                writer.writerow([
                    name,
                    i,
                    scenario_result.event,
                    scenario_result.steps,
                    scenario_result.trace_len,
                ])

    print("\nResults saved to results.csv")


if __name__ == "__main__":
    main()