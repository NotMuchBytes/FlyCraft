import json
import socket
import tempfile
import threading
import unittest
from unittest import mock
from pathlib import Path

from autonomy import AutonomousAgent, AutonomyConfig
from autonomy.bridge import LiveNavigationController
from learning import NeuralFeatureTable
from minecraft_bridge import BridgeServer

ROOT = Path(__file__).resolve().parents[1]


class FakeNeural:
    """Protocol fixture; full-network parity has a separate real-graph check."""
    def __init__(self, table):
        self.table = table

    def neural_observation(self, sector):
        return self.table.for_sector(sector), None, 100


class AutonomyBridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.table = NeuralFeatureTable.from_phase35(ROOT / "experiments/phase35/results/rate_decoder_evaluation.json")

    def request(self, tick, *, distance=5, session="test", sector="center"):
        return {"tick_id": tick, "sector": sector, "telemetry": {"session_id": session, "position": [0, 0, 0], "target_distance": distance}}

    def test_goal_telemetry_stopping_tick_rejection_and_checkpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "initial.npz"
            saved = Path(directory) / "finished.npz"
            AutonomousAgent(self.table, seed=29, config=AutonomyConfig(max_steps=2)).save(path)
            controller = LiveNavigationController(FakeNeural(self.table), path, save_path=saved)
            first = controller.evaluate_request(self.request(10))
            self.assertIn(first["action"], ("NO_OP", "TURN_LEFT", "TURN_RIGHT", "FORWARD"))
            with self.assertRaises(ValueError):
                controller.evaluate_request(self.request(10))
            second = controller.evaluate_request(self.request(20, distance=0.7))
            self.assertEqual(second["autonomy_status"], "success")
            self.assertEqual(second["action"], "NO_OP")
            self.assertTrue(saved.exists())
            self.assertEqual(controller.evaluate_request(self.request(30))["goal_actions"], 1)
            with self.assertRaises(ValueError):
                controller.evaluate_request({"tick_id": 40})

    def test_new_world_does_not_apply_old_action_outcome(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "initial.npz"
            AutonomousAgent(self.table).save(path)
            controller = LiveNavigationController(FakeNeural(self.table), path)
            controller.evaluate_request(self.request(100))
            result = controller.evaluate_request(self.request(1, session="new_world"))
            self.assertEqual(result["goal_actions"], 0)
            self.assertEqual(controller.agent.memory.world_id, "minecraft:new_world")

    def test_real_tcp_protocol_supports_legacy_and_autonomy_controllers(self):
        class Legacy:
            def evaluate(self, sector):
                return {"action": "NO_OP", "latency_ms": 0}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "initial.npz"
            AutonomousAgent(self.table).save(path)
            for controller in (Legacy(), LiveNavigationController(FakeNeural(self.table), path)):
                with BridgeServer(("127.0.0.1", 0), controller, Path(directory) / "log.jsonl") as server:
                    thread = threading.Thread(target=server.serve_forever, daemon=True)
                    thread.start()
                    try:
                        with socket.create_connection(server.server_address, timeout=2) as connection:
                            connection.sendall((json.dumps(self.request(10)) + "\n").encode())
                            response = json.loads(connection.makefile("r").readline())
                        self.assertEqual(response["status"], "ok")
                        self.assertEqual(response["tick_id"], 10)
                    finally:
                        server.shutdown()
                        thread.join(timeout=2)

    def test_logging_survives_a_path_reopen_lock(self):
        with tempfile.TemporaryDirectory() as directory:
            with BridgeServer(("127.0.0.1", 0), object(), Path(directory) / "events.jsonl") as server:
                with mock.patch.object(Path, "open", side_effect=PermissionError("simulated sync lock")):
                    server.write_log({"event": "still_logged"})
            self.assertIn("still_logged", (Path(directory) / "events.jsonl").read_text())


if __name__ == "__main__":
    unittest.main()
