"""Transparent deterministic mapping from five visual sectors to neurons."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .populations import PopulationRecord


SECTORS = ("far_left", "left", "center", "right", "far_right")


@dataclass
class SensoryEncoder:
    neuron_count: int
    sector_indices: dict[str, np.ndarray]
    amplitude: float = 1.05
    duration_steps: int = 1

    @classmethod
    def from_population(
        cls,
        records: list[PopulationRecord],
        neuron_count: int,
        neurons_per_sector: int = 50,
        amplitude: float = 1.05,
        duration_steps: int = 1,
    ) -> "SensoryEncoder":
        left = np.array([r.dense_index for r in records if r.side == "left"], dtype=np.int64)
        right = np.array([r.dense_index for r in records if r.side == "right"], dtype=np.int64)
        left.sort()
        right.sort()
        if len(left) < neurons_per_sector * 2 or len(right) < neurons_per_sector * 2:
            raise ValueError("insufficient left/right input neurons for disjoint sector mappings")
        half = neurons_per_sector // 2
        center = np.concatenate((left[-half:], right[: neurons_per_sector - half]))
        mapping = {
            "far_left": left[:neurons_per_sector],
            "left": left[neurons_per_sector : 2 * neurons_per_sector],
            "center": np.sort(center),
            "right": right[-2 * neurons_per_sector : -neurons_per_sector],
            "far_right": right[-neurons_per_sector:],
        }
        return cls(neuron_count, mapping, amplitude, duration_steps)

    def encode(self, sector: str | None, step_in_observation: int = 0, intensity: float = 1.0) -> np.ndarray:
        current = np.zeros(self.neuron_count, dtype=np.float32)
        if sector is None or step_in_observation >= self.duration_steps:
            return current
        if sector not in self.sector_indices:
            raise ValueError(f"unknown sector: {sector}")
        current[self.sector_indices[sector]] = np.float32(self.amplitude * max(0.0, intensity))
        return current
