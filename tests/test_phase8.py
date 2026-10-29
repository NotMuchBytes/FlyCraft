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

    def test_blocked_movement_feedback_replans_but_policy_selects_recovery_action(self):
        with tempfile.TemporaryDirectory() as directory:
            controller=self.controller(Path(directory),forced="FORWARD")
            telemetry=self.telemetry(visible=False,near=False,target_distance=-1,
                allowed_actions=["FORWARD","TURN_LEFT","TURN_RIGHT","NO_OP"])
            def request(tick,ack=None):
                row=self.request(tick,telemetry=telemetry,ack=ack)
                row["sector"]="not_visible"
                return row
            try:
                response=controller.evaluate_request(request(10))
                self.assertEqual(response["action"],"FORWARD")
                for tick in (20,30):
                    ack=self.ack(response,action="FORWARD",status="failed",error="movement_blocked",changed=False)
                    ack.update(movement_distance=0.,movement_confirmed=False)
                    response=controller.evaluate_request(request(tick,ack))
                self.assertEqual(controller.agent.session["failed_actions"],2)
                self.assertEqual(controller.agent.recovery.events[0]["reason"],"repeated_failure")
                self.assertNotEqual(response["action"],"FORWARD")
                self.assertFalse(controller.agent.session["success"])
                self.assertEqual(controller.ledger.previous["log"],0)
            finally:
                controller.close()

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

    def boundary(self, folder, controller, *, logs):
        request=self.request(20)
        control=request["control"] | {"active":False,"terminal":{
            "server_tick":400,"inventory":self.telemetry()["inventory"] | {"log":logs},"position":[0.,0.,0.]}}
        path=folder/"control.json"
        path.write_text(json.dumps(control))
        controller.control_file=path
        return path

    def test_boundary_snapshot_rejects_late_pickup_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory); controller=self.controller(folder)
            try:
                first=controller.evaluate_request(self.request(10))
                path=self.boundary(folder,controller,logs=0)
                late=self.telemetry(inventory_revision=2)
                late["inventory"]["log"]=1
                result=controller.evaluate_request(self.request(20,telemetry=late,ack=self.ack(first)))
                self.assertEqual(result["autonomy_status"],"episode_boundary")
                self.assertTrue(result["terminal_acknowledged"])
                self.assertFalse(controller.agent.session["success"])
                self.assertEqual(controller.ledger.previous["log"],0)
                self.assertEqual(controller.agent.session["terminal_server_tick"],400)
                self.assertEqual(controller.command_id,first["command_id"])
                controller.evaluate_request(self.request(30,telemetry=late))
                self.assertEqual(len((folder/"results.jsonl").read_text().splitlines()),1)
                self.assertEqual(json.loads(Path(str(path)+".ack").read_text())["episode_id"],"unit")
                with self.assertRaises(ObservationError):
                    controller.ledger.observe(late,None)
            finally:
                controller.close()

    def test_boundary_can_confirm_inventory_before_client_packet_arrives(self):
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory); controller=self.controller(folder)
            try:
                first=controller.evaluate_request(self.request(10))
                self.boundary(folder,controller,logs=1)
                result=controller.evaluate_request(self.request(20,ack=self.ack(first)))
                self.assertEqual(result["autonomy_status"],"success")
                self.assertEqual(controller.agent.session["terminal_inventory"]["log"],1)
                self.assertEqual(controller.agent.session["actions"],1)
            finally:
                controller.close()

    def test_unexecuted_terminal_command_cannot_train_or_count_as_action(self):
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory); controller=self.controller(folder)
            try:
                first=controller.evaluate_request(self.request(10,train=True))
                weights=controller.agent.policy.weights.copy()
                self.boundary(folder,controller,logs=0)
                result=controller.evaluate_request(self.request(20,ack=self.ack(first,status="not_executed",changed=False)))
                self.assertTrue(result["terminal_acknowledged"])
                self.assertEqual(controller.agent.session["actions"],0)
                self.assertEqual(controller.agent.session["training_suppressed"],"unexecuted_terminal_command")
                np.testing.assert_array_equal(controller.agent.policy.weights,weights)
            finally:
                controller.close()

    def test_missing_terminal_ack_is_bounded_and_suppresses_learning(self):
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory); controller=self.controller(folder)
            try:
                controller.evaluate_request(self.request(10,train=True))
                self.boundary(folder,controller,logs=0)
                for tick in range(20,70,10):
                    result=controller.evaluate_request(self.request(tick))
                    self.assertEqual(result["command_id"],0)
                self.assertEqual(result["autonomy_status"],"terminal_ack_missing")
                self.assertFalse(controller.agent.session["train"])
                self.assertEqual(controller.agent.session["actions"],0)
            finally:
                controller.close()

    def test_passive_terminal_pickup_accounts_reward_without_crediting_unexecuted_action(self):
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory); controller=self.controller(folder)
            try:
                first=controller.evaluate_request(self.request(10,train=True))
                second=controller.evaluate_request(self.request(20,train=True,ack=self.ack(first)))
                weights=controller.agent.policy.weights.copy()
                prior_reward=controller.agent.session["total_reward"]
                trajectory_length=len(controller.agent.trajectory)
                self.boundary(folder,controller,logs=1)
                result=controller.evaluate_request(self.request(30,ack=self.ack(second,status="not_executed",changed=False)))
                session=controller.agent.session
                self.assertEqual(result["autonomy_status"],"success")
                self.assertEqual(session["actions"],1)
                self.assertEqual(len(controller.agent.trajectory),trajectory_length)
                self.assertAlmostEqual(session["unattributed_terminal_reward"],8.25)
                self.assertAlmostEqual(session["total_reward"],prior_reward+8.25)
                self.assertEqual(session["subgoals_complete"],session["subgoals"])
                self.assertIn("root",session["completed"])
                self.assertEqual(controller.agent.memory.inventory["log"],1)
                self.assertFalse(session["train"])
                np.testing.assert_array_equal(controller.agent.policy.weights,weights)
                controller.evaluate_request(self.request(40))
                self.assertAlmostEqual(session["total_reward"],prior_reward+8.25)
            finally:
                controller.close()

    def test_delayed_old_episode_observation_cannot_mutate_new_lifecycle(self):
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory); controller=self.controller(folder)
            try:
                first=controller.evaluate_request(self.request(10))
                path=folder/"control.json"
                path.write_text(json.dumps(self.request(20,episode="replacement")["control"] | {"active":True}))
                controller.control_file=path
                response=controller.evaluate_request(self.request(20,ack=self.ack(first)))
                self.assertTrue(response["observe_only"])
                self.assertEqual(controller.episode_id,"unit")
                self.assertEqual(controller.agent.session["actions"],0)
            finally:
                controller.close()

    def test_shuffled_control_permutates_actual_window_even_for_center_sector(self):
        with tempfile.TemporaryDirectory() as directory:
            controller=self.controller(Path(directory))
            try:
                controller.neural.neural_observation=lambda sector:(np.array([1.,.11,.22,.33]),None,123)
                response=controller.evaluate_request(self.request(10,condition="shuffled"))
                np.testing.assert_allclose(controller.agent.pending[0][:4],[1.,.33,.11,.22])
                self.assertEqual(response["neural_features"]["left_readout_div50"],.11)
                self.assertEqual(response["policy_neural_inputs"]["left_input"],.33)
                self.assertEqual(response["peak_global_active"],123)
                self.assertAlmostEqual(sum(response["action_probabilities"].values()),1)
                self.assertIn("permutation",response["feature_intervention"])
            finally:
                controller.close()

    def test_success_boundary_cancellation_is_not_failed_gameplay_or_recovery(self):
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory); controller=self.controller(folder)
            try:
                first=controller.evaluate_request(self.request(10))
                second=controller.evaluate_request(self.request(20,ack=self.ack(first)))
                self.boundary(folder,controller,logs=1)
                result=controller.evaluate_request(self.request(30,ack=self.ack(second,status="interrupted",error="episode_boundary",changed=False)))
                session=controller.agent.session
                self.assertEqual(result["autonomy_status"],"success")
                self.assertEqual(session["actions"],2)
                self.assertEqual(session["failed_actions"],0)
                self.assertEqual(len(controller.agent.recovery.events),0)
                self.assertAlmostEqual(session["total_reward"],8.21)
                self.assertEqual(session["subgoals_complete"],session["subgoals"])
            finally:
                controller.close()


if __name__ == "__main__":
    unittest.main()
