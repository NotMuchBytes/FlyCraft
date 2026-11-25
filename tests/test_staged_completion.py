"""Shutdown eligibility only: tests never invoke an operating-system action."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from autonomy.experiment import atomic_json, digest

path = Path(__file__).resolve().parents[1] / "experiments/phase9/staged25_operations/finish_when_staged_verified.py"
spec = importlib.util.spec_from_file_location("staged_shutdown_tests", path)
companion = importlib.util.module_from_spec(spec)
spec.loader.exec_module(companion)


class StagedCompletionTests(unittest.TestCase):
    def prepare(self, folder):
        self.config = dict(curriculum_schema="staged-terrain-v1", world_limit=10000,
            official_experiment_authorized=True, pending_skills=[], supported_stages=[dict(id="last")],
            foundation=dict(foundation_world_instances=9998), recording_milestones=[10000])
        atomic_json(folder / "seeds.json", dict(training=[101, 102]))
        self.config["catalog_sha256"] = digest(folder / "seeds.json")
        checkpoint = dict(path="sealed_final", sha256="proof_checked_only_after_eligibility")
        self.state = dict(status="curriculum_complete", active_attempt=None, final_policy=checkpoint,
            current_checkpoint=checkpoint, curriculum_index=1, gates=dict(last=dict(passed=True)),
            attempts=[dict(split="training", generated_world_instances=1, official_world_number=9999+i,
                world_seed=101+i, status="committed", video_required=i == 1) for i in range(2)])
        atomic_json(folder / "executor.json", dict(status="training_budget_complete", final_checkpoint=checkpoint))
        self.save(folder)

    def save(self, folder):
        atomic_json(folder / "config.json", self.config)
        self.state["config_sha256"] = digest(folder / "config.json")
        atomic_json(folder / "state.json", self.state)

    def test_pending_skills_failed_gate_or_partial_state_cannot_mean_done(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            self.prepare(folder)
            self.assertTrue(companion.completion_ready(folder))
            self.config["pending_skills"] = ["combat"]
            self.save(folder)
            self.assertFalse(companion.completion_ready(folder))
            self.config["pending_skills"] = []
            self.state["gates"]["last"]["passed"] = False
            self.save(folder)
            self.assertFalse(companion.completion_ready(folder))
            self.state["gates"]["last"]["passed"] = True
            self.state["status"] = "awaiting_next_skill_implementation"
            self.save(folder)
            self.assertFalse(companion.completion_ready(folder))

    def test_stop_duplicates_and_missing_recording_block_shutdown(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            self.prepare(folder)
            (folder / "STOP").touch()
            self.assertFalse(companion.completion_ready(folder))
            (folder / "STOP").unlink()
            self.state["attempts"][1]["official_world_number"] = 9999
            self.save(folder)
            self.assertFalse(companion.completion_ready(folder))
            self.state["attempts"][1]["official_world_number"] = 10000
            self.state["attempts"][1]["video_required"] = False
            self.save(folder)
            with self.assertRaisesRegex(ValueError, "milestone"):
                companion.completion_ready(folder)
