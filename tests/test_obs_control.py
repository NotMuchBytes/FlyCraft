import io
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from tools.obs_control import ObsRecorder


class ObsControlTests(unittest.TestCase):
    def recorder(self, directory):
        folder = Path(directory)
        (folder / "obs-state.txt").write_text(f"initial\nstopped\n\n0\n0\n{int(time.time())}\n")
        return ObsRecorder(folder, "unit")

    def test_windows_sharing_violation_is_retried_before_command_commit(self):
        import os
        original = os.replace
        with tempfile.TemporaryDirectory() as directory:
            recorder = self.recorder(directory)
            calls = []
            def replace(source, destination):
                calls.append(destination)
                if len(calls) < 3:
                    raise PermissionError("reader still open")
                return original(source, destination)
            with mock.patch("tools.obs_control.os.replace", side_effect=replace):
                recorder.command("start")
            self.assertEqual(len(calls), 3)
            self.assertEqual(recorder.command_file.read_text().splitlines()[:2], ["unit", "start"])

    def test_stale_or_busy_recorder_cannot_open_a_trial(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            for status, timestamp in (("recording", int(time.time())), ("stopped", 1)):
                (folder / "obs-state.txt").write_text(f"other\n{status}\n\n854\n480\n{timestamp}\n")
                with self.assertRaises(RuntimeError):
                    ObsRecorder(folder, "unit")

    def test_recording_loss_is_not_silently_restarted(self):
        with tempfile.TemporaryDirectory() as directory:
            recorder = self.recorder(directory)
            recorder.started = True
            with self.assertRaisesRegex(RuntimeError, "confirmation was lost"):
                recorder.pulse()

    def test_failed_recording_stop_still_cleans_owned_processes(self):
        from tools import run_phase8_live as runner
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            arguments = ["run_phase8_live.py", "--run-id", "cleanup_test", "--work-dir", str(folder / "runtime"),
                         "--build-dir", str(folder / "build"), "--checkpoint", str(folder / "initial.npz"),
                         "--obs-control-dir", str(folder)]
            recorder = mock.Mock(started=True)
            recorder.pulse.side_effect = RuntimeError("OBS recording confirmation was lost")
            recorder.stop.side_effect = PermissionError("sharing violation during stop")
            with mock.patch.object(runner, "ROOT", folder), mock.patch("sys.argv", arguments), \
                 mock.patch.object(runner, "ObsRecorder", return_value=recorder), \
                 mock.patch.object(runner, "listening", return_value=False), \
                 mock.patch.object(runner.subprocess, "Popen"), \
                 mock.patch.object(runner.socket, "create_connection", side_effect=OSError("closed")), \
                 mock.patch.object(runner, "stop") as cleanup, mock.patch("sys.stdout", new=io.StringIO()):
                runner.main()
            self.assertEqual(cleanup.call_count, 2)
            import json
            metadata = json.loads((folder / "experiments/phase8/cleanup_test/run.json").read_text())
            self.assertEqual(metadata["stop_reason"], "recording_confirmation_lost")


if __name__ == "__main__":
    unittest.main()
