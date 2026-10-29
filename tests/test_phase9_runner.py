import argparse
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from autonomy import AutonomousAgent
from autonomy.experiment import Campaign
from learning import NeuralFeatureTable
from tools import run_phase9 as runner

ROOT=Path(__file__).resolve().parents[1]


class RunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.table=NeuralFeatureTable.from_phase35(ROOT/"experiments/phase35/results/rate_decoder_evaluation.json")

    def campaign(self,folder):
        checkpoint=folder/"initial.npz"
        AutonomousAgent(self.table).save(checkpoint)
        return Campaign.create(folder/"campaign",project_root=folder,name="runner_unit",checkpoint=checkpoint,
                               worlds=2,table=self.table)

    def test_manual_stop_blocks_worker_launch_and_clear_preserves_request(self):
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory); campaign=self.campaign(folder)
            (campaign.folder/"STOP").touch()
            arguments=["run_phase9.py","run","--campaign",str(campaign.folder),"--work-dir",str(folder/"work"),
                       "--build-dir",str(folder/"build"),"--obs-control-dir",str(folder/"obs")]
            with mock.patch.object(runner,"Campaign",return_value=campaign),mock.patch("sys.argv",arguments), \
                 mock.patch.object(runner.subprocess,"Popen") as spawn:
                runner.main()
            spawn.assert_not_called()
            self.assertEqual(campaign.state["attempts"],[])
            arguments=["run_phase9.py","clear-stop","--campaign",str(campaign.folder)]
            with mock.patch.object(runner,"Campaign",return_value=campaign),mock.patch("sys.argv",arguments):
                runner.main()
            self.assertFalse((campaign.folder/"STOP").exists())
            self.assertEqual(len(list(campaign.folder.glob("STOP.ack.*"))),1)

    def test_eval_command_disables_learning_and_uses_same_affordances(self):
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory); campaign=self.campaign(folder)
            args=argparse.Namespace(work_dir=folder/"work",build_dir=folder/"build",obs_control_dir=folder/"obs",video_export_dir=None)
            train=campaign.begin(runtime_root=args.work_dir)
            train_command=runner.worker_command(campaign,train,args,240)
            campaign.recover()
            evaluation=campaign.begin("eval_a",condition="uniform",runtime_root=args.work_dir)
            eval_command=runner.worker_command(campaign,evaluation,args,240)
            self.assertIn("--train",train_command)
            self.assertNotIn("--train",eval_command)
            self.assertIn("--spectator",eval_command)
            for flag in ("--camera-mode","--trial-ticks","--capture-width","--server-heap-mib"):
                self.assertEqual(train_command[train_command.index(flag)+1],eval_command[eval_command.index(flag)+1])
            self.assertEqual(eval_command[eval_command.index("--conditions")+1],"uniform")

    def test_dashboard_uses_actual_logged_features_and_marks_requested_action(self):
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory); campaign=self.campaign(folder)
            results=folder/"results"; results.mkdir()
            response={"neural_features":{"left_readout_div50":.123},"action_probabilities":{"FORWARD":.75,"NO_OP":.25},
                      "action":"FORWARD","command_id":17,"feature_mode":"trained","peak_global_active":947,
                      "neural_steps":18,"cumulative_reward":1.25}
            (results/"bridge.jsonl").write_text(json.dumps({"timestamp_unix":123,"response":response})+"\n")
            data=runner.dashboard(campaign,"running",results)
            self.assertEqual(data["brain"]["features"],response["neural_features"])
            self.assertEqual(data["brain"]["probabilities"],response["action_probabilities"])
            page=(campaign.folder/"dashboard.html").read_text()
            self.assertIn("Requested action: FORWARD",page)
            self.assertIn("not neuron firing animations",page)
            self.assertEqual(data["summary"]["official_training_worlds"],0)


if __name__=="__main__":
    unittest.main()
