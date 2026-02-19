from gridbot.eval.harness import run_episode
from gridbot.sim.actions import Action, Heading
from gridbot.sim.simulator import Simulator
from gridbot.sim.types import Event
from gridbot.world.grid import Grid


class AlwaysForward:
    def act(self, observation):
        return Action.FORWARD


def test_run_episode_reaches_goal_in_two_steps():
    grid = Grid(width=3, height=3, obstacles=set(), start=(0, 0), goal=(2, 0))
    sim = Simulator(grid, max_steps=10, start_heading=Heading.E)

    result = run_episode(sim, AlwaysForward())

    assert result.event == Event.GOAL_REACHED
    assert result.steps == 2
    assert result.trace_len == 2
