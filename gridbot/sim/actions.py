from __future__ import annotations

from enum import Enum


class Action(str, Enum):
    FORWARD = "FORWARD"
    TURN_LEFT = "TURN_LEFT"
    TURN_RIGHT = "TURN_RIGHT"
    WAIT = "WAIT"


class Heading(str, Enum):
    N = "N"
    E = "E"
    S = "S"
    W = "W"


def turn_left(h: Heading) -> Heading:
    return {
        Heading.N: Heading.W,
        Heading.W: Heading.S,
        Heading.S: Heading.E,
        Heading.E: Heading.N,
    }[h]


def turn_right(h: Heading) -> Heading:
    return {
        Heading.N: Heading.E,
        Heading.E: Heading.S,
        Heading.S: Heading.W,
        Heading.W: Heading.N,
    }[h]


def forward_delta(h: Heading) -> tuple[int, int]:
    return {
        Heading.N: (0, -1),
        Heading.E: (1, 0),
        Heading.S: (0, 1),
        Heading.W: (-1, 0),
    }[h]
