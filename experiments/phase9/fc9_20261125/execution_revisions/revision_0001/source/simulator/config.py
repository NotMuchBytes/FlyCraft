"""Explicit engineering configuration for the first FlyCraft simulator."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class WeightTransformConfig:
    """Convert aggregate synapse counts into dimensionless model weights.

    None of these transforms is asserted to be biologically correct. The
    default compresses the heavy-tailed count distribution and then applies a
    conservative global scale.
    """

    name: str = "log1p"
    scale: float = 0.03
    cap: float = 32.0

    def to_dict(self) -> dict[str, float | str]:
        return asdict(self)


@dataclass(frozen=True)
class NeuronConfig:
    """Dimensionless synchronous leaky-integrate-and-fire-like parameters."""

    decay: float = 0.90
    threshold: float = 1.0
    reset_value: float = 0.0
    refractory_steps: int = 0

    def validate(self) -> None:
        if not 0.0 <= self.decay <= 1.0:
            raise ValueError("decay must be in [0, 1]")
        if self.threshold <= self.reset_value:
            raise ValueError("threshold must be greater than reset_value")
        if self.refractory_steps < 0:
            raise ValueError("refractory_steps must be non-negative")

    def to_dict(self) -> dict[str, float | int]:
        return asdict(self)
