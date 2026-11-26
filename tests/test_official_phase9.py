"""Synthetic orchestration tests: these are not Minecraft training results."""

import argparse
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

from autonomy.experiment import Campaign, RESOURCE_GOALS
from autonomy.official import cleanup_world, validate_worker
from learning import NeuralFeatureTable
from tools.run_official_phase9 import run, OFFICIAL_MILESTONES
from tools.run_phase9 import worker_command

ROOT = Path(__file__).resolve().parents[1]
CHECKPOINT = ROOT / "checkpoints/phase8/finish_20261123/progress_readout_mining.npz"


class OfficialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.table = NeuralFeatureTable.from_phase35(ROOT / "experiments/phase35/results/rate_decoder_evaluation.json")

    def campaign(self, root, **changes):
        graph = root / "data/processed/connectome_raw_csr.npz"
        graph.parent.mkdir(parents=True)
        graph.write_bytes(b"UNIT TEST GRAPH MARKER - NOT A CONNECTOME")
        options = dict(name="official_unit", checkpoint=CHECKPOINT, worlds=10000,
                       checked=True, official=True, forward_ticks=2, compact=True,
                       authorization={"statement": "synthetic unit authorization", "authorized_date": "unit-only"},
                       recording_policy="milestones", recording_milestones=OFFICIAL_MILESTONES)
        options.update(changes)
        return Campaign.create(root / "campaign", project_root=root, table=self.table, **options)

    def finish_without_score(self, campaign, attempt, *, created):
        if created:
            (Path(attempt["runtime"]) / "server/world").mkdir(parents=True)
        return campaign.recover()

    def test_authorization_and_budget_are_required(self):
        for changes in ({"authorization": None}, {"checked": False}, {"worlds": 9999}, {"official": False}):
            with self.subTest(changes=changes), tempfile.TemporaryDirectory() as directory:
                with self.assertRaises(ValueError):
                    self.campaign(Path(directory), **changes)

    def test_generated_partial_world_consumes_seed_and_goal_but_prelaunch_does_not(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            campaign = self.campaign(root)
            first = campaign.begin("training", runtime_root=root / "work")
            self.finish_without_score(campaign, first, created=False)
            retry = campaign.begin("training", runtime_root=root / "work")
            self.assertEqual(first["world_seed"], retry["world_seed"])
            self.finish_without_score(campaign, retry, created=True)
            second = campaign.begin("training", runtime_root=root / "work")
            self.assertEqual(second["official_world_number"], 2)
            self.assertEqual(second["goal"], "three_logs")
            self.assertNotEqual(second["world_seed"], first["world_seed"])
            self.assertEqual(campaign.summary()["official_training_worlds"], 1)
            self.assertEqual(campaign.summary()["training_episodes"], 0)
            self.assertEqual(campaign.state["current_checkpoint"], campaign.config["initial_checkpoint"])

    def test_balanced_schedule_disjoint_partitions_and_final_boundary(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            campaign = self.campaign(root)
            seeds = campaign.catalog["training"]
            for split in ("pilot", "eval_a", "eval_b"):
                self.assertFalse(set(seeds) & set(campaign.catalog[split]))
            self.assertEqual({g: sum(i % 4 == n for i in range(10000)) for n, g in enumerate(RESOURCE_GOALS)},
                             {g: 2500 for g in RESOURCE_GOALS})
            for split in ("pilot", "eval_a", "eval_b"):
                with self.assertRaises(ValueError):
                    campaign.begin(split)
            # Synthetic ledger only; no Minecraft processes or worlds generated.
            campaign.state["attempts"] = [dict(split="training", generated_world_instances=1,
                status="interrupted", finished_unix=1, started_unix=0, world_seed=seeds[i],
                goal=list(RESOURCE_GOALS)[i % 4]) for i in range(9999)]
            final = campaign.begin("training", runtime_root=root / "work")
            self.assertEqual(final["official_world_number"], 10000)
            self.assertEqual(final["world_seed"], seeds[-1])
            self.assertEqual(final["goal"], "wooden_pickaxe")
            self.finish_without_score(campaign, final, created=True)
            with self.assertRaisesRegex(ValueError, "complete"):
                campaign.begin("training")
            self.assertEqual(campaign.training_worlds(), 10000)

    def test_worker_profile_and_manifest_reject_configuration_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            campaign = self.campaign(root)
            args = SimpleNamespace(work_dir=root / "work", build_dir=root / "build", obs_control_dir=root / "obs", video_export_dir=None)
            for number, goal in enumerate(RESOURCE_GOALS, 1):
                attempt = campaign.begin("training", runtime_root=args.work_dir)
                self.assertEqual(attempt["goal"], goal)
                command = worker_command(campaign, attempt, args, 300)
                self.assertIn("--campaign-manifest", command)
                self.assertIn("--train", command)
                self.assertEqual(command[command.index("--trial-ticks") + 1],
                                 "1500" if goal in ("three_logs", "wooden_pickaxe") else "400")
                values = dict(run_id=attempt["run_id"], official_world_number=number, world_seed=attempt["world_seed"],
                    layout_start=attempt["layout_seed"], policy_seed=attempt["policy_seed"], goals=goal,
                    conditions="trained", train=True, headless=True, trials=1, camera_mode="bounded", pitch_actions=True,
                    spectator=True, milestone=number, operator_fault="none", natural_world=False,
                    blocked_forward_fixture=False, explore_forward=False, jump_on_blocked_forward=False, camera_probe=False,
                    movement_feedback="displacement", layout_seeds=None, natural_start=None, unplaced_table_fixture=False,
                    graphics_backend="opengl", launcher="direct", minimum_available_ram_mib=768, minimum_free_disk_mib=2048,
                    checkpoint=Path(attempt["checkpoint"]["path"]), frozen_checkpoint=Path(campaign.config["frozen_checkpoint"]["path"]),
                    stop_file=campaign.folder / "STOP", work_dir=args.work_dir)
                profile = campaign.runtime_profile(goal)
                values.update({key: profile[key] for key in ("turn_degrees", "forward_ticks", "trial_ticks", "three_tree_fixture", "remember_mined_columns", "server_heap_mib", "client_heap_mib")})
                values.update(capture_width=profile["width"], capture_height=profile["height"])
                worker = SimpleNamespace(**values)
                self.assertEqual(validate_worker(worker, root, campaign=campaign)["official_world_number"], number)
                for field, wrong in (("train", False), ("world_seed", 3), ("trial_ticks", 1), ("minimum_available_ram_mib", 100), ("checkpoint", root / "wrong.npz")):
                    original = getattr(worker, field)
                    setattr(worker, field, wrong)
                    with self.subTest(field=field), self.assertRaises(ValueError):
                        validate_worker(worker, root, campaign=campaign)
                    setattr(worker, field, original)
                self.finish_without_score(campaign, attempt, created=True)

    def test_cleanup_preserves_milestones_unverified_worlds_and_logs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            campaign = self.campaign(root)
            attempt = campaign.begin("training", runtime_root=root / "work")
            world = Path(attempt["runtime"]) / "server/world"
            world.mkdir(parents=True)
            (world / "level.dat").write_bytes(b"synthetic world")
            log = world.parent / "server.log"
            log.write_text("keep evidence")
            attempt.update(status="committed", checker_status="verified")
            self.assertFalse(cleanup_world(campaign, attempt, root / "work"))
            attempt["video_required"] = False
            attempt["checker_status"] = "needs_attention"
            self.assertFalse(cleanup_world(campaign, attempt, root / "work"))
            attempt["checker_status"] = "verified"
            with self.assertRaises(ValueError):
                cleanup_world(campaign, dict(attempt, runtime=str(root / "outside")), root / "work")
            self.assertTrue(cleanup_world(campaign, attempt, root / "work"))
            self.assertFalse(world.exists())
            self.assertTrue(log.exists())
            self.assertFalse(cleanup_world(campaign, attempt, root / "work"))

    def test_executor_never_clears_stop_or_starts_final_evaluation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            campaign = self.campaign(root)
            args = argparse.Namespace(work_dir=root / "work")
            calls = []

            def batch(current, options, *, official):
                calls.append((options.split, options.condition, official))
                (current.folder / "STOP").touch()
                return 0

            self.assertEqual(run(campaign, args, batch=batch), 0)
            self.assertEqual(calls, [("training", "trained", True)])
            self.assertTrue((campaign.folder / "STOP").exists())
            self.assertIsNone(campaign.state["final_policy"])


if __name__ == "__main__":
    unittest.main()
