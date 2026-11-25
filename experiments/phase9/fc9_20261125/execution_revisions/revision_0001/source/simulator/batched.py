"""Batched independent LIF runs sharing one immutable sparse graph."""

from __future__ import annotations

import numpy as np
from scipy import sparse

from .config import NeuronConfig


class BatchedLIFSimulator:
    """Numerically equivalent independent columns evaluated with sparse-dense SpMM."""

    def __init__(self, adjacency: sparse.spmatrix, config: NeuronConfig, batch_size: int) -> None:
        config.validate()
        if batch_size < 1:
            raise ValueError("batch_size must be positive")
        self.adjacency = adjacency.astype(np.float32, copy=False).tocsr()
        self.config = config
        self.n = self.adjacency.shape[0]
        self.batch_size = batch_size
        self.voltage = np.zeros((self.n, batch_size), dtype=np.float32)
        self.spikes = np.zeros((self.n, batch_size), dtype=np.bool_)
        self.refractory = np.zeros((self.n, batch_size), dtype=np.uint16)

    @property
    def state_memory_bytes(self) -> int:
        return self.voltage.nbytes + self.spikes.nbytes + self.refractory.nbytes

    def step(self, external_current: np.ndarray | None = None) -> np.ndarray:
        self.voltage *= np.float32(self.config.decay)
        self.voltage += self.adjacency @ self.spikes.astype(np.float32)
        if external_current is not None:
            current = np.asarray(external_current, dtype=np.float32)
            if current.shape != self.voltage.shape:
                raise ValueError("external_current must have shape (neurons, batch_size)")
            self.voltage += current
        unavailable = self.refractory > 0
        if np.any(unavailable):
            self.voltage[unavailable] = np.float32(self.config.reset_value)
            self.refractory[unavailable] -= 1
        self.spikes = (self.voltage >= np.float32(self.config.threshold)) & ~unavailable
        self.voltage[self.spikes] = np.float32(self.config.reset_value)
        if self.config.refractory_steps:
            self.refractory[self.spikes] = self.config.refractory_steps
        return np.count_nonzero(self.spikes, axis=0)
