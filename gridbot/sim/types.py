from __future__ import annotations

from enum import Enum


class Event(str, Enum):
    OK = "OK"
    COLLISION = "COLLISION"
    GOAL_REACHED = "GOAL_REACHED"
    TIMEOUT = "TIMEOUT"
