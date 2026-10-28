#!/usr/bin/env python3
"""Supervise bounded, disposable live Minecraft trials and preserve all evidence."""

import argparse
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import psutil

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from autonomy.minecraft import CONDITIONS, OBJECTIVES
from tools.obs_control import ObsRecorder


def listening(port):
    try:
        return any(connection.status == psutil.CONN_LISTEN and connection.laddr.port == port
                   for connection in psutil.net_connections(kind="tcp"))
    except psutil.Error:
        pass
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.2):
            return True
    except OSError:
        return False


def stop(process):
    if process is None or process.poll() is not None:
        return
    try:
        parent = psutil.Process(process.pid)
        children = parent.children(recursive=True)
        for child in reversed(children):
            try:
                child.terminate()
            except psutil.NoSuchProcess:
                pass
        process.terminate()
        _, remaining = psutil.wait_procs(children + [parent], timeout=4)
        for child in remaining:
            try:
                child.kill()
            except psutil.NoSuchProcess:
                pass
    except psutil.NoSuchProcess:
        pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--build-dir", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--frozen-checkpoint", type=Path)
    parser.add_argument("--goals", default="one_log")
    parser.add_argument("--conditions", default="trained")
    parser.add_argument("--trials", type=int, default=1)
    parser.add_argument("--world-seed", type=int, default=81001)
    parser.add_argument("--layout-start", type=int, default=81001)
    parser.add_argument("--seconds", type=int, default=180)
    parser.add_argument("--trial-ticks", type=int, default=600)
    parser.add_argument("--train", action="store_true")
    parser.add_argument("--recording-gate", action="store_true", help="Wait for runtime/start.enabled before starting trials")
    parser.add_argument("--obs-control-dir", type=Path, required=True, help="Directory shared with the OBS Lua recorder; new trials require recording")
    args = parser.parse_args()
    if any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for c in args.run_id):
        parser.error("run-id must be a simple identifier")
    goals, conditions = args.goals.split(","), args.conditions.split(",")
    if any(goal not in OBJECTIVES for goal in goals) or any(c not in CONDITIONS for c in conditions):
        parser.error("unknown goal or condition")
    if not 0 < args.trials <= 30 or not 0 < args.seconds <= 900 or args.trial_ticks <= 0:
        parser.error("use 1-30 trials and a bounded wall limit up to 900 seconds")
    if listening(25567) or listening(8765):
        parser.error("live test ports already occupied; no existing process will be stopped")
    recorder = ObsRecorder(args.obs_control_dir.resolve(), args.run_id)
    runtime = args.work_dir.resolve() / args.run_id
    results = ROOT / "experiments/phase8" / args.run_id
    if runtime.exists() or results.exists():
        parser.error("run paths must be new")
    server_dir, client_dir = runtime / "server", runtime / "client"
    server_dir.mkdir(parents=True); client_dir.mkdir(); results.mkdir(parents=True)
    control = runtime / "control.json"
    control.write_text(json.dumps({"episode_id": "initial", "goal": goals[0], "condition": conditions[0],
                                  "train": False, "active": False, "suite_complete": False}), encoding="utf-8")
    trials = runtime / "trials.csv"
    rows = [f"{condition},{goal},{args.layout_start + i},{str(args.train and condition == 'trained').lower()}"
            for i in range(args.trials) for goal in goals for condition in conditions]
    trials.write_text("\n".join(rows) + "\n", encoding="utf-8")
    def java_path(path):
        return str(path).replace("\\", "/")
    (server_dir / "flycraft-phase8.properties").write_text(
        f"controlFile={java_path(control)}\ntrialsFile={java_path(trials)}\nresultsFile={java_path(results / 'server.jsonl')}\nmaxTrialTicks={args.trial_ticks}\nmaxSeconds={args.seconds}\n", encoding="utf-8")
    (client_dir / "flycraft-phase8-client.properties").write_text(f"controlFile={java_path(control)}\n", encoding="utf-8")
    with (server_dir / "flycraft-phase8.properties").open("a", encoding="utf-8") as handle:
        handle.write(f"startGate={java_path(runtime / 'start.enabled')}\n")
    # Reuse the user's existing local-test EULA acceptance; never open a saved player world.
    (server_dir / "eula.txt").write_text("eula=true\n", encoding="utf-8")
    (server_dir / "server.properties").write_text(
        "server-ip=127.0.0.1\nserver-port=25567\nonline-mode=false\nenforce-secure-profile=false\n"
        f"level-name=world\nlevel-seed={args.world_seed}\nlevel-type=minecraft:flat\n"
        "gamemode=survival\nforce-gamemode=true\ndifficulty=peaceful\ngenerate-structures=false\n"
        "spawn-protection=0\nmax-players=1\nview-distance=2\nsimulation-distance=2\nallow-flight=false\n", encoding="utf-8")
    (client_dir / "options.txt").write_text("maxFps:30\nrenderDistance:2\nsimulationDistance:2\nparticles:2\nfullscreen:false\npauseOnLostFocus:false\nsoundCategory_master:0.0\n", encoding="utf-8")
    java = ROOT / ".runtime/jdk-25/bin/java.exe"
    gradle = [str(java), "-Xmx64m", "-classpath", "gradle/wrapper/gradle-wrapper.jar", "org.gradle.wrapper.GradleWrapperMain",
              "--offline", "--no-daemon", "--max-workers=2", "--console=plain", "-PflycraftBuildDir=" + java_path(args.build_dir.resolve())]
    environment = os.environ | {"JAVA_HOME": str(java.parents[1])}
    processes, handles, temperatures = [], [], []
    started, last_rows, stop_reason = time.perf_counter(), 0, "wall_budget"
    try:
        def launch(command, name, cwd):
            handle = (results / (name + "_launcher.log")).open("x", encoding="utf-8")
            handles.append(handle)
            process = subprocess.Popen(command, cwd=cwd, stdout=handle, stderr=subprocess.STDOUT,
                                       stdin=subprocess.PIPE, env=environment, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            processes.append(process)
            return process
        bridge_command = [sys.executable, str(ROOT / "minecraft_bridge.py"), "--phase8-checkpoint", str(args.checkpoint.resolve()),
                          "--phase8-results", str(results / "controller.jsonl"), "--log", str(results / "bridge.jsonl")]
        if args.frozen_checkpoint:
            bridge_command += ["--phase8-frozen-checkpoint", str(args.frozen_checkpoint.resolve())]
        if args.train:
            bridge_command += ["--phase8-save-dir", str(ROOT / "checkpoints/phase8" / args.run_id)]
        bridge = launch(bridge_command, "bridge", ROOT)
        server = launch(gradle + ["-PflycraftRunDir=" + java_path(server_dir), "runServer", "--args=nogui"], "server", ROOT / "minecraft_mod")
        client = None
        next_thermal = 0
        while time.perf_counter() - started < args.seconds:
            elapsed = time.perf_counter() - started
            if recorder.pulse() and not (runtime / "start.enabled").exists():
                (runtime / "start.enabled").write_text("OBS confirmed active\n", encoding="utf-8")
            if client is None and listening(25567) and listening(8765):
                client = launch(gradle + ["-PflycraftRunDir=" + java_path(client_dir), "-PflycraftAutotest", "-PflycraftServer=127.0.0.1:25567", "runClient"], "client", ROOT / "minecraft_mod")
            server_rows = (results / "server.jsonl").read_text(encoding="utf-8").splitlines() if (results / "server.jsonl").exists() else []
            if len(server_rows) != last_rows:
                last_rows = len(server_rows)
                print(json.dumps({"elapsed_seconds": round(elapsed, 1), "completed": last_rows, "requested": len(rows), "last": json.loads(server_rows[-1])}), flush=True)
            if control.exists() and json.loads(control.read_text()).get("suite_complete"):
                stop_reason = "suite_complete"; time.sleep(2); break
            if bridge.poll() is not None or server.poll() is not None or client is not None and client.poll() is not None:
                stop_reason = "process_exit"; break
            if elapsed >= next_thermal:
                next_thermal = elapsed + 5
                try:
                    thermal = subprocess.run(["nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=3)
                    value = int(thermal.stdout.splitlines()[0]); temperatures.append(value)
                    if value >= 75:
                        stop_reason = "gpu_temperature_guard"; break
                except (OSError, ValueError, IndexError, subprocess.TimeoutExpired):
                    pass
            time.sleep(1)
    except (RuntimeError, OSError) as error:
        stop_reason = "recording_control_error" if isinstance(error, OSError) else "recording_confirmation_lost" if "OBS" in str(error) else "supervisor_error"
        print(json.dumps({"error": str(error), "stop_reason": stop_reason}), flush=True)
    finally:
        recording = None
        try:
            recording = recorder.stop()
        except Exception as error:
            # Recording errors must never prevent cleanup of owned game/bridge
            # processes. The OBS heartbeat remains a second bounded fallback.
            print(json.dumps({"recording_stop_error": str(error)}), flush=True)
        try:
            with socket.create_connection(("127.0.0.1", 8765), timeout=2) as connection:
                connection.sendall(b'{"tick_id":9223372036854775807,"event":"end_suite"}\n')
                connection.recv(4096)
        except OSError:
            pass
        for process in reversed(processes):
            stop(process)
        for handle in handles:
            handle.close()
        import shutil
        for name, folder in (("server", server_dir), ("client", client_dir)):
            log = folder / "logs/latest.log"
            if log.exists():
                shutil.copy2(log, results / (name + ".log"))
        summary = {"run_id": args.run_id, "world_seed": args.world_seed, "layout_start": args.layout_start,
                   "goals": goals, "conditions": conditions, "trials_per_goal_condition": args.trials, "requested": len(rows),
                   "completed": last_rows, "stop_reason": stop_reason, "elapsed_seconds": time.perf_counter() - started,
                   "maximum_sampled_gpu_c": max(temperatures) if temperatures else None, "train": args.train}
        summary["recording"] = str(recording) if recording else None
        summary["recording_confirmed"] = recorder.started
        (results / "run.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
