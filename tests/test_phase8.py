import copy
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from autonomy import AutonomousAgent, AutonomyConfig
from autonomy.minecraft import LiveResourceController, ObservationError, TransactionLedger
from autonomy.world import ACTIONS, ITEMS
from learning import NeuralFeatureTable

ROOT = Path(__file__).resolve().parents[1]


class FakeNeural:
    def __init__(self, table):
        self.table = table
    def neural_observation(self, sector):
        return self.table.for_sector(sector), None, 100


class Phase8Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.table = NeuralFeatureTable.from_phase35(ROOT / "experiments/phase35/results/rate_decoder_evaluation.json")

    def telemetry(self, **extra):
        return {"game_mode": "SURVIVAL", "session_id": "unit_world", "position": [0., 0., 0.],
                "inventory_consistent": True, "inventory_revision": 1, "inventory": {key: 0 for key in ITEMS},
                "station_visible": False, "visible": True, "near": True, "target_distance": 2., "target_angle": 0.,
                "target_id": "visible_block", "allowed_actions": ["NO_OP", "COLLECT_LOG"], **extra}

    def request(self, tick, *, episode="unit", goal="one_log", condition="trained", telemetry=None, ack=None, train=False):
        request = {"tick_id": tick, "sector": "center", "control": {"episode_id": episode, "goal": goal, "condition": condition,
            "policy_seed": 7, "train": train}, "telemetry": telemetry or self.telemetry()}
        if ack:
            request["ack"] = ack
        return request

    def controller(self, folder, *, forced="COLLECT_LOG", checkpoint=None, result="results"):
        if checkpoint is None:
            checkpoint = folder / (result + "_initial.npz")
            agent = AutonomousAgent(self.table, config=AutonomyConfig(max_steps=12, repeat_limit=2, max_recoveries=1))
            agent.policy.weights[0, ACTIONS.index(forced)] = 1000
            agent.save(checkpoint)
        return LiveResourceController(FakeNeural(self.table), self.table, checkpoint, result_log=folder / (result + ".jsonl"))

    def ack(self, response, *, action="COLLECT_LOG", status="success", error="", changed=True):
        return {"command_id": response["command_id"], "action": action, "status": status, "error": error, "block_changed": changed}

    def test_mining_ack_alone_is_not_resource_collection(self):
        ledger = TransactionLedger()
        ledger.observe(self.telemetry(), None)
        counts = ledger.observe(self.telemetry(), {"action": "COLLECT_LOG", "block_changed": True})
        self.assertEqual(counts["log"], 0)
        self.assertEqual(ledger.produced["log"], 0)
        self.assertEqual(ledger.mined_blocks, 1)

    def test_inventory_requires_server_revision_and_consistency(self):
        ledger = TransactionLedger()
        before = self.telemetry()
        ledger.observe(before, None)
        after = copy.deepcopy(before)
        after["inventory"]["log"] = 1
        with self.assertRaises(ObservationError):
            ledger.observe(after, None)
        after["inventory_revision"] = 2
        self.assertEqual(ledger.observe(after, None)["log"], 1)
        with self.assertRaises(ObservationError):
            ledger.observe(after | {"inventory_consistent": False}, None)

    def test_creative_or_privileged_observation_rejected(self):
        for telemetry in (self.telemetry(game_mode="CREATIVE"), self.telemetry(world_seed=123)):
            with self.assertRaises(ObservationError):
                TransactionLedger().observe(telemetry, None)

    def test_goal_completes_only_on_acknowledged_inventory_gain(self):
        with tempfile.TemporaryDirectory() as directory:
            controller = self.controller(Path(directory))
            try:
                first = controller.evaluate_request(self.request(10))
                second = controller.evaluate_request(self.request(20, ack=self.ack(first)))
                self.assertEqual(second["autonomy_status"], "running")
                after = self.telemetry(inventory_revision=2)
                after["inventory"]["log"] = 1
                final = controller.evaluate_request(self.request(30, telemetry=after, ack=self.ack(second)))
                self.assertEqual(final["autonomy_status"], "success")
                self.assertEqual(final["command_id"], 0)
            finally:
                controller.close()

    def test_failed_block_interaction_triggers_bounded_recovery(self):
        with tempfile.TemporaryDirectory() as directory:
            controller = self.controller(Path(directory))
            try:
                response = controller.evaluate_request(self.request(10))
                for tick in (20, 30):
                    response = controller.evaluate_request(self.request(tick, ack=self.ack(response, status="failed", error="mining_timeout", changed=False)))
                self.assertGreaterEqual(controller.agent.session["failed_actions"], 2)
                self.assertGreaterEqual(len(controller.agent.recovery.events), 1)
                self.assertFalse(controller.agent.session["success"])
            finally:
                controller.close()

    def test_missing_ack_times_out_without_replaying_command(self):
        with tempfile.TemporaryDirectory() as directory:
            controller = self.controller(Path(directory))
            try:
                first = controller.evaluate_request(self.request(10))
                for tick in range(20, 70, 10):
                    response = controller.evaluate_request(self.request(tick))
                    self.assertEqual(response["command_id"], 0)
                self.assertEqual(response["autonomy_status"], "acknowledgment_timeout")
                self.assertGreater(first["command_id"], 0)
            finally:
                controller.close()

    def test_connection_reset_interrupts_previous_goal(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            controller = self.controller(folder)
            try:
                controller.evaluate_request(self.request(10))
                controller.evaluate_request(self.request(20, episode="reconnected"))
                records = [json.loads(line) for line in (folder / "results.jsonl").read_text().splitlines()]
                self.assertEqual(records[0]["termination"], "minecraft_episode_interrupted")
                self.assertFalse(records[0]["success"])
            finally:
                controller.close()

    def test_crafting_failure_does_not_create_inventory_or_success(self):
        with tempfile.TemporaryDirectory() as directory:
            controller = self.controller(Path(directory), forced="CRAFT_PLANKS")
            observation = self.telemetry(allowed_actions=["NO_OP", "CRAFT_PLANKS"])
            observation["inventory"]["log"] = 1
            try:
                first = controller.evaluate_request(self.request(10, goal="planks", telemetry=observation))
                controller.evaluate_request(self.request(20, goal="planks", telemetry=observation,
                    ack=self.ack(first, action="CRAFT_PLANKS", status="failed", error="crafting_timeout", changed=False)))
                self.assertEqual(controller.ledger.previous["planks"], 0)
                self.assertFalse(controller.agent.session["success"])
            finally:
                controller.close()

    def test_pending_transaction_checkpoint_restores_without_replay(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            controller = self.controller(folder)
            first = controller.evaluate_request(self.request(10))
            controller.save_state(folder / "pending.npz")
            controller.close()
            restored = self.controller(folder, checkpoint=folder / "pending.npz", result="restored")
            try:
                after = self.telemetry(inventory_revision=2)
                after["inventory"]["log"] = 1
                response = restored.evaluate_request(self.request(20, telemetry=after, ack=self.ack(first)))
                self.assertEqual(response["autonomy_status"], "success")
                self.assertEqual(restored.command_id, first["command_id"])
            finally:
                restored.close()

    def test_neural_removal_keeps_context_and_changes_neural_inputs(self):
        from unittest import mock
        with tempfile.TemporaryDirectory() as directory:
            controller = self.controller(Path(directory))
            try:
                original = controller.agent.choose_action
                inputs = []
                def choose(observation, *, neural):
                    inputs.append(neural.copy())
                    return original(observation, neural=neural)
                with mock.patch.object(controller.agent, "choose_action", side_effect=choose):
                    controller.evaluate_request(self.request(10, condition="no_neural"))
                np.testing.assert_array_equal(inputs[0], [1., 0., 0., 0.])
            finally:
                controller.close()

    def test_completed_checkpoint_does_not_emit_a_previous_episode(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            original = self.controller(folder)
            first = original.evaluate_request(self.request(10))
            after = self.telemetry(inventory_revision=2)
            after["inventory"]["log"] = 1
            original.evaluate_request(self.request(20, telemetry=after, ack=self.ack(first)))
            original.save_state(folder / "complete.npz")
            original.close()
            restored = self.controller(folder, checkpoint=folder / "complete.npz", result="fresh")
            restored.evaluate_request(self.request(30, episode="fresh"))
            self.assertEqual((folder / "fresh.jsonl").read_text(), "")
            restored.close()
            records = [json.loads(line) for line in (folder / "fresh.jsonl").read_text().splitlines()]
            self.assertEqual([row["episode_id"] for row in records], ["fresh"])


if __name__ == "__main__":
    unittest.main()
