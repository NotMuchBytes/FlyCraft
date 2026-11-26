"""Synthetic interface/transfer tests; these are not Minecraft success scores."""
import copy
from pathlib import Path
import tempfile
import unittest

import numpy as np

from autonomy import AutonomousAgent
from autonomy.features import PITCH_FEATURE_COUNT, TERRAIN_FEATURE_COUNT, encode
from autonomy.memory import PersistentMemory
from autonomy.recovery import Recovery
from autonomy.minecraft import LiveResourceController
from autonomy.world import ITEMS, LIVE_PITCH_ACTIONS, TERRAIN_ACTIONS
from learning import NeuralFeatureTable

ROOT = Path(__file__).resolve().parents[1]


class FakeNeural:
    def __init__(self, table):
        self.table = table

    def neural_observation(self, sector):
        return self.table.for_sector(sector), None, 100


class TerrainTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.table = NeuralFeatureTable.from_phase35(ROOT / "experiments/phase35/results/rate_decoder_evaluation.json")

    def telemetry(self):
        return dict(game_mode="SURVIVAL", session_id="unit_world", position=[0., 0., 0.],
            inventory_consistent=True, inventory_revision=1, inventory={key: 0 for key in ITEMS},
            station_visible=False, visible=True, near=False, target_distance=5., target_angle=0.,
            target_pitch_error=0., target_id="visible_block", allowed_actions=["JUMP_FORWARD"],
            terrain_observation_schema="visible-terrain-v1", health=20., food=20,
            on_ground=True, obstacle_visible=True, support_visible=True, drop_visible=False, water_visible=False)

    def request(self, telemetry, tick=10, ack=None):
        value = dict(tick_id=tick, sector="center", transport_id="unit_transport",
            control=dict(episode_id="unit", goal="one_log", condition="trained", policy_seed=7, train=False), telemetry=telemetry)
        if ack:
            value["ack"] = ack
        return value

    def test_transfer_preserves_prefix_and_old_masked_probabilities(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            agent = AutonomousAgent(self.table)
            agent.enable_live_pitch()
            agent.policy.weights[:] = np.random.default_rng(17).normal(size=agent.policy.weights.shape)
            old = agent.policy.weights.copy()
            old_input = np.random.default_rng(4).normal(size=PITCH_FEATURE_COUNT)
            old_probs = agent.policy.probabilities(old_input)
            original = folder / "original.npz"
            agent.save(original)
            agent.enable_live_terrain()
            self.assertEqual(agent.policy.actions, TERRAIN_ACTIONS)
            np.testing.assert_array_equal(agent.policy.weights[:PITCH_FEATURE_COUNT, :len(LIVE_PITCH_ACTIONS)], old)
            np.testing.assert_array_equal(agent.policy.weights[PITCH_FEATURE_COUNT:, :-1], 0)
            np.testing.assert_array_equal(agent.policy.weights[:PITCH_FEATURE_COUNT, -1], old[:, LIVE_PITCH_ACTIONS.index("FORWARD")])
            jump_input = np.r_[old_input, [1., 1., 1., 0., 1., 0., 0., 0.]]
            probs = agent.policy.probabilities(jump_input)
            self.assertAlmostEqual(probs[-1] / probs[TERRAIN_ACTIONS.index("FORWARD")], .25)
            expanded_input = np.r_[old_input, np.ones(8)]
            mask = np.r_[np.ones(len(LIVE_PITCH_ACTIONS), dtype=bool), False]
            np.testing.assert_allclose(agent.policy.probabilities(expanded_input, mask)[:-1], old_probs, rtol=1e-14)
            expanded = folder / "expanded.npz"
            agent.save(expanded)
            restored, _ = AutonomousAgent.load(expanded, self.table)
            self.assertEqual(restored.policy.weights.shape, (TERRAIN_FEATURE_COUNT, len(TERRAIN_ACTIONS)))
            legacy, _ = AutonomousAgent.load(original, self.table)
            np.testing.assert_array_equal(legacy.policy.weights, old)

    def test_controller_uses_policy_jump_and_refuses_incomplete_vitals_before_inventory(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            initial = folder / "initial.npz"
            AutonomousAgent(self.table).save(initial)
            controller = LiveResourceController(FakeNeural(self.table), self.table, initial,
                result_log=folder / "result.jsonl", pitch_actions=True, terrain_actions=True)
            try:
                invalid = self.telemetry()
                invalid.pop("health")
                result = controller.evaluate_request(self.request(invalid))
                self.assertTrue(result["observe_only"])
                self.assertIsNone(controller.ledger.previous)
                first = controller.evaluate_request(self.request(self.telemetry()))
                self.assertEqual(first["action"], "JUMP_FORWARD")
                self.assertEqual(first["action_probabilities"]["JUMP_FORWARD"], 1.)
                after = self.telemetry() | dict(position=[0., 1.2, 0.], on_ground=False,
                    target_distance=3.8, allowed_actions=["FORWARD"])
                ack = dict(command_id=first["command_id"], action="JUMP_FORWARD", status="success", error="", block_changed=False)
                second = controller.evaluate_request(self.request(after, tick=20, ack=ack))
                self.assertEqual(second["action"], "FORWARD")
                self.assertEqual(controller.agent.session["actions"], 1)
                self.assertEqual(len(controller.agent.pending[0]), TERRAIN_FEATURE_COUNT)
                self.assertEqual(controller.agent.pending[0][-1], 1.)
            finally:
                controller.close()

    def test_old_interface_does_not_silently_use_terrain_checkpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            agent = AutonomousAgent(self.table)
            agent.enable_live_terrain()
            path = folder / "terrain.npz"
            agent.save(path)
            with self.assertRaisesRegex(ValueError, "terrain interface"):
                LiveResourceController(FakeNeural(self.table), self.table, path,
                    result_log=folder / "no_result.jsonl", pitch_actions=True)
