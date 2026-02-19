from gridbot.eval.scenario import Scenario
from gridbot.eval.suite import run_suite
from gridbot.sim.actions import Action
from gridbot.sim.types import Event


class AlwaysForward:
    def act(self, observation):
        return Action.FORWARD


def test_suite_counts_successes():
    scenarios = [
        Scenario(3, 3, set(), (0, 0), (2, 0)),
        Scenario(3, 3, set(), (0, 0), (1, 0)),
    ]

    result = run_suite(scenarios, AlwaysForward())

    assert result.success_count == 2
    assert result.collision_count == 0
