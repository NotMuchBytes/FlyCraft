import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tools.power_guard import critical_battery, run, publish_status, request_stop


class PowerGuardTests(unittest.TestCase):
    def test_sharing_violation_retries_and_persistent_lock_retains_old_frame(self):
        with TemporaryDirectory() as directory:
            p=Path(directory)/"status.json";p.write_text('{"old":true}')
            ticks=[0.];calls=[]
            def replace(source,target):
                calls.append(1)
                if len(calls)<3:raise PermissionError("reader sharing lock")
                source.replace(target)
            def sleep(seconds):ticks[0]+=seconds
            self.assertTrue(publish_status(p,dict(active=True),replace=replace,sleep=sleep,clock=lambda:ticks[0]))
            self.assertEqual(len(calls),3)
            old=p.read_bytes()
            def locked(*args):raise PermissionError("persistent reader lock")
            self.assertFalse(publish_status(p,dict(active=False),replace=locked,sleep=sleep,clock=lambda:ticks[0]))
            self.assertEqual(p.read_bytes(),old)

    def test_failed_status_publication_does_not_release_native_protection(self):
        events=[]
        class Guard:
            def __init__(self,callback):pass
            def __enter__(self):events.append("acquired");return self
            def pump(self):events.append("pump")
            def __exit__(self,*args):events.append("released")
        with TemporaryDirectory() as directory:
            samples=iter([SimpleNamespace(percent=50,power_plugged=False),SimpleNamespace(percent=5,power_plugged=False)])
            with patch("tools.power_guard.publish_status",return_value=False):
                run(Path(directory),[Path(directory)/"STOP"],guard=Guard,battery=lambda:next(samples),sleep=lambda _:None)
            self.assertEqual(events,["acquired","pump","pump","released"])
            self.assertTrue((Path(directory)/"STOP").exists())

    def test_critical_stop_proof_never_marks_a_preexisting_manual_stop(self):
        with TemporaryDirectory() as directory:
            p=Path(directory)/"STOP";p.touch()
            request_stop([p],reason="critical_battery")
            self.assertFalse(p.with_name("STOP.reason.json").exists())

    def test_only_unplugged_critical_battery_releases(self):
        self.assertFalse(critical_battery(None))
        for percent, plugged, expected in [(5, False, True), (0, False, True),
                (6, False, False), (5, True, False), (100, False, False)]:
            self.assertEqual(critical_battery(SimpleNamespace(percent=percent, power_plugged=plugged)), expected)

    def test_critical_battery_requests_worker_stop_and_releases_guard(self):
        events = []

        class FakeGuard:
            def __init__(self, callback):
                pass

            def __enter__(self):
                events.append("acquired")
                return self

            def pump(self):
                pass

            def __exit__(self, *unused):
                events.append("released")

        with TemporaryDirectory() as directory:
            folder = Path(directory)
            stop = folder / "campaign" / "STOP"
            samples = iter([SimpleNamespace(percent=6, power_plugged=False),
                            SimpleNamespace(percent=5, power_plugged=False)])
            run(folder, [stop], battery=lambda: next(samples), guard=FakeGuard, sleep=lambda _: None)
            self.assertTrue(stop.exists())
            self.assertEqual(events, ["acquired", "released"])
            report = json.loads((folder / "status.json").read_text())
            self.assertEqual(report["status"], "released_critical_battery")
            self.assertFalse(report["blocks_normal_shutdown"])

    def test_manual_release_leaves_training_stop_untouched(self):
        class FakeGuard:
            def __init__(self, callback):
                pass

            def __enter__(self):
                return self

            def pump(self):
                pass

            def __exit__(self, *unused):
                pass

        with TemporaryDirectory() as directory:
            folder = Path(directory)
            (folder / "RELEASE").touch()
            stop = folder / "STOP"
            run(folder, [stop], battery=lambda: None, guard=FakeGuard)
            self.assertFalse(stop.exists())
            self.assertEqual(json.loads((folder / "status.json").read_text())["status"], "released")


if __name__ == "__main__":
    unittest.main()
