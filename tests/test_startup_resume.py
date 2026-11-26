"""Restart state-machine tests; no scheduled task or system shutdown is invoked."""
import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
OPS=ROOT/"experiments/phase9/autostart26_operations"
def module(name):
    spec=importlib.util.spec_from_file_location("startup_"+name,OPS/(name+".py"));result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result
supervisor=module("supervise")
recovery=module("recover")
bootstrap=module("bootstrap")


class StartupTests(unittest.TestCase):
    def test_critical_battery_does_not_restart_power_guard_or_worker(self):
        with TemporaryDirectory() as directory:
            p=Path(directory);plan=p/"plan.json"
            plan.write_text(json.dumps(dict(state_dir=str(p),root=str(p),campaign=str(p/"campaign"))))
            with patch.object(supervisor.psutil,"sensors_battery",return_value=SimpleNamespace(percent=5,power_plugged=False)),patch.object(supervisor,"ensure_companion") as launch:
                self.assertEqual(supervisor.run(plan,once=True),0);launch.assert_not_called()
            self.assertEqual(json.loads((p/"status.json").read_text())["status"],"critical_battery")
    def test_bootstrap_restarts_a_crashed_supervisor_with_backoff(self):
        with TemporaryDirectory() as directory:
            p=Path(directory);plan=p/"plan.json";plan.write_text(json.dumps(dict(state_dir=str(p),root=str(p),python="python")))
            first=SimpleNamespace(wait=lambda:1);second=SimpleNamespace(wait=lambda:0);waits=[]
            with patch.object(bootstrap.subprocess,"Popen",side_effect=[first,second]) as calls:
                self.assertEqual(bootstrap.run(plan,sleep=waits.append),0)
            self.assertEqual(calls.call_count,2);self.assertEqual(waits,[15])
            self.assertEqual(len(list(p.glob("bootstrap_*.log"))),2)

    def test_disabling_autostart_prevents_bootstrap_launch(self):
        with TemporaryDirectory() as directory:
            p=Path(directory);plan=p/"plan.json";plan.write_text(json.dumps(dict(state_dir=str(p),root=str(p),python="python")))
            (p/"DISABLE_AUTOSTART").touch()
            with patch.object(bootstrap.subprocess,"Popen") as launch:
                self.assertEqual(bootstrap.run(plan),0);launch.assert_not_called()
    def test_duplicate_supervisors_cannot_own_the_same_lease(self):
        with TemporaryDirectory() as directory:
            with supervisor.Lease(Path(directory)/"lease"):
                with self.assertRaises(RuntimeError):
                    with supervisor.Lease(Path(directory)/"lease"):pass
            with supervisor.Lease(Path(directory)/"lease"):pass

    def test_stop_gate_failure_and_missing_skill_are_never_bypassed(self):
        with TemporaryDirectory() as directory:
            p=Path(directory)
            for status in ("stage_gate_failed","awaiting_next_skill_implementation","curriculum_complete","ready"):
                (p/"state.json").write_text(json.dumps(dict(status=status)))
                self.assertEqual(supervisor.decision(p),"resume" if status=="ready" else status)
            (p/"STOP").touch();self.assertEqual(supervisor.decision(p),"paused_by_stop")
            (p/"STOP").unlink();(p/"fix_request.json").write_text('{}')
            self.assertEqual(supervisor.decision(p),"needs_review")

    def test_pid_reuse_cannot_adopt_an_unrelated_process(self):
        fake=SimpleNamespace(create_time=lambda:123.,cmdline=lambda:["unrelated.py"])
        with patch.object(supervisor.psutil,"Process",return_value=fake):
            self.assertFalse(supervisor.alive(dict(pid=1,process_created=122.),"unrelated.py"))
            self.assertFalse(supervisor.alive(dict(pid=1,process_created=123.),"run_staged_curriculum.py"))

    def test_only_unchanged_critical_battery_stop_can_be_cleared(self):
        with TemporaryDirectory() as directory:
            p=Path(directory);stop=p/"STOP";stop.touch()
            proof=dict(reason="critical_battery",stop_mtime_ns=stop.stat().st_mtime_ns)
            (p/"STOP.reason.json").write_text(json.dumps(proof))
            self.assertFalse(supervisor.clear_critical_stop(p,SimpleNamespace(power_plugged=False,percent=90)))
            proof['stop_mtime_ns']-=1;(p/"STOP.reason.json").write_text(json.dumps(proof))
            self.assertFalse(supervisor.clear_critical_stop(p,SimpleNamespace(power_plugged=True,percent=90)))
            proof['stop_mtime_ns']=stop.stat().st_mtime_ns;(p/"STOP.reason.json").write_text(json.dumps(proof))
            self.assertTrue(supervisor.clear_critical_stop(p,SimpleNamespace(power_plugged=True,percent=90)))

    def test_recovery_never_retries_scored_partial_or_recorded_attempts(self):
        with TemporaryDirectory() as directory:
            p=Path(directory)
            self.assertTrue(recovery.unscored_technical({},p))
            self.assertFalse(recovery.unscored_technical(dict(video_required=True),p))
            for content in ('{"success":true}\n','{"success":'):
                (p/"server.jsonl").write_text(content)
                self.assertFalse(recovery.unscored_technical({},p))
            (p/"server.jsonl").write_text('')
            (p/"run.json").write_text(json.dumps(dict(completed=0,stop_reason="coordinator_lost")))
            self.assertTrue(recovery.unscored_technical({},p))
            (p/"run.json").write_text(json.dumps(dict(completed=0,stop_reason="manual_stop")))
            self.assertFalse(recovery.unscored_technical({},p))

    def test_lightweight_source_hash_matches_frozen_manifest_algorithm(self):
        from autonomy.experiment import source_manifest
        self.assertEqual(supervisor.source_hash(ROOT),source_manifest(ROOT)['implementation_sha256'])
