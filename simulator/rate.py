"""Separate bounded rate model for Phase 3.5 sensitivity experiments."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import sparse


def filter_min_synapses(raw: sparse.spmatrix, minimum: int) -> sparse.csr_matrix:
    if minimum < 1:
        raise ValueError("minimum must be at least one")
    result = raw.tocsr(copy=True)
    result.data[result.data < minimum] = 0
    result.eliminate_zeros()
    return result


def normalize_incoming(raw: sparse.spmatrix, *, minimum: int = 5, gain: float = 1.0) -> sparse.csr_matrix:
    """Normalize each target neuron's retained incoming weights to fixed gain.

    This is an engineering homeostatic normalization, not a measured biological
    rule. Relative retained synapse counts within each target row are preserved.
    """
    result = filter_min_synapses(raw, minimum).astype(np.float32)
    row_sums = np.asarray(result.sum(axis=1)).ravel().astype(np.float32)
    nonzero = row_sums > 0
    inverse = np.zeros_like(row_sums)
    inverse[nonzero] = np.float32(gain) / row_sums[nonzero]
    result.data *= np.repeat(inverse, np.diff(result.indptr))
    return result


@dataclass(frozen=True)
class RateConfig:
    decay: float = 0.5
    activity_floor: float = 1e-6

    def validate(self) -> None:
        if not 0 <= self.decay <= 1:
            raise ValueError("decay must be in [0, 1]")
        if self.activity_floor < 0:
            raise ValueError("activity_floor must be non-negative")


class BoundedRateSimulator:
    """Non-negative saturating rate abstraction with values in [0, 1]."""

    def __init__(self, adjacency: sparse.spmatrix, config: RateConfig) -> None:
        config.validate()
        self.adjacency = adjacency.astype(np.float32, copy=False).tocsr()
        self.config = config
        self.n = self.adjacency.shape[0]
        self.state = np.zeros(self.n, dtype=np.float32)
        self.activity = np.zeros(self.n, dtype=np.float32)

    def reset(self) -> None:
        self.state.fill(0)
        self.activity.fill(0)

    def step(self, external_current: np.ndarray | None = None) -> np.ndarray:
        self.state *= np.float32(self.config.decay)
        self.state += self.adjacency @ self.activity
        if external_current is not None:
            current = np.asarray(external_current, dtype=np.float32)
            if current.shape != (self.n,):
                raise ValueError("external_current must have one value per neuron")
            self.state += np.maximum(current, 0)
        np.maximum(self.state, 0, out=self.state)
        self.activity[:] = self.state / (np.float32(1.0) + self.state)
        if self.config.activity_floor:
            self.activity[self.activity < self.config.activity_floor] = 0
        return self.activity
