from gridbot.eval.drift import compare_runs
from gridbot.eval.harness import run_episode_record
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


def test_detects_regression_goal_to_timeout():
    grid = Grid(width=3, height=3, obstacles=set(), start=(0, 0), goal=(2, 0))

    sim1 = Simulator(grid, max_steps=5, start_heading=Heading.E)
    prev = run_episode_record(sim1, AlwaysForward())
    assert prev.event == Event.GOAL_REACHED

    sim2 = Simulator(grid, max_steps=2, start_heading=Heading.E)
    curr = run_episode_record(sim2, AlwaysWait())
    assert curr.event in (Event.TIMEOUT, Event.OK, Event.TIMEOUT)  # depending on max_steps logic

    drift = compare_runs(prev, curr)
    assert drift.regression is True
