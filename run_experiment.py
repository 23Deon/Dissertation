print("Running experiment...")

from gridbot.eval.scenario import Scenario
from gridbot.eval.suite import run_suite
from gridbot.eval.load_controller import load_controller


def main():
    print("Setting up scenarios...")

    scenarios = [
        Scenario(3, 3, set(), (0, 0), (2, 0)),        # easy straight line
        Scenario(3, 3, set(), (0, 0), (0, 2)),        # requires turning
        Scenario(3, 3, {(1, 0)}, (0, 0), (2, 0)),     # blocked directly ahead
    ]

    controllers = {
        "PDD v1": "controllers/pdd/controller_v1.py",
        "PDD v2": "controllers/pdd/controller_v2.py",
        "SDD v1": "controllers/sdd/controller_v1.py",
    }

    for name, path in controllers.items():
        print(f"\n--- Running {name} ---")

        controller = load_controller(path)
        result = run_suite(scenarios, controller)

        print("Successes:", result.success_count)
        print("Collisions:", result.collision_count)
        print("Total steps:", result.total_steps)
        print("Average steps:", result.average_steps)


if __name__ == "__main__":
    main()