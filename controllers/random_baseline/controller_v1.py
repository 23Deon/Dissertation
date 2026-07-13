import random

from gridbot.sim.actions import Action


class Controller:
    def __init__(self):
        self._rng = random.Random(0)
        self._actions = (
            Action.FORWARD,
            Action.TURN_LEFT,
            Action.TURN_RIGHT,
            Action.WAIT,
        )

    def act(self, observation) -> Action:
        return self._rng.choice(self._actions)
