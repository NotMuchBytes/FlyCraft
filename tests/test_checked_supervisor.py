"""Evidence tampering and supervision tests; temporary copies are not live trials."""

import argparse
import json
from pathlib import Path
import shutil
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

from autonomy.agent import AutonomousAgent
from autonomy.evidence import audit_run, EvidenceError
from autonomy.experiment import Campaign, CampaignLock, atomic_json, source_manifest, seed_catalog
from learning import NeuralFeatureTable
from tools import supervise_phase9 as supervisor
from tools.obs_session import archive_stale_markers, check_profile
from tools.run_phase9 import worker_command

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "experiments/phase9/p8_mining_20261124_pickaxe_milestone"
CHECKPOINT = ROOT / "checkpoints/phase8/finish_20261123/progress_readout_mining.npz"


def load(path):
    return json.loads(path.read_text())


def rewrite_rows(path, change):
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    change(rows)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


class CheckedSupervisorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.table = NeuralFeatureTable.from_phase35(ROOT / "experiments/phase35/results/rate_decoder_evaluation.json")

    def evidence(self, folder, *, failed=False):
        destination = folder / "evidence"
        destination.mkdir(parents=True)
        source = ROOT / "experiments/phase9/p8_gate_20261124_b1_long_a1" if failed else SOURCE
        for path in source.iterdir():
            if path.suffix in (".json", ".jsonl"):
                shutil.copy2(path, destination / path.name)
        meta = load(destination / "run.json")
        if failed:
            candidates = [json.loads(line) for line in (destination/"server.jsonl").read_text().splitlines()]
            chosen = next(row for row in candidates if row["goal"] == "wooden_pickaxe" and not row["success"])
            identity = chosen["episode_id"]
            for path in destination.glob("*.jsonl"):
                if path.name == "camera.jsonl":
                    continue
                rows = [json.loads(line) for line in path.read_text().splitlines()]
                if path.name == "bridge.jsonl":
                    rows = [row for row in rows if (row.get("response") or {}).get("episode_id") == identity]
                else:
                    rows = [row for row in rows if row.get("episode_id") == identity]
                path.write_text("".join(json.dumps(row) + "\n" for row in rows))
            meta.update(requested=1, completed=1, goals=["wooden_pickaxe"], layout_seeds=[chosen["layout_seed"]])
        meta.update(milestone=None, recording=None, spectator=False, client_exited_cleanly=None,
                    recording_mode="structured_event_logs_no_video")
        atomic_json(destination / "run.json", meta)
        return destination

    def campaign(self, folder, *, goal="wooden_pickaxe", worlds=4):
        graph = folder / "data/processed/connectome_raw_csr.npz"
        graph.parent.mkdir(parents=True)
        graph.write_bytes(b"SYNTHETIC UNIT GRAPH MARKER, NOT A CONNECTOME")
        return Campaign.create(folder / "campaign", project_root=folder, name="checker_unit",
            checkpoint=CHECKPOINT, table=self.table, goal=goal, checked=True, worlds=worlds,
            forward_ticks=2, recording_policy="milestones", recording_milestones=(100,))

    def planned_evidence(self, campaign, *, training=False, failed=False):
        attempt = campaign.begin("pilot" if training else "eval_a", runtime_root=campaign.root / "runtime")
        data = self.evidence(campaign.root, failed=failed)
        meta = load(data / "run.json")
        meta.update(world_seed=attempt["world_seed"], layout_seeds=[attempt["layout_seed"]],
                    implementation_sha256=campaign.config["implementation_sha256"], train=training,
                    frozen_checkpoint_sha256=attempt["checkpoint"]["sha256"])
        atomic_json(data / "run.json", meta)
        atomic_json(data / "source_manifest.json", source_manifest(campaign.root))
        rewrite_rows(data / "server.jsonl", lambda rows: rows[0].update(layout_seed=attempt["layout_seed"], train=training))
        rewrite_rows(data / "server.jsonl.initial.jsonl", lambda rows: rows[0].update(
            world_seed=attempt["world_seed"], layout_seed=attempt["layout_seed"]))
        rewrite_rows(data / "controller.jsonl", lambda rows: rows[0].update(train=training))
        def change_control(rows):
            for row in rows:
                request = json.loads(row["request"])
                if "control" in request:
                    request["control"]["train"] = training
                    row["request"] = json.dumps(request)
        rewrite_rows(data / "bridge.jsonl", change_control)
        if training:
            row = json.loads((data / "controller.jsonl").read_text())
            row["update"]["weight_delta_norm"] = .01
            (data / "controller.jsonl").write_text(json.dumps(row) + "\n")
            agent, _ = AutonomousAgent.load(CHECKPOINT, self.table)
            agent.policy.weights.flat[0] += .01
            agent.session = row
            agent.save(campaign.root / "checkpoints/phase9" / attempt["run_id"] / "trial_0000.npz",
                       extension={"phase8": {"episode_id": row["episode_id"]}})
        destination = campaign.root / "experiments/phase9" / attempt["run_id"]
        destination.parent.mkdir(parents=True)
        data.rename(destination)
        return attempt, destination

    def test_archived_actual_pickaxe_has_independent_block_and_recipe_evidence(self):
        report = audit_run(SOURCE, verify_video=False)
        self.assertEqual(report["status"], "verified")
        self.assertEqual(report["episodes"][0]["confirmed_breaks"], 3)
        self.assertEqual(report["episodes"][0]["inventory"]["wooden_pickaxe"], 1)
        self.assertEqual(report["episodes"][0]["actions"], 45)

    def test_contradictory_inventory_missing_recipe_update_and_wrong_seed_are_rejected(self):
        for damage, expected in (("inventory", "inventory_success"), ("recipe", "missing_recipe"),
                                 ("update", "evaluation_update"), ("seed", "seed_identity"),
                                 ("source", "source_manifest"), ("neural", "neural_intervention")):
            with self.subTest(damage=damage), tempfile.TemporaryDirectory() as directory:
                data = self.evidence(Path(directory))
                if damage == "inventory":
                    # Change all terminal reports consistently: success still needs its actual item.
                    rewrite_rows(data / "server.jsonl", lambda rows: rows[0]["inventory"].update(wooden_pickaxe=0))
                    rewrite_rows(data / "controller.jsonl", lambda rows: rows[0]["terminal_inventory"].update(wooden_pickaxe=0))
                    def change(rows):
                        for row in rows:
                            request = json.loads(row["request"])
                            if request.get("control", {}).get("terminal"):
                                request["control"]["terminal"]["inventory"]["wooden_pickaxe"] = 0
                                row["request"] = json.dumps(request)
                    rewrite_rows(data / "bridge.jsonl", change)
                elif damage == "recipe":
                    def change(rows):
                        rows[:] = [row for row in rows if not (row["event"] == "action_end"
                                   and row["data"]["ack"]["action"] == "CRAFT_PICKAXE")]
                    rewrite_rows(data / "headless.jsonl", change)
                elif damage == "update":
                    rewrite_rows(data / "controller.jsonl", lambda rows: rows[0]["update"].update(weight_delta_norm=.1))
                elif damage == "seed":
                    rewrite_rows(data / "server.jsonl.initial.jsonl", lambda rows: rows[0].update(world_seed=0))
                elif damage == "source":
                    meta = load(data / "run.json"); meta["implementation_sha256"] = "changed"
                    atomic_json(data / "run.json", meta)
                else:
                    def change(rows):
                        for row in rows:
                            response = row.get("response") or {}
                            if response.get("command_id"):
                                response["policy_neural_inputs"]["left_input"] += 1
                                break
                    rewrite_rows(data / "bridge.jsonl", change)
                with self.assertRaisesRegex(EvidenceError, expected):
                    audit_run(data, verify_video=False)

    def test_missing_terminal_ack_and_duplicate_ack_cannot_pass(self):
        for damage, expected in (("boundary", "terminal_acknowledgment"), ("duplicate", "duplicate_ack")):
            with self.subTest(damage=damage), tempfile.TemporaryDirectory() as directory:
                data = self.evidence(Path(directory))
                if damage == "boundary":
                    def change(rows):
                        for row in rows:
                            if row.get("response", {}).get("terminal_acknowledged"):
                                row["response"]["terminal_acknowledged"] = False
                    rewrite_rows(data / "bridge.jsonl", change)
                else:
                    def change(rows):
                        rows.append(next(row for row in rows if row["event"] == "action_end"))
                    rewrite_rows(data / "headless.jsonl", change)
                with self.assertRaisesRegex(EvidenceError, expected):
                    audit_run(data, verify_video=False)

    def test_late_resource_stop_retains_valid_score_but_missing_score_does_not(self):
        with tempfile.TemporaryDirectory() as directory:
            data = self.evidence(Path(directory))
            meta = load(data / "run.json"); meta.update(stop_reason="available_ram_guard", server_exited_cleanly=False)
            atomic_json(data / "run.json", meta)
            self.assertEqual(audit_run(data)["status"], "verified")
            (data / "server.jsonl").write_text("")
            with self.assertRaisesRegex(EvidenceError, "episode_count"):
                audit_run(data)
            meta["completed"] = 0; atomic_json(data / "run.json", meta)
            self.assertEqual(audit_run(data)["status"], "technical_stop")

    def test_valid_policy_failure_is_kept_and_next_episode_uses_a_new_seed(self):
        with tempfile.TemporaryDirectory() as directory:
            campaign = self.campaign(Path(directory))
            attempt, data = self.planned_evidence(campaign, failed=True)
            result = campaign.recover()
            self.assertEqual(result["status"], "committed")
            self.assertFalse(result["success"])
            self.assertEqual(supervisor.classify(campaign, result), "continue")
            following = campaign.begin("eval_a")
            self.assertNotEqual(following["world_seed"], attempt["world_seed"])

    def test_batch_stop_and_existing_attention_prevent_worker_launch(self):
        for attention in (False, True):
            with self.subTest(attention=attention), tempfile.TemporaryDirectory() as directory:
                campaign = self.campaign(Path(directory))
                (campaign.folder / ("fix_request.json" if attention else "STOP")).write_text("{}")
                args = argparse.Namespace(seconds=300, max_attempts=2, split="eval_a", condition="trained",
                    worker_seconds=240, obs_control_dir=Path(directory)/"obs")
                with mock.patch.object(supervisor.subprocess, "Popen") as spawn:
                    result = supervisor.supervise(campaign, args)
                self.assertEqual(result, 2 if attention else 0)
                spawn.assert_not_called()
                self.assertEqual(campaign.state["attempts"], [])

    def test_busy_campaign_is_not_modified_or_given_a_spurious_fix_request(self):
        with tempfile.TemporaryDirectory() as directory:
            campaign = self.campaign(Path(directory))
            argv = ["supervise_phase9.py", "run", "--campaign", str(campaign.folder),
                "--work-dir", directory, "--build-dir", directory, "--obs-control-dir", directory]
            with CampaignLock(campaign.folder), mock.patch("sys.argv", argv):
                self.assertEqual(supervisor.main(), 2)
            self.assertFalse((campaign.folder / "fix_request.json").exists())

    def test_unowned_obs_is_never_started_or_closed_by_the_supervisor(self):
        from tools.obs_session import BackgroundRecorder
        with tempfile.TemporaryDirectory() as directory:
            recorder = BackgroundRecorder(Path(directory)/"obs", Path(directory)/"archive")
            with mock.patch("tools.obs_session.check_profile", return_value={}), \
                 mock.patch("tools.obs_session.obs_running", return_value=True), \
                 mock.patch("tools.obs_session.subprocess.Popen") as spawn:
                with self.assertRaisesRegex(RuntimeError, "unowned OBS"):
                    recorder.ensure_ready()
                recorder.close()
                spawn.assert_not_called()

    def test_official_or_oversized_configuration_cannot_enter_the_supervisor(self):
        for change in ({"world_limit": 10000}, {"official_experiment_authorized": True}):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as directory:
                campaign = self.campaign(Path(directory))
                campaign.config.update(change)
                with self.assertRaisesRegex(ValueError, "at most 100 worlds"):
                    supervisor.supervise(campaign, None)

    def test_checked_checkpoint_advances_only_after_independent_gate_and_is_idempotent(self):
        for corrupt in (False, True):
            with self.subTest(corrupt=corrupt), tempfile.TemporaryDirectory() as directory:
                campaign = self.campaign(Path(directory))
                attempt, data = self.planned_evidence(campaign, training=True)
                before = dict(campaign.state["current_checkpoint"])
                if corrupt:
                    rewrite_rows(data / "server.jsonl.delivery.jsonl", lambda rows: rows[0].update(acknowledged=False))
                result = campaign.recover()
                self.assertEqual(result["status"], "interrupted" if corrupt else "committed")
                if corrupt:
                    self.assertEqual(campaign.state["current_checkpoint"], before)
                    self.assertEqual(result["checker_status"], "needs_attention")
                else:
                    self.assertNotEqual(campaign.state["current_checkpoint"], before)
                    self.assertTrue(Path(result["checker_report"]).is_file())
                self.assertIsNone(campaign.recover())

    def test_checked_worker_uses_four_goal_pitch_contract_and_evaluation_never_trains(self):
        for goal in ("one_log", "three_logs", "planks", "wooden_pickaxe"):
            with self.subTest(goal=goal), tempfile.TemporaryDirectory() as directory:
                campaign = self.campaign(Path(directory), goal=goal)
                args = argparse.Namespace(work_dir=Path(directory)/"work", build_dir=Path(directory)/"build",
                                          obs_control_dir=Path(directory)/"obs", video_export_dir=None)
                attempt = campaign.begin("eval_a", runtime_root=args.work_dir)
                command = worker_command(campaign, attempt, args, 240)
                self.assertIn("--pitch-actions", command)
                self.assertNotIn("--train", command)
                long_goal = goal in ("three_logs", "wooden_pickaxe")
                self.assertEqual(command[command.index("--trial-ticks") + 1], "1500" if long_goal else "400")
                self.assertEqual("--three-tree-fixture" in command, long_goal)
                self.assertEqual("--remember-mined-columns" in command, long_goal)

    def test_graph_changes_block_launch_and_seed_catalog_excludes_prior_ids(self):
        prior = seed_catalog(99)
        exclude = prior["pilot"][:3] + prior["eval_a"][:3]
        fresh = seed_catalog(99, exclude=exclude)
        self.assertFalse(set(exclude) & set(fresh["pilot"] + fresh["eval_a"]))
        with tempfile.TemporaryDirectory() as directory:
            campaign = self.campaign(Path(directory))
            Path(campaign.config["checker"]["graph"]["path"]).write_bytes(b"changed graph")
            with self.assertRaisesRegex(ValueError, "connectome integrity"):
                campaign.begin("eval_a")

    def test_resource_wait_requires_two_stable_samples_and_stop_is_responsive(self):
        for stop in (False, True):
            with self.subTest(stop=stop), tempfile.TemporaryDirectory() as directory:
                campaign = self.campaign(Path(directory)); now = [0]
                def sleep(seconds):
                    now[0] += seconds
                    if stop and now[0] >= 2:
                        (campaign.folder/"STOP").touch()
                healthy = supervisor.wait_resources(campaign, 100, sleep=sleep, clock=lambda: now[0],
                    memory=lambda: SimpleNamespace(available=3000*1024**2),
                    disk=lambda _: SimpleNamespace(free=10000*1024**2), temperature=lambda: 40)
                self.assertEqual(healthy, not stop)
                self.assertEqual(now[0], 2 if stop else 30)

    def test_retries_are_bounded_and_handoff_is_durable_without_automatic_fixes(self):
        with tempfile.TemporaryDirectory() as directory:
            campaign = self.campaign(Path(directory)); report = campaign.folder/"technical.json"
            atomic_json(report, {"stop_reason": "available_ram_guard"})
            item = {"status": "interrupted", "checker_status": "technical_stop", "checker_report": str(report)}
            for count, expected in ((1, "retry"), (2, "retry"), (3, "needs_attention")):
                campaign.state["attempts"] = [dict(item) for _ in range(count)]
                self.assertEqual(supervisor.classify(campaign, item), expected)
            request = supervisor.request_fix(campaign.folder, "missing acknowledgement", code="terminal_acknowledgment", attempt=item)
            self.assertFalse(request["automatic_code_changes"])
            self.assertEqual(load(campaign.folder/"fix_request.json")["reviewer"], "Codex")
            self.assertTrue((campaign.folder/"attention/request_0001.md").is_file())

    def test_obs_markers_are_preserved_and_foreign_recorder_is_untouched(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)/"obs"; (root/".sentinel").mkdir(parents=True)
            marker = root/".sentinel/run_35174127-4247-40e7-8ba9-85fd7cc432b3"; marker.touch()
            with mock.patch("tools.obs_session.obs_running", return_value=True):
                self.assertEqual(archive_stale_markers(root, Path(directory)/"archive"), [])
                self.assertTrue(marker.exists())
            with mock.patch("tools.obs_session.obs_running", return_value=False):
                moved = archive_stale_markers(root, Path(directory)/"archive")
                self.assertEqual(len(moved), 1)
                self.assertTrue(Path(moved[0]["archive"]).exists())


if __name__ == "__main__":
    unittest.main()
