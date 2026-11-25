"""Completion/shutdown tests are synthetic and never shut down the machine."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("campaign_completion",
    ROOT / "experiments/phase9/fc9_20261125_operations/finish_when_verified.py")
completion = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(completion)


class CompletionTests(unittest.TestCase):
    def fixture(self, root):
        goals = ["one_log", "three_logs", "planks", "wooden_pickaxe"]
        config = dict(stage="official_training", world_limit=10000, official_experiment_authorized=True,
                      goal_schedule=goals, recording_milestones=[1, 10, 10000])
        (root / "seeds.json").write_text(json.dumps({"training": list(range(10000))}))
        config["catalog_sha256"] = completion.digest(root / "seeds.json")
        (root / "config.json").write_text(json.dumps(config))
        checkpoint = {"path": "synthetic-only", "sha256": "unit-only"}
        state = dict(active_attempt=None, config_sha256=completion.digest(root / "config.json"),
            final_policy=checkpoint, current_checkpoint=checkpoint,
            attempts=[dict(split="training", generated_world_instances=1, official_world_number=i+1,
                world_seed=i, goal=goals[i % 4], status="committed", video_required=i+1 in config["recording_milestones"])
                for i in range(10000)])
        (root / "state.json").write_text(json.dumps(state))
        (root / "executor.json").write_text(json.dumps(dict(status="training_budget_complete", final_checkpoint=checkpoint)))
        return state

    def test_only_full_unique_budget_with_all_milestones_is_ready(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state = self.fixture(root)
            self.assertTrue(completion.completion_ready(root))
            state["attempts"][-1]["official_world_number"] = 9999
            (root / "state.json").write_text(json.dumps(state))
            self.assertFalse(completion.completion_ready(root))
            state["attempts"][-1]["official_world_number"] = 10000
            state["attempts"][-1]["status"] = "interrupted"
            (root / "state.json").write_text(json.dumps(state))
            with self.assertRaisesRegex(ValueError, "milestone"):
                completion.completion_ready(root)

    def test_running_stop_attention_or_wrong_seed_cannot_shutdown(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state = self.fixture(root)
            for marker in ("STOP", "fix_request.json"):
                (root / marker).touch()
                self.assertFalse(completion.completion_ready(root))
                (root / marker).unlink()
            state["active_attempt"] = 3
            (root / "state.json").write_text(json.dumps(state))
            self.assertFalse(completion.completion_ready(root))
            state["active_attempt"] = None
            state["attempts"][100]["world_seed"] = -1
            (root / "state.json").write_text(json.dumps(state))
            with self.assertRaisesRegex(ValueError, "schedule"):
                completion.completion_ready(root)

    def test_cancel_leaves_power_guard_and_machine_running(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "CANCEL_SHUTDOWN").touch()
            invoke = mock.Mock()
            self.assertFalse(completion.shutdown_after_verification(root, root, root / "status.json", {}, invoke=invoke))
            invoke.assert_not_called()
            self.assertFalse((root / "RELEASE").exists())

    def test_completion_releases_guard_then_requests_nonforced_shutdown(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            guard = root / "guard"
            guard.mkdir()
            (guard / "status.json").write_text(json.dumps({"blocks_normal_shutdown": False}))
            invoke = mock.Mock()
            with mock.patch.object(completion, "completion_ready", return_value=True):
                self.assertTrue(completion.shutdown_after_verification(root, guard, root / "status.json", {},
                    sleep=lambda _: None, invoke=invoke))
            self.assertTrue((guard / "RELEASE").exists())
            command = invoke.call_args.args[0]
            self.assertEqual(command[-3:], ["/s", "/t", "0"])
            self.assertNotIn("/f", command)


if __name__ == "__main__":
    unittest.main()
