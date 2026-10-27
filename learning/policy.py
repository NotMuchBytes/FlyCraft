"""A minimal learnable action readout with safe persistence."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

import numpy as np


ACTIONS = ("NO_OP", "TURN_LEFT", "TURN_RIGHT", "FORWARD")


class LinearSoftmaxPolicy:
    """Softmax action readout; the default four-action Phase 5 API is preserved."""

    def __init__(self, feature_count: int = 4, weights: np.ndarray | None = None, *, actions: tuple[str, ...] = ACTIONS) -> None:
        if not actions or len(set(actions)) != len(actions):
            raise ValueError("actions must be nonempty and unique")
        self.actions = tuple(actions)
        if weights is None:
            weights = np.zeros((feature_count, len(self.actions)), dtype=np.float64)
        weights = np.asarray(weights, dtype=np.float64)
        if weights.shape != (feature_count, len(self.actions)) or not np.isfinite(weights).all():
            raise ValueError("invalid readout weight shape or nonfinite weights")
        self.weights = weights.copy()
        self.baseline = 0.0
        self.episodes_trained = 0

    def probabilities(self, features: np.ndarray, mask: np.ndarray | None = None) -> np.ndarray:
        logits = np.asarray(features, dtype=np.float64) @ self.weights
        if not np.isfinite(logits).all():
            raise ValueError("nonfinite policy logits")
        if mask is not None:
            mask = np.asarray(mask, dtype=bool)
            if mask.shape != logits.shape or not mask.any():
                raise ValueError("action mask must permit at least one action")
            logits = np.where(mask, logits, -np.inf)
        logits -= np.max(logits)
        probabilities = np.exp(logits)
        return probabilities / probabilities.sum()

    def sample(self, features: np.ndarray, rng: np.random.Generator, mask: np.ndarray | None = None) -> tuple[int, str, np.ndarray]:
        probabilities = self.probabilities(features, mask)
        index = int(rng.choice(len(self.actions), p=probabilities))
        return index, self.actions[index], probabilities

    def greedy(self, features: np.ndarray) -> str:
        return self.actions[int(np.argmax(self.probabilities(features)))]

    def expanded(self, feature_count: int, actions: tuple[str, ...]) -> "LinearSoftmaxPolicy":
        """Transfer existing features/actions without changing the neural graph."""
        result = LinearSoftmaxPolicy(feature_count, actions=actions)
        for old, action in enumerate(self.actions):
            if action in actions:
                count = min(feature_count, self.weights.shape[0])
                result.weights[:count, actions.index(action)] = self.weights[:count, old]
        result.baseline = self.baseline
        result.episodes_trained = self.episodes_trained
        return result

    def apply_reinforce(
        self,
        trajectory: list[tuple[np.ndarray, int, np.ndarray, float]],
        *,
        learning_rate: float,
        gamma: float,
        baseline_retention: float,
        gradient_clip: float,
        entropy_coefficient: float = 0.0,
    ) -> dict[str, float]:
        if not trajectory:
            return {"gradient_norm": 0.0, "baseline": self.baseline, "weight_delta_norm": 0.0}
        returns = np.empty(len(trajectory), dtype=np.float64)
        running = 0.0
        for index in range(len(trajectory) - 1, -1, -1):
            running = trajectory[index][3] + gamma * running
            returns[index] = running
        old_weights = self.weights.copy()
        gradient = np.zeros_like(self.weights)
        for (features, action_index, probabilities, _), value in zip(trajectory, returns, strict=True):
            action_error = -probabilities.copy()
            action_error[action_index] += 1.0
            gradient += np.outer(features, action_error) * (value - self.baseline)
            if entropy_coefficient:
                logp = np.log(np.maximum(probabilities, 1e-300))
                entropy_gradient = -probabilities * (logp - float(probabilities @ logp))
                gradient += entropy_coefficient * np.outer(features, entropy_gradient)
        gradient /= len(trajectory)
        norm = float(np.linalg.norm(gradient))
        if norm > gradient_clip:
            gradient *= gradient_clip / norm
        self.weights += learning_rate * gradient
        self.baseline = baseline_retention * self.baseline + (1.0 - baseline_retention) * float(returns.mean())
        self.episodes_trained += 1
        return {
            "gradient_norm": norm,
            "baseline": self.baseline,
            "weight_delta_norm": float(np.linalg.norm(self.weights - old_weights)),
        }

    def save_atomic(self, path: Path, *, training_seed: int, rng_state: dict[str, Any], extra_metadata: dict[str, Any] | None = None, overwrite: bool = True) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
        os.close(descriptor)
        temporary = Path(name)
        payload = {
            "weights": self.weights,
            "actions": np.asarray(self.actions),
            "baseline": np.asarray(self.baseline),
            "episodes_trained": np.asarray(self.episodes_trained, dtype=np.int64),
            "training_seed": np.asarray(training_seed, dtype=np.int64),
            "rng_state_json": np.asarray(json.dumps(rng_state, sort_keys=True)),
            "extra_metadata_json": np.asarray(json.dumps(extra_metadata or {}, sort_keys=True, allow_nan=False)),
        }
        try:
            with temporary.open("wb") as handle:
                np.savez_compressed(handle, **payload)
                handle.flush()
                os.fsync(handle.fileno())
            if overwrite:
                os.replace(temporary, path)
            else:
                os.link(temporary, path)  # Atomic, fails if an artifact already exists.
        finally:
            if temporary.exists():
                temporary.unlink()

    @classmethod
    def load(cls, path: Path) -> tuple["LinearSoftmaxPolicy", dict[str, Any]]:
        with np.load(path, allow_pickle=False) as checkpoint:
            actions = tuple(str(item) for item in checkpoint["actions"].tolist())
            weights = checkpoint["weights"]
            policy = cls(feature_count=weights.shape[0], weights=weights, actions=actions)
            policy.baseline = float(checkpoint["baseline"])
            policy.episodes_trained = int(checkpoint["episodes_trained"])
            metadata = {
                "training_seed": int(checkpoint["training_seed"]),
                "rng_state": json.loads(str(checkpoint["rng_state_json"])),
                "extra": json.loads(str(checkpoint["extra_metadata_json"])) if "extra_metadata_json" in checkpoint else {},
            }
        return policy, metadata
