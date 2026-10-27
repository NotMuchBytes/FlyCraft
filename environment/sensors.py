"""Five-sector artificial visual sensor for one target."""

from __future__ import annotations

from dataclasses import dataclass
import math

from .world2d import World2D


@dataclass(frozen=True)
class VisualObservation:
    visible: bool
    sector: str | None
    relative_angle: float
    distance: float
    intensity: float


class AngularSensor:
    def __init__(self, field_of_view: float = math.pi, max_distance: float = 20.0) -> None:
        self.field_of_view = field_of_view
        self.max_distance = max_distance

    @staticmethod
    def _wrap(angle: float) -> float:
        return (angle + math.pi) % (2 * math.pi) - math.pi

    def observe(self, world: World2D) -> VisualObservation:
        dx = world.target_x - world.x
        dy = world.target_y - world.y
        distance = math.hypot(dx, dy)
        relative = self._wrap(math.atan2(dy, dx) - world.heading)
        visible = distance <= self.max_distance and abs(relative) <= self.field_of_view / 2
        if not visible:
            return VisualObservation(False, None, relative, distance, 0.0)
        normalized = relative / (self.field_of_view / 2)
        if normalized <= -0.6:
            sector = "far_right"
        elif normalized <= -0.2:
            sector = "right"
        elif normalized < 0.2:
            sector = "center"
        elif normalized < 0.6:
            sector = "left"
        else:
            sector = "far_left"
        intensity = max(0.1, 1.0 - distance / self.max_distance)
        return VisualObservation(True, sector, relative, distance, intensity)
