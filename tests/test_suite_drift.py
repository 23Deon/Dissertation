from gridbot.eval.harness import run_episode_record
from gridbot.eval.scenario import Scenario
from gridbot.eval.suite_drift import compare_suites
from gridbot.sim.actions import Action, Heading
from gridbot.sim.simulator import Simulator
from gridbot.sim.types import Event
from gridbot.world.grid import Grid


class AlwaysForward:
    def act(self, obs):
        return Action.FORWARD


class AlwaysWait:
    def act(self, obs):
        return Action.WAIT


def test_suite_detects_regression():
    scenario = Scenario(3, 3, set(), (0, 0), (2, 0))

    # Previous controller succeeds
    grid1 = Grid(3, 3, set(), (0, 0), (2, 0))
    sim1 = Simulator(grid1, max_steps=10, start_heading=Heading.E)
    prev = run_episode_record(sim1, AlwaysForward())

    # Current controller fails
    grid2 = Grid(3, 3, set(), (0, 0), (2, 0))
    sim2 = Simulator(grid2, max_steps=2, start_heading=Heading.E)
    curr = run_episode_record(sim2, AlwaysWait())

    result = compare_suites([prev], [curr])

    assert result.regressions == 1
    assert result.total_scenarios == 1
