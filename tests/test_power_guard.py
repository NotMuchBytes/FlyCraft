import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest

from tools.power_guard import critical_battery, run


class PowerGuardTests(unittest.TestCase):
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
