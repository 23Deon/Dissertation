print("Running experiment...")

from gridbot.eval.scenario import Scenario
from gridbot.eval.suite import run_suite
from gridbot.eval.load_controller import load_controller


def main():
    print("Setting up scenarios and controller...")

    scenarios = [
    Scenario(3, 3, set(), (0, 0), (2, 0)),        # easy straight line
    Scenario(3, 3, set(), (0, 0), (0, 2)),        # requires turning
    Scenario(3, 3, {(1, 0)}, (0, 0), (2, 0)),     # blocked directly ahead
]


    controller = load_controller("controllers/pdd/controller_v1.py")

    result = run_suite(scenarios, controller)

    print("Successes:", result.success_count)
    print("Collisions:", result.collision_count)


if __name__ == "__main__":
    main()