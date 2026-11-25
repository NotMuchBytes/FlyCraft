"""Vectorized synchronous signal propagation on a sparse structural graph."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import sparse

from .config import NeuronConfig


@dataclass(frozen=True)
class StepMetrics:
    timestep: int
    active_neurons: int
    newly_active_neurons: int
    peak_membrane_potential: float
    total_absolute_potential: float


class LIFSimulator:
    """A computational abstraction, not a physiological fly-neuron model."""

    def __init__(
        self,
        adjacency: sparse.spmatrix,
        config: NeuronConfig,
        source_gain: np.ndarray | None = None,
    ) -> None:
        config.validate()
        matrix = adjacency.astype(np.float32, copy=False).tocsr()
        if matrix.shape[0] != matrix.shape[1]:
            raise ValueError("adjacency must be square")
        self.adjacency = matrix
        self.config = config
        self.n = matrix.shape[0]
        self.source_gain = (
            np.ones(self.n, dtype=np.float32)
            if source_gain is None
            else np.asarray(source_gain, dtype=np.float32)
        )
        if self.source_gain.shape != (self.n,):
            raise ValueError("source_gain must have one value per neuron")
        self.voltage = np.zeros(self.n, dtype=np.float32)
        self.spikes = np.zeros(self.n, dtype=np.bool_)
        self.refractory = np.zeros(self.n, dtype=np.uint16)
        self.timestep = 0

    @property
    def state_memory_bytes(self) -> int:
        return int(
            self.voltage.nbytes
            + self.spikes.nbytes
            + self.refractory.nbytes
            + self.source_gain.nbytes
        )

    def reset(self) -> None:
        self.voltage.fill(0.0)
        self.spikes.fill(False)
        self.refractory.fill(0)
        self.timestep = 0

    def step(self, external_current: np.ndarray | None = None) -> StepMetrics:
        previous_spikes = self.spikes.copy()
        self.voltage *= np.float32(self.config.decay)
        presynaptic = self.spikes.astype(np.float32)
        presynaptic *= self.source_gain
        self.voltage += self.adjacency @ presynaptic
        if external_current is not None:
            current = np.asarray(external_current, dtype=np.float32)
            if current.shape != (self.n,):
                raise ValueError("external_current must have one value per neuron")
            self.voltage += current

        unavailable = self.refractory > 0
        if np.any(unavailable):
            self.voltage[unavailable] = np.float32(self.config.reset_value)
            self.refractory[unavailable] -= 1
        self.spikes = (self.voltage >= np.float32(self.config.threshold)) & ~unavailable
        if np.any(self.spikes):
            self.voltage[self.spikes] = np.float32(self.config.reset_value)
            if self.config.refractory_steps:
                self.refractory[self.spikes] = self.config.refractory_steps
        self.timestep += 1
        return StepMetrics(
            timestep=self.timestep - 1,
            active_neurons=int(np.count_nonzero(self.spikes)),
            newly_active_neurons=int(np.count_nonzero(self.spikes & ~previous_spikes)),
            peak_membrane_potential=float(np.max(self.voltage, initial=0.0)),
            total_absolute_potential=float(np.sum(np.abs(self.voltage), dtype=np.float64)),
        )
