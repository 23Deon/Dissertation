from gridbot.sim.actions import Action, Heading
from gridbot.sim.simulator import Event, Simulator
from gridbot.world.grid import Grid


def test_reaches_goal():
    grid = Grid(
        width=5,
        height=5,
        obstacles=set(),
        start=(0, 0),
        goal=(1, 0),
    )

    sim = Simulator(grid, max_steps=10, start_heading=Heading.E)

    event = sim.step(Action.FORWARD)

    assert sim.state.position == (1, 0)
    assert sim.state.done is True
    assert event == Event.GOAL_REACHED
