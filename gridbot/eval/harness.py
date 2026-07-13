from __future__ import annotations

from dataclasses import dataclass

from gridbot.controller import Controller
from gridbot.sim.actions import Action
from gridbot.sim.simulator import Simulator
from gridbot.sim.types import Event
from gridbot.world.observe import Observation
from gridbot.eval.scenario import Scenario
from gridbot.world.grid import Grid
from gridbot.eval.record import ScenarioRunRecord, TraceRecord


@dataclass(frozen=True)
class EpisodeResult:
    event: Event
    steps: int
    trace_len: int


def run_episode(sim: Simulator, controller: Controller) -> EpisodeResult:
    """
    Deterministically runs until termination (goal, collision, timeout).
    Returns a small summary (full trace is inside sim.trace).
    """
    while not sim.state.done:
        obs = Observation(
            position=sim.state.position,
            heading=sim.state.heading,
            goal=sim.grid.goal,
        )

        action: Action = controller.act(obs)
        sim.step(action)

    return EpisodeResult(
        event=sim.state.last_event,
        steps=sim.state.t,
        trace_len=len(sim.trace.steps),
    )


def run_scenario(scenario: Scenario, controller: Controller):
    grid = Grid(
        width=scenario.width,
        height=scenario.height,
        obstacles=scenario.obstacles,
        start=scenario.start,
        goal=scenario.goal,
    )

    sim = Simulator(grid, max_steps=scenario.max_steps)

    return run_episode(sim, controller)


def run_episode_record(sim: Simulator, controller: Controller) -> ScenarioRunRecord:
    start_heading = sim.state.heading
    result = run_episode(sim, controller)

    positions = [sim.grid.start, *[s.position for s in sim.trace.steps]]
    actions = [s.action for s in sim.trace.steps]
    headings = [start_heading, *[s.heading for s in sim.trace.steps]]

    return ScenarioRunRecord(
        event=result.event,
        steps=result.steps,
        trace=TraceRecord(positions=positions, actions=actions, headings=headings),
    )


def run_scenario_record(scenario: Scenario, controller: Controller) -> ScenarioRunRecord:
    """
    Runs a scenario and returns the full recorded trace, not just summary stats.
    """
    grid = Grid(
        width=scenario.width,
        height=scenario.height,
        obstacles=scenario.obstacles,
        start=scenario.start,
        goal=scenario.goal,
    )

    sim = Simulator(grid, max_steps=scenario.max_steps)

    return run_episode_record(sim, controller)
