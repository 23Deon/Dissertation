print("Running experiment...")

from gridbot.eval.scenario import Scenario
from gridbot.eval.suite import run_suite
from gridbot.sim.actions import Action

class AlwaysForward:
    def act(self, observation):
        return Action.FORWARD


def main():
    print("Setting up scenarios and controller...")
    scenarios = [Scenario(3,3, set(), (0,0), (2,0)), Scenario(5,5, {(2,2)}, (0,0), (4,0))]

    controller = AlwaysForward()

    result = run_suite(scenarios, controller)

    print("Successes:", result.success_count)
    print("Collisions:", result.collision_count)
    
if __name__ == "__main__":
    main()