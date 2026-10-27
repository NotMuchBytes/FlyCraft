from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

import numpy as np

from environment import World2D
from learning import LinearSoftmaxPolicy, NeuralFeatureTable, TargetTask, TrainingConfig


ROOT = Path(__file__).resolve().parents[1]


class LearningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.table = NeuralFeatureTable.from_phase35(ROOT / "experiments" / "phase35" / "results" / "rate_decoder_evaluation.json")

    def test_feature_table_is_fixed_phase35_output(self) -> None:
        self.assertEqual(self.table.for_sector("left").shape, (4,))
        self.assertGreater(self.table.for_sector("left")[1], self.table.for_sector("left")[2])
        self.assertGreater(self.table.for_sector("right")[2], self.table.for_sector("right")[1])
        np.testing.assert_array_equal(self.table.for_sector(None), self.table.for_sector("not_visible"))

    def test_reward_scores_orientation_outcome_not_action_label(self) -> None:
        task = TargetTask(self.table)
        left_world = World2D(target_x=2.0, target_y=8.0)
        before = left_world.state
        correct = left_world.step("TURN_LEFT")
        correct_reward, _, _ = task.step_reward(before, correct, left_world)
        wrong_world = World2D(target_x=2.0, target_y=8.0)
        before = wrong_world.state
        wrong = wrong_world.step("TURN_RIGHT")
        wrong_reward, _, _ = task.step_reward(before, wrong, wrong_world)
        self.assertGreater(correct_reward, wrong_reward)

    def test_reinforce_update_changes_only_readout_weights(self) -> None:
        policy = LinearSoftmaxPolicy()
        features = np.array([1.0, 0.8, 0.1, 0.9])
        probabilities = policy.probabilities(features)
        before = policy.weights.copy()
        metrics = policy.apply_reinforce(
            [(features, 1, probabilities, 1.0)],
            learning_rate=0.025,
            gamma=0.97,
            baseline_retention=0.95,
            gradient_clip=5.0,
        )
        self.assertGreater(metrics["weight_delta_norm"], 0.0)
        self.assertFalse(np.array_equal(before, policy.weights))

    def test_checkpoint_round_trip_and_rng_metadata(self) -> None:
        policy = LinearSoftmaxPolicy()
        policy.weights[2, 3] = 1.25
        policy.baseline = 0.5
        policy.episodes_trained = 7
        rng = np.random.default_rng(42)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "checkpoint.npz"
            policy.save_atomic(path, training_seed=42, rng_state=rng.bit_generator.state)
            self.assertTrue(path.exists())
            self.assertFalse(path.with_name(path.name + ".tmp").exists())
            restored, metadata = LinearSoftmaxPolicy.load(path)
        np.testing.assert_array_equal(policy.weights, restored.weights)
        self.assertEqual(restored.baseline, 0.5)
        self.assertEqual(restored.episodes_trained, 7)
        self.assertEqual(metadata["training_seed"], 42)

    def test_episode_reset_and_seed_are_reproducible(self) -> None:
        task = TargetTask(self.table)
        config = TrainingConfig(max_steps=8)
        first = task.run_episode(LinearSoftmaxPolicy(), np.random.default_rng(99), episode=1, seed=99, config=config, train=False)
        second = task.run_episode(LinearSoftmaxPolicy(), np.random.default_rng(99), episode=1, seed=99, config=config, train=False)
        self.assertEqual(first.serializable() | {"elapsed_seconds": 0}, second.serializable() | {"elapsed_seconds": 0})

    def test_checkpoint_resume_matches_uninterrupted_training(self) -> None:
        task = TargetTask(self.table)
        config = TrainingConfig(max_steps=8)
        full_policy = LinearSoftmaxPolicy()
        full_rng = np.random.default_rng(123)
        for episode in range(1, 11):
            task.run_episode(full_policy, full_rng, episode=episode, seed=123, config=config, train=True)

        partial_policy = LinearSoftmaxPolicy()
        partial_rng = np.random.default_rng(123)
        for episode in range(1, 6):
            task.run_episode(partial_policy, partial_rng, episode=episode, seed=123, config=config, train=True)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "resume.npz"
            partial_policy.save_atomic(path, training_seed=123, rng_state=partial_rng.bit_generator.state)
            resumed, metadata = LinearSoftmaxPolicy.load(path)
        resumed_rng = np.random.default_rng()
        resumed_rng.bit_generator.state = metadata["rng_state"]
        for episode in range(6, 11):
            task.run_episode(resumed, resumed_rng, episode=episode, seed=123, config=config, train=True)
        np.testing.assert_array_equal(full_policy.weights, resumed.weights)
        self.assertEqual(full_policy.baseline, resumed.baseline)


if __name__ == "__main__":
    unittest.main()
