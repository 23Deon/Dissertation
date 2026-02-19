from __future__ import annotations

from dataclasses import dataclass

from gridbot.controller import Controller
from gridbot.sim.actions import Action
from gridbot.sim.simulator import Simulator
from gridbot.sim.types import Event
from gridbot.world.observe import Observation


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
