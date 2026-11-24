import unittest

import numpy as np

from experiments.phase9.phase8_finish_20261123.train_progress_readout import objective


class LoggedTrainingTests(unittest.TestCase):
    def test_masked_progress_loss_gradient_matches_finite_differences(self):
        rng = np.random.default_rng(23)
        features = rng.normal(size=(5, 3))
        original = rng.normal(size=(3, 4))
        weights = original + rng.normal(scale=0.2, size=original.shape)
        allowed = np.array([
            [True, False, True, True],
            [False, True, True, False],
            [True, True, False, True],
            [True, False, False, True],
            [False, True, True, True],
        ])
        labels = np.array([2, 1, 3, 0, 2])
        sample_weights = np.array([0.1, 0.25, 0.2, 0.15, 0.3])
        args = features, labels, allowed, sample_weights, original, 0.03
        loss, gradient = objective(weights.ravel(), *args)
        self.assertTrue(np.isfinite(loss))
        numerical = np.zeros(weights.size)
        epsilon = 1e-6
        for coordinate in range(weights.size):
            positive = weights.ravel().copy()
            negative = weights.ravel().copy()
            positive[coordinate] += epsilon
            negative[coordinate] -= epsilon
            numerical[coordinate] = (
                objective(positive, *args)[0] - objective(negative, *args)[0]
            ) / (2 * epsilon)
        np.testing.assert_allclose(gradient, numerical, rtol=1e-5, atol=1e-7)
