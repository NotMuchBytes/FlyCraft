"""Transactional tests use temporary, explicitly synthetic worker evidence.

These fixtures test bookkeeping, not Minecraft gameplay or recording quality.
Real video decode/content validation has separate tests and live run evidence.
"""

import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from autonomy import AutonomousAgent
from autonomy.experiment import Campaign, CampaignLock, atomic_json, digest, seed_catalog
from learning import NeuralFeatureTable

ROOT=Path(__file__).resolve().parents[1]


class ExperimentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.table=NeuralFeatureTable.from_phase35(ROOT/"experiments/phase35/results/rate_decoder_evaluation.json")

    def campaign(self, folder, *, worlds=3):
        initial=folder/"initial.npz"
        AutonomousAgent(self.table).save(initial)
        return Campaign.create(folder/"campaign",project_root=folder,name="unit_only",checkpoint=initial,
                               worlds=worlds,table=self.table)

    def evidence(self, campaign, attempt, *, success=True, train=None, delta=0):
        results=campaign.root/"experiments/phase9"/attempt["run_id"]
        results.mkdir(parents=True)
        trained=attempt["train"] if train is None else train
        score={"episode_id":"trial_0000","success":success,"ticks":80,"train":trained,
               "layout_seed":attempt["layout_seed"],"inventory":{"log":int(success)}}
        outcome={"episode_id":"trial_0000","success":success,"done":True,"train":trained,
                 "actions":2,"total_reward":8.2 if success else -2,"termination":"success" if success else "episode_boundary",
                 "terminal_inventory":{"log":int(success)},"update":{"weight_delta_norm":delta}}
        if trained:
            agent,_=AutonomousAgent.load(Path(attempt["checkpoint"]["path"]),self.table)
            agent.session=outcome.copy()
            agent.policy.weights.flat[0]+=delta
            checkpoint=campaign.root/"checkpoints/phase9"/attempt["run_id"]/"trial_0000.npz"
            agent.save(checkpoint)
        # Synthetic metadata stand-ins, temporary and never offered as footage.
        fixture=results/"unit_only_not_minecraft.fixture"
        fixture.write_bytes(b"UNIT TEST ARTIFACT - NOT VIDEO OR MINECRAFT FOOTAGE")
        video={"path":str(fixture),"sha256":digest(fixture),"episode_coverage_complete":True,
               "visual_content_preflight_verified":True}
        run={"stop_reason":"suite_complete","completed":1,"generated_world_instances":1,
             "server_exited_cleanly":True,"client_exited_cleanly":True,"train":trained,
             "checkpoint_sha256":attempt["checkpoint"]["sha256"],"world_seed":attempt["world_seed"],
             "implementation_sha256":campaign.config["implementation_sha256"],
             "milestone_video_status":"verified","milestone_video":video,"elapsed_seconds":90}
        atomic_json(results/"run.json",run)
        for name,row in (("server.jsonl",score),("controller.jsonl",outcome),
                         ("server.jsonl.delivery.jsonl",{"acknowledged":True})):
            (results/name).write_text(json.dumps(row)+"\n")
        return results

    def test_seed_partitions_reproduce_and_do_not_overlap(self):
        a=seed_catalog(17)
        self.assertEqual(a,seed_catalog(17))
        values=[seed for split in ("pilot","training","eval_a","eval_b") for seed in a[split]]
        self.assertEqual(len(values),len(set(values)))
        self.assertEqual(len(a["eval_a"]),100)
        self.assertEqual(len(a["eval_b"]),100)
        self.assertFalse(set(values)&{44556777,44556778,44556779})
        self.assertTrue(all(0<=value<2**63 for value in values))

    def test_commit_is_atomic_idempotent_and_restores_checkpoint_chain(self):
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory); campaign=self.campaign(folder)
            first=campaign.begin(runtime_root=folder/"runtime")
            self.evidence(campaign,first,delta=.1)
            resumed=Campaign(campaign.folder,project_root=folder,table=self.table)
            result=resumed.recover()
            self.assertEqual(result["status"],"committed")
            self.assertIsNone(resumed.recover())
            self.assertEqual(resumed.summary()["training_updates"],1)
            second=resumed.begin()
            self.assertEqual(second["episode_number"],2)
            self.assertEqual(second["checkpoint"],result["checkpoint_after"])
            self.assertNotEqual(second["world_seed"],first["world_seed"])

    def test_crash_keeps_previous_checkpoint_and_counts_reused_seed_instances(self):
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory); campaign=self.campaign(folder)
            first=campaign.begin(runtime_root=folder/"runtime")
            world=Path(first["runtime"])/"server/world"
            world.mkdir(parents=True); (world/"level.dat").write_bytes(b"unit-world-marker")
            before=dict(campaign.state["current_checkpoint"])
            result=campaign.recover()
            self.assertEqual(result["status"],"interrupted")
            self.assertEqual(campaign.state["current_checkpoint"],before)
            retry=campaign.begin(runtime_root=folder/"runtime")
            self.assertEqual(retry["episode_number"],1)
            self.assertEqual(retry["world_seed"],first["world_seed"])
            self.assertNotEqual(retry["run_id"],first["run_id"])
            self.evidence(campaign,retry)
            self.assertEqual(campaign.recover()["status"],"committed")
            summary=campaign.summary()
            self.assertEqual(summary["generated_world_instances"],2)
            self.assertEqual(summary["distinct_generated_seeds"],1)
            self.assertEqual(summary["training_episodes"],1)

    def test_missing_video_cannot_advance_checkpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory); campaign=self.campaign(folder)
            attempt=campaign.begin()
            results=self.evidence(campaign,attempt,delta=.1)
            before=dict(campaign.state["current_checkpoint"])
            run=json.loads((results/"run.json").read_text()); run["milestone_video_status"]="missing"
            atomic_json(results/"run.json",run)
            self.assertEqual(campaign.recover()["status"],"interrupted")
            self.assertEqual(campaign.state["current_checkpoint"],before)
            self.assertEqual(campaign.summary()["training_episodes"],0)

    def test_eval_cannot_train_and_final_requires_frozen_selection(self):
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory); campaign=self.campaign(folder)
            with self.assertRaisesRegex(ValueError,"freeze"):
                campaign.begin("eval_b")
            attempt=campaign.begin("eval_a")
            self.assertFalse(attempt["train"])
            self.assertNotIn(attempt["world_seed"],campaign.catalog["pilot"])
            self.evidence(campaign,attempt,train=True)
            self.assertEqual(campaign.recover()["status"],"interrupted")
            campaign.freeze_final()
            with self.assertRaisesRegex(ValueError,"frozen"):
                campaign.begin()
            final=campaign.begin("eval_b")
            self.evidence(campaign,final,train=False)
            self.assertEqual(campaign.recover()["status"],"committed")
            self.assertEqual(campaign.summary()["evaluation_episodes"],1)
            self.assertEqual(campaign.summary()["training_episodes"],0)

    def test_integrity_mutations_and_parallel_coordinators_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory); campaign=self.campaign(folder)
            with CampaignLock(campaign.folder):
                with self.assertRaises(RuntimeError):
                    with CampaignLock(campaign.folder):
                        self.fail("two coordinators acquired the same lease")
            with CampaignLock(campaign.folder):
                pass
            seeds=json.loads((campaign.folder/"seeds.json").read_text()); seeds["pilot"][0]+=1
            atomic_json(campaign.folder/"seeds.json",seeds)
            with self.assertRaisesRegex(ValueError,"catalog integrity"):
                Campaign(campaign.folder,project_root=folder,table=self.table)

    def test_implementation_change_requires_new_campaign(self):
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory); campaign=self.campaign(folder)
            (folder/"minecraft_bridge.py").write_text("# changed test implementation\n")
            with self.assertRaisesRegex(ValueError,"implementation changed"):
                campaign.begin()

    def test_atomic_status_retries_transient_windows_reader_lock(self):
        from autonomy import experiment
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"status.json"
            atomic_json(path,{"revision":1})
            real_replace=experiment.os.replace
            seen=[]
            def sharing_race(source,destination):
                seen.append(json.loads(path.read_text())["revision"])
                if len(seen)<3:
                    raise PermissionError("simulated Windows reader sharing lock")
                real_replace(source,destination)
            with mock.patch.object(experiment.os,"replace",side_effect=sharing_race):
                atomic_json(path,{"revision":2})
            self.assertEqual(seen,[1,1,1])
            self.assertEqual(json.loads(path.read_text())["revision"],2)

    def test_failed_atomic_replacement_keeps_old_committed_state(self):
        from autonomy import experiment
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"state.json"
            atomic_json(path,{"committed":1})
            with mock.patch.object(experiment.os,"replace",side_effect=PermissionError("persistent lock")), \
                 mock.patch.object(experiment.time,"monotonic",side_effect=[0,2]):
                with self.assertRaises(PermissionError):
                    atomic_json(path,{"committed":2})
            self.assertEqual(json.loads(path.read_text())["committed"],1)
            self.assertTrue(path.with_name("state.json.tmp").is_file())


if __name__=="__main__":
    unittest.main()
