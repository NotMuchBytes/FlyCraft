"""Small, explicit learning layer over fixed FlyCraft neural features."""

from .policy import ACTIONS, LinearSoftmaxPolicy
from .task import EpisodeResult, NeuralFeatureTable, RewardConfig, TargetTask, TrainingConfig

__all__ = [
    "ACTIONS",
    "EpisodeResult",
    "LinearSoftmaxPolicy",
    "NeuralFeatureTable",
    "RewardConfig",
    "TargetTask",
    "TrainingConfig",
]
