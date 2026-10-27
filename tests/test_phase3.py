from __future__ import annotations

import math
from pathlib import Path
import unittest

import numpy as np

from environment import AngularSensor, World2D
from interface import ActionDecoder, PopulationRecord, RateActionDecoder, SensoryEncoder, select_phase3_populations, select_superclass_population


ROOT = Path(__file__).resolve().parents[1]


def record(index: int, side: str) -> PopulationRecord:
    return PopulationRecord(index + 100, index, side, "", "", "", "", "", "", "", "", "test")


class Phase3Tests(unittest.TestCase):
    def test_real_metadata_population_selection(self) -> None:
        inputs, outputs = select_phase3_populations(ROOT / "data")
        self.assertEqual(len(inputs), 9706)
        self.assertEqual(len(outputs), 1305)
        self.assertTrue(all(r.family == "Photo Receptors" and r.sub_class == "photo_receptor" for r in inputs))
        self.assertTrue(all(r.super_class == "descending" for r in outputs))

    def test_deterministic_environment_reset_and_actions(self) -> None:
        world = World2D()
        initial = world.state
        world.step("TURN_LEFT")
        self.assertGreater(world.heading, initial[2])
        world.reset()
        self.assertEqual(world.state, initial)
        world.step("FORWARD")
        self.assertAlmostEqual(world.y, initial[1] + 0.5)

    def test_sensor_left_right_and_hidden(self) -> None:
        world = World2D()
        sensor = AngularSensor()
        world.reset((2, 8))
        self.assertIn(sensor.observe(world).sector, {"left", "far_left"})
        world.reset((8, 8))
        self.assertIn(sensor.observe(world).sector, {"right", "far_right"})
        world.reset((5, 0))
        self.assertFalse(sensor.observe(world).visible)

    def test_encoder_is_deterministic_and_disjoint(self) -> None:
        records = [record(i, "left") for i in range(120)] + [record(i + 120, "right") for i in range(120)]
        first = SensoryEncoder.from_population(records, 240, neurons_per_sector=20)
        second = SensoryEncoder.from_population(records, 240, neurons_per_sector=20)
        for sector in first.sector_indices:
            np.testing.assert_array_equal(first.sector_indices[sector], second.sector_indices[sector])
        self.assertEqual(np.count_nonzero(first.encode("left")), 20)
        self.assertEqual(np.count_nonzero(first.encode(None)), 0)

    def test_output_decoder(self) -> None:
        decoder = ActionDecoder([record(0, "left"), record(1, "right")])
        self.assertEqual(decoder.decode(decoder.observe(np.array([False, False]))), "NO_OP")
        self.assertEqual(decoder.decode(decoder.observe(np.array([True, False]))), "TURN_LEFT")
        self.assertEqual(decoder.decode(decoder.observe(np.array([False, True]))), "TURN_RIGHT")
        self.assertEqual(decoder.decode(decoder.observe(np.array([True, True]))), "FORWARD")

    def test_rate_output_decoder_never_receives_condition_labels(self) -> None:
        decoder = RateActionDecoder([record(0, "left"), record(1, "right")], turn_margin=0.1)
        self.assertEqual(decoder.decode(decoder.observe(np.array([0.0, 0.0], dtype=np.float32))), "NO_OP")
        self.assertEqual(decoder.decode(decoder.observe(np.array([0.3, 0.1], dtype=np.float32))), "TURN_LEFT")
        self.assertEqual(decoder.decode(decoder.observe(np.array([0.1, 0.3], dtype=np.float32))), "TURN_RIGHT")
        self.assertEqual(decoder.decode(decoder.observe(np.array([0.3, 0.3], dtype=np.float32))), "FORWARD")

    def test_visual_projection_population_is_annotation_selected(self) -> None:
        records = select_superclass_population(ROOT / "data", "visual_projection")
        self.assertEqual(len(records), 7684)
        self.assertTrue(all(record.super_class == "visual_projection" for record in records))

    def test_closed_loop_components_repeat(self) -> None:
        def run() -> list[tuple[float, float, float]]:
            world = World2D(target_x=2, target_y=8)
            actions = ["TURN_LEFT", "FORWARD", "NO_OP"]
            return [world.step(action) for action in actions]
        self.assertEqual(run(), run())


if __name__ == "__main__":
    unittest.main()
