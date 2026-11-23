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
        (folder / "obs-state.txt").write_text(f"initial\nstopped\n\n0\n0\n{int(time.time())}\n\nEND\n")
        return ObsRecorder(folder, "unit")

    def test_windows_sharing_violation_is_retried_before_command_commit(self):
        original = Path.write_text
        with tempfile.TemporaryDirectory() as directory:
            recorder = self.recorder(directory)
            calls = []
            def write(path, payload, **kwargs):
                calls.append(path)
                if len(calls) < 3:
                    raise PermissionError("reader still open")
                return original(path, payload, **kwargs)
            with mock.patch.object(Path, "write_text", new=write):
                recorder.command("start")
            self.assertEqual(len(calls), 3)
            self.assertEqual(recorder.command_file.read_text().splitlines()[:2], ["unit", "start"])

    def test_stale_or_busy_recorder_cannot_open_a_trial(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            for status, timestamp in (("recording", int(time.time())), ("stopped", 1)):
                (folder / "obs-state.txt").write_text(f"other\n{status}\n\n854\n480\n{timestamp}\n\nEND\n")
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
            (folder / "initial.npz").write_bytes(b"test checkpoint placeholder; no model is loaded by mocked subprocesses")
            arguments = ["run_phase8_live.py", "--run-id", "cleanup_test", "--work-dir", str(folder / "runtime"),
                         "--build-dir", str(folder / "build"), "--checkpoint", str(folder / "initial.npz"),
                         "--obs-control-dir", str(folder), "--launcher", "gradle"]
            recorder = mock.Mock(started=True)
            recorder.pulse.side_effect = RuntimeError("OBS recording confirmation was lost")
            recorder.stop.side_effect = PermissionError("sharing violation during stop")
            with mock.patch.object(runner, "ROOT", folder), mock.patch("sys.argv", arguments), \
                 mock.patch.object(runner, "ObsRecorder", return_value=recorder), \
                 mock.patch.object(runner, "listening", return_value=False), \
                 mock.patch.object(runner.psutil, "virtual_memory", return_value=mock.Mock(available=4096*1024**2)), \
                 mock.patch.object(runner.shutil, "disk_usage", return_value=mock.Mock(free=4096*1024**2)), \
                 mock.patch.object(runner.subprocess, "Popen") as process_factory, \
                 mock.patch.object(runner.socket, "create_connection", side_effect=OSError("closed")), \
                 mock.patch.object(runner, "stop") as cleanup, mock.patch("sys.stdout", new=io.StringIO()):
                process_factory.return_value.poll.return_value=None
                runner.main()
            self.assertEqual(cleanup.call_count, 2)
            import json
            metadata = json.loads((folder / "experiments/phase8/cleanup_test/run.json").read_text())
            self.assertEqual(metadata["stop_reason"], "recording_confirmation_lost")

    def test_cleanup_tolerates_native_crash_and_leaves_windows_reporter_alone(self):
        import psutil
        from tools import run_phase8_live as runner
        process=mock.Mock(pid=101)
        process.poll.return_value=None
        process.terminate.side_effect=PermissionError("already exiting")
        parent,child,reporter=mock.Mock(),mock.Mock(),mock.Mock()
        parent.children.return_value=[child,reporter]
        child.name.return_value="java.exe"
        child.terminate.side_effect=psutil.AccessDenied(102)
        child.kill.side_effect=psutil.AccessDenied(102)
        reporter.name.return_value="WerFault.exe"
        with mock.patch.object(runner.psutil,"Process",return_value=parent), \
             mock.patch.object(runner.psutil,"wait_procs",return_value=([],[child,parent])) as wait:
            runner.stop(process)
        reporter.terminate.assert_not_called(); reporter.kill.assert_not_called()
        self.assertNotIn(reporter,wait.call_args.args[0])

    def test_nvidia_gate_checks_actual_device_and_rejects_opengl_fallback(self):
        from tools.run_phase8_live import graphics_readiness
        preference = "Preferring discrete GPU: NVIDIA GeForce RTX 4050 Laptop GPU\n"
        vulkan = "Using graphics backend Vulkan, using drivers: NVIDIA\n"
        self.assertEqual(graphics_readiness(preference, "vulkan"), (False, None))
        self.assertEqual(graphics_readiness(preference+vulkan+"Using graphics device: AMD Radeon 740M", "vulkan"),
                         (False, "requested_nvidia_device_not_selected"))
        self.assertEqual(graphics_readiness(preference+"Using graphics backend OpenGL", "vulkan"),
                         (False, "vulkan_unavailable_opengl_fallback_rejected"))
        self.assertEqual(graphics_readiness(vulkan+"Using graphics device: NVIDIA GeForce RTX 4050 Laptop GPU (NVIDIA)", "vulkan"),
                         (True, None))
        self.assertEqual(graphics_readiness("Using graphics backend OpenGL\nUsing graphics device: NVIDIA Corporation RTX 4050", "opengl"),
                         (True, None))
        self.assertEqual(graphics_readiness("Using graphics backend OpenGL\nUsing graphics device: AMD Radeon 740M", "opengl"),
                         (False, "requested_nvidia_device_not_selected"))

    def test_low_ram_aborts_and_cleans_owned_processes(self):
        from tools import run_phase8_live as runner
        import json
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory)
            (folder/"initial.npz").write_bytes(b"mocked model")
            for run_id, samples, launched, minimum in (
                ("ram_preflight", (128,), 0, None),
                ("ram_live", (1024, 128, 128, 128), 2, 128),
            ):
                with self.subTest(run_id=run_id):
                    args=["run_phase8_live.py", "--run-id", run_id, "--work-dir", str(folder/"runtime"),
                          "--build-dir", str(folder/"build"), "--checkpoint", str(folder/"initial.npz"),
                          "--obs-control-dir", str(folder), "--launcher", "gradle"]
                    recorder=mock.Mock(started=False)
                    recorder.pulse.return_value=False
                    recorder.stop.return_value=None
                    memory_samples = [mock.Mock(available=mib*1024**2) for mib in samples]
                    with mock.patch.object(runner,"ROOT",folder),mock.patch("sys.argv",args), \
                         mock.patch.object(runner,"ObsRecorder",return_value=recorder), \
                         mock.patch.object(runner,"listening",return_value=False), \
                         mock.patch.object(runner.shutil,"disk_usage",return_value=mock.Mock(free=4096*1024**2)), \
                         mock.patch.object(runner.psutil,"virtual_memory",side_effect=memory_samples), \
                         mock.patch.object(runner.subprocess,"Popen") as factory, \
                         mock.patch.object(runner.subprocess,"run",return_value=mock.Mock(stdout="45\n")), \
                         mock.patch.object(runner.time,"sleep"), \
                         mock.patch.object(runner.socket,"create_connection",side_effect=OSError("closed")), \
                         mock.patch.object(runner,"stop") as cleanup,mock.patch("sys.stdout",new=io.StringIO()):
                        factory.return_value.poll.return_value=None
                        runner.main()
                    self.assertEqual(factory.call_count,launched)
                    self.assertEqual(cleanup.call_count,launched)
                    metadata=json.loads((folder/"experiments/phase8"/run_id/"run.json").read_text())
                    self.assertEqual(metadata["stop_reason"],"available_ram_guard")
                    self.assertEqual(metadata["minimum_sampled_available_ram_mib"],minimum)
                    self.assertFalse((folder/"runtime"/run_id/"start.enabled").exists())


if __name__ == "__main__":
    unittest.main()
