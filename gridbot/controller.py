from __future__ import annotations

from typing import Protocol

from gridbot.sim.actions import Action


class Controller(Protocol):
    def act(self, observation: object) -> Action:
        ...
