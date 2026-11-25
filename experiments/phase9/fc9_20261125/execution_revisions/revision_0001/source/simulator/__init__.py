"""Lightweight structural-connectome simulation tools for FlyCraft."""

from .config import NeuronConfig, WeightTransformConfig
from .graph import ConnectomeGraph, build_source_gain, transform_weights
from .simulator import LIFSimulator, StepMetrics
from .batched import BatchedLIFSimulator
from .rate import BoundedRateSimulator, RateConfig, filter_min_synapses, normalize_incoming

__all__ = [
    "ConnectomeGraph",
    "LIFSimulator",
    "BatchedLIFSimulator",
    "BoundedRateSimulator",
    "RateConfig",
    "filter_min_synapses",
    "normalize_incoming",
    "NeuronConfig",
    "StepMetrics",
    "WeightTransformConfig",
    "build_source_gain",
    "transform_weights",
]
