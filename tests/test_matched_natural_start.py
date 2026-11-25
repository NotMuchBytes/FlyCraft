"""Matched control setup uses recorded own pose, never resource locations."""
import json
from pathlib import Path
import tempfile
import unittest

from autonomy.evidence import EvidenceError, verify_start_pose
from autonomy.staged import reference_start


class MatchedNaturalStartTests(unittest.TestCase):
    def test_reference_needs_the_scored_trained_cell_and_empty_inventory(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            path = folder / "server.jsonl.initial.jsonl"
            initial = dict(world_seed=27, game_mode="SURVIVAL", inventory=dict(log=0),
                           position_xyz_yaw_pitch=[7.5, 64., -3.5, 17., 0.])
            path.write_text(json.dumps(initial)+"\n")
            attempt = dict(curriculum_stage="exploration", split="eval_a", evaluation_task="primary",
                evaluation_index=4, condition="trained", status="committed", world_seed=27, results=str(folder))
            self.assertEqual(reference_start([attempt],stage="exploration",index=4,seed=27), initial["position_xyz_yaw_pitch"])
            with self.assertRaisesRegex(ValueError, "reference"):
                reference_start([attempt],stage="exploration",index=4,seed=28)
            initial["inventory"]["log"] = 1
            path.write_text(json.dumps(initial)+"\n")
            with self.assertRaisesRegex(ValueError, "empty"):
                reference_start([attempt],stage="exploration",index=4,seed=27)

    def test_checker_requires_actual_native_pose_and_rejects_nan_or_drift(self):
        pose = [7.5,64.,-3.5,17.,0.]
        metadata = dict(environment_kind="vanilla_overworld_spawn",natural_start_requested=pose)
        verify_start_pose(metadata,dict(trial_0000=dict(position_xyz_yaw_pitch=list(pose))))
        for actual in (None, [7.5,64.,-2.5,17.,0.], [float("nan"),64.,-3.5,17.,0.]):
            with self.assertRaises(EvidenceError):
                verify_start_pose(metadata,dict(trial_0000=dict(position_xyz_yaw_pitch=actual)))
        with self.assertRaises(EvidenceError):
            verify_start_pose(metadata,{})
