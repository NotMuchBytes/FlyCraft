from __future__ import annotations

import unittest

import numpy as np
from scipy import sparse

from simulator import (
    BatchedLIFSimulator,
    BoundedRateSimulator,
    LIFSimulator,
    NeuronConfig,
    RateConfig,
    WeightTransformConfig,
    build_source_gain,
    transform_weights,
    normalize_incoming,
)


def graph(size: int, edges: list[tuple[int, int, float]]) -> sparse.csr_matrix:
    """Build target-row/source-column adjacency from source,target,weight edges."""
    source = np.array([edge[0] for edge in edges], dtype=np.int32)
    target = np.array([edge[1] for edge in edges], dtype=np.int32)
    weight = np.array([edge[2] for edge in edges], dtype=np.float32)
    return sparse.csr_matrix((weight, (target, source)), shape=(size, size))


class SimulatorTests(unittest.TestCase):
    def test_bounded_rate_is_stable_and_normalized(self) -> None:
        raw = graph(3, [(0, 1, 5.0), (0, 2, 10.0), (1, 2, 10.0)])
        normalized = normalize_incoming(raw, minimum=5, gain=0.8)
        np.testing.assert_allclose(np.asarray(normalized.sum(axis=1)).ravel(), [0.0, 0.8, 0.8])
        sim = BoundedRateSimulator(normalized, RateConfig(decay=0.5))
        for _ in range(20):
            activity = sim.step(np.array([1.0, 0.0, 0.0], dtype=np.float32))
        self.assertTrue(np.all(activity >= 0))
        self.assertTrue(np.all(activity <= 1))
        self.assertGreater(activity[2], 0)

    def test_batched_matches_individual_simulators(self) -> None:
        adjacency = graph(3, [(0, 1, 1.0), (1, 2, 1.0)])
        config = NeuronConfig(decay=0.5, threshold=0.5)
        batched = BatchedLIFSimulator(adjacency, config, 2)
        singles = [LIFSimulator(adjacency, config) for _ in range(2)]
        currents = np.array([[1.0, 0.0], [0.0, 1.0], [0.0, 0.0]], dtype=np.float32)
        for step in range(4):
            batch_current = currents if step == 0 else None
            batched.step(batch_current)
            for column, sim in enumerate(singles):
                sim.step(currents[:, column] if step == 0 else None)
                np.testing.assert_array_equal(batched.spikes[:, column], sim.spikes)
                np.testing.assert_allclose(batched.voltage[:, column], sim.voltage)

    def test_chain_propagates_one_hop_per_step(self) -> None:
        sim = LIFSimulator(graph(3, [(0, 1, 1.0), (1, 2, 1.0)]), NeuronConfig(decay=0, threshold=0.5))
        current = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        self.assertEqual(sim.step(current).active_neurons, 1)
        self.assertTrue(sim.spikes[0])
        self.assertEqual(sim.step().active_neurons, 1)
        self.assertTrue(sim.spikes[1])
        self.assertEqual(sim.step().active_neurons, 1)
        self.assertTrue(sim.spikes[2])

    def test_branching(self) -> None:
        sim = LIFSimulator(graph(3, [(0, 1, 1.0), (0, 2, 1.0)]), NeuronConfig(decay=0, threshold=0.5))
        sim.step(np.array([1, 0, 0], dtype=np.float32))
        metrics = sim.step()
        self.assertEqual(metrics.active_neurons, 2)
        np.testing.assert_array_equal(sim.spikes, [False, True, True])

    def test_weight_threshold_and_reset(self) -> None:
        sim = LIFSimulator(graph(2, [(0, 1, 0.4)]), NeuronConfig(decay=1, threshold=0.5, reset_value=0))
        sim.step(np.array([1, 0], dtype=np.float32))
        self.assertEqual(sim.step().active_neurons, 0)
        self.assertAlmostEqual(float(sim.voltage[1]), 0.4, places=6)
        sim.step(np.array([0, 0.2], dtype=np.float32))
        self.assertTrue(sim.spikes[1])
        self.assertEqual(float(sim.voltage[1]), 0.0)

    def test_decay_accumulates_subthreshold_current(self) -> None:
        sim = LIFSimulator(sparse.csr_matrix((1, 1), dtype=np.float32), NeuronConfig(decay=0.5, threshold=1.0))
        current = np.array([0.6], dtype=np.float32)
        self.assertFalse(sim.spikes[0])
        sim.step(current)
        self.assertFalse(sim.spikes[0])
        sim.step(current)
        self.assertFalse(sim.spikes[0])
        sim.step(current)
        self.assertTrue(sim.spikes[0])

    def test_weight_transforms(self) -> None:
        raw = graph(2, [(0, 1, 9.0)])
        self.assertAlmostEqual(transform_weights(raw, WeightTransformConfig("raw", 0.5)).data[0], 4.5)
        self.assertAlmostEqual(transform_weights(raw, WeightTransformConfig("sqrt", 1)).data[0], 3.0)
        self.assertAlmostEqual(transform_weights(raw, WeightTransformConfig("log1p", 1)).data[0], np.log(10), places=6)
        self.assertAlmostEqual(transform_weights(raw, WeightTransformConfig("clipped", 1, 4)).data[0], 4.0)
        self.assertAlmostEqual(transform_weights(raw, WeightTransformConfig("normalized_clipped", 1, 4)).data[0], 1.0)

    def test_unknown_transmitter_policies(self) -> None:
        codes = np.array([0, 1, 2], dtype=np.uint8)
        np.testing.assert_array_equal(build_source_gain(codes), [1, 1, 1])
        np.testing.assert_array_equal(build_source_gain(codes, unknown_policy="zero"), [0, 1, 1])
        with self.assertRaises(ValueError):
            build_source_gain(codes, unknown_policy="error")
        signed = build_source_gain(
            codes,
            mode="simplified_signed",
            sign_map={"ACH": 1.0, "GABA": -1.0},
            unknown_policy="zero",
        )
        np.testing.assert_array_equal(signed, [0, 1, -1])


if __name__ == "__main__":
    unittest.main()
