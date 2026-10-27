"""Small deterministic bounded 2D environment."""

from __future__ import annotations

from dataclasses import dataclass
import math


ACTIONS = {"TURN_LEFT", "TURN_RIGHT", "FORWARD", "NO_OP"}


@dataclass
class World2D:
    width: float = 10.0
    height: float = 10.0
    turn_radians: float = math.pi / 8
    forward_distance: float = 0.5
    start_x: float = 5.0
    start_y: float = 2.0
    start_heading: float = math.pi / 2
    target_x: float = 5.0
    target_y: float = 8.0

    def __post_init__(self) -> None:
        self.reset()

    def reset(self, target: tuple[float, float] | None = None) -> tuple[float, float, float]:
        self.x = float(self.start_x)
        self.y = float(self.start_y)
        self.heading = float(self.start_heading)
        if target is not None:
            self.target_x, self.target_y = map(float, target)
        return self.state

    @property
    def state(self) -> tuple[float, float, float]:
        return self.x, self.y, self.heading

    def step(self, action: str) -> tuple[float, float, float]:
        if action not in ACTIONS:
            raise ValueError(f"unknown action: {action}")
        if action == "TURN_LEFT":
            self.heading = (self.heading + self.turn_radians) % (2 * math.pi)
        elif action == "TURN_RIGHT":
            self.heading = (self.heading - self.turn_radians) % (2 * math.pi)
        elif action == "FORWARD":
            self.x = min(self.width, max(0.0, self.x + self.forward_distance * math.cos(self.heading)))
            self.y = min(self.height, max(0.0, self.y + self.forward_distance * math.sin(self.heading)))
        return self.state
