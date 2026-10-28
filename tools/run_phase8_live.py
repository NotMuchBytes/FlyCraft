#!/usr/bin/env python3
"""Supervise bounded, disposable live Minecraft trials and preserve all evidence."""

import argparse
import hashlib
import math
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
from tools.java_launch import command_from_export
from tools.milestone_video import MILESTONES, require_video_tools, preserve_milestone, compare_capture_frames


class EventLogRecording:
    """A headless server produces event evidence, never an implicit video."""
    started=False
    def pulse(self):
        return True
    def stop(self):
        return None


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


def graphics_readiness(log, backend):
    """Verify the selected renderer, rather than a preferred-device message."""
    lines = log.lower().splitlines()
    backends = [line for line in lines if "using graphics backend " in line]
    devices = [line.split("using graphics device:", 1)[1].strip()
               for line in lines if "using graphics device:" in line]
    if backend == "vulkan" and backends and "using graphics backend opengl" in backends[-1]:
        return False, "vulkan_unavailable_opengl_fallback_rejected"
    if backend == "opengl" and backends and "using graphics backend opengl" not in backends[-1]:
        return False, "requested_opengl_backend_not_selected"
    if devices and not devices[-1].startswith("nvidia "):
        return False, "requested_nvidia_device_not_selected"
    return bool(backends and devices), None


def stop(process):
    if process is None or process.poll() is not None:
        return
    try:
        parent = psutil.Process(process.pid)
        children = []
        for child in parent.children(recursive=True):
            try:
                if child.name().lower() not in {"werfault.exe","werfaultsecure.exe","wermgr.exe"}:
                    children.append(child)
            except (psutil.NoSuchProcess,psutil.AccessDenied):
                pass
        for child in reversed(children):
            try:
                child.terminate()
            except (psutil.NoSuchProcess,psutil.AccessDenied):
                pass
        try:
            process.terminate()
        except (OSError,psutil.AccessDenied):
            pass
        _, remaining = psutil.wait_procs(children + [parent], timeout=4)
        for child in remaining:
            try:
                child.kill()
            except (psutil.NoSuchProcess,psutil.AccessDenied):
                pass
    except (psutil.NoSuchProcess,psutil.AccessDenied):
        pass


def owned_rss_mib(process):
    if not isinstance(process.pid,int):
        return None
    try:
        parent=psutil.Process(process.pid)
        processes=[parent,*parent.children(recursive=True)]
        return sum(child.memory_info().rss for child in processes)/1024**2
    except (psutil.NoSuchProcess,psutil.AccessDenied):
        return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--build-dir", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--frozen-checkpoint", type=Path)
    parser.add_argument("--policy-label", default="six_live_log_episodes")
    parser.add_argument("--frozen-label", default="phase7_frozen_transfer")
    parser.add_argument("--goals", default="one_log")
    parser.add_argument("--conditions", default="trained")
    parser.add_argument("--trials", type=int, default=1)
    parser.add_argument("--world-seed", type=int, default=81001)
    parser.add_argument("--layout-start", type=int, default=81001)
    parser.add_argument("--seconds", type=int, default=180)
    parser.add_argument("--trial-ticks", type=int, default=600)
    parser.add_argument("--train", action="store_true")
    parser.add_argument("--camera-mode", choices=("legacy","instant","bounded"), default="bounded")
    parser.add_argument("--turn-degrees", type=float, default=15)
    parser.add_argument("--camera-probe", action="store_true", help="Scripted motor tests, never autonomous goal evidence")
    parser.add_argument("--graphics-backend", choices=("default","opengl","vulkan"),default="opengl")
    parser.add_argument("--minimum-available-ram-mib", type=int, default=768)
    parser.add_argument("--launcher", choices=("direct", "gradle"), default="direct")
    parser.add_argument("--headless", action="store_true", help="Server-only adapter; structured event logs, no MP4")
    parser.add_argument("--spectator", action="store_true", help="Record a headless agent with an isolated spectator client")
    parser.add_argument("--spectator-view", choices=("third_person","first_person"), default="third_person")
    parser.add_argument("--capture-width", type=int, default=1920)
    parser.add_argument("--capture-height", type=int, default=1080)
    parser.add_argument("--milestone", type=int, choices=MILESTONES)
    parser.add_argument("--redo-of", help="Prior development run retained separately; this is a new execution, not a replay")
    parser.add_argument("--video-export-dir", type=Path)
    parser.add_argument("--server-heap-mib", type=int, default=768)
    parser.add_argument("--client-heap-mib", type=int, default=1024)
    parser.add_argument("--recording-gate", action="store_true", help="Wait for runtime/start.enabled before starting trials")
    parser.add_argument("--obs-control-dir", type=Path, help="Directory shared with OBS; graphical trials require recording")
    args = parser.parse_args()
    graphical = not args.headless or args.spectator
    if any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for c in args.run_id):
        parser.error("run-id must be a simple identifier")
    goals, conditions = args.goals.split(","), args.conditions.split(",")
    if any(goal not in OBJECTIVES for goal in goals) or any(c not in CONDITIONS for c in conditions):
        parser.error("unknown goal or condition")
    if not 0 < args.trials <= 30 or not 0 < args.seconds <= 900 or args.trial_ticks <= 0:
        parser.error("use 1-30 trials and a bounded wall limit up to 900 seconds")
    if args.minimum_available_ram_mib < 256:
        parser.error("the RAM reserve must be at least 256 MiB")
    if not 512<=args.server_heap_mib<=2048 or not 768<=args.client_heap_mib<=2048:
        parser.error("use bounded server/client heaps")
    if graphical and args.obs_control_dir is None:
        parser.error("graphical trials require --obs-control-dir")
    if args.spectator and not args.headless:
        parser.error("--spectator requires --headless")
    if args.milestone is not None:
        if not args.spectator or args.trials!=1 or len(goals)!=1 or len(conditions)!=1:
            parser.error("a milestone requires one episode and an isolated recorded spectator")
        require_video_tools()
    if not 854<=args.capture_width<=1920 or not 480<=args.capture_height<=1080:
        parser.error("capture dimensions must remain within 854x480 and 1920x1080")
    if args.headless and (args.launcher!="direct" or args.camera_mode=="legacy" or args.camera_probe
                         or any(goal not in {"one_log","planks"} for goal in goals)):
        parser.error("headless pilot supports direct launch, strict camera, and one_log/planks only")
    if not args.checkpoint.is_file() or args.frozen_checkpoint and not args.frozen_checkpoint.is_file():
        parser.error("checkpoint files must exist")
    if not math.isfinite(args.turn_degrees) or not 0<args.turn_degrees<=45:
        parser.error("turn-degrees must be finite and in (0,45]")
    if args.camera_probe and (args.camera_mode=="legacy" or goals!=["camera_probe"] or args.trials!=1):
        parser.error("camera-probe requires one camera_probe trial in instant or bounded mode")
    if listening(25567) or listening(8765):
        parser.error("live test ports already occupied; no existing process will be stopped")
    recorder = EventLogRecording() if not graphical else ObsRecorder(args.obs_control_dir.resolve(), args.run_id)
    runtime = args.work_dir.resolve() / args.run_id
    phase="phase9" if args.headless else "phase8"
    results = ROOT / "experiments" / phase / args.run_id
    if runtime.exists() or results.exists():
        parser.error("run paths must be new")
    server_dir, client_dir = runtime / "server", runtime / "client"
    server_dir.mkdir(parents=True); client_dir.mkdir(); results.mkdir(parents=True)
    source_paths=[ROOT/"minecraft_bridge.py",ROOT/"minecraft_mod/build.gradle",ROOT/"tools/run_phase8_live.py",ROOT/"tools/java_launch.py"]
    for source_folder in ("autonomy","learning","simulator","interface","minecraft_mod/src"):
        source_paths.extend(path for path in (ROOT/source_folder).rglob("*") if path.is_file() and path.suffix in {".py",".java",".json",".png"})
    source_hashes={str(path.relative_to(ROOT)).replace("\\","/"):hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(set(source_paths)) if path.is_file()}
    implementation_sha256=hashlib.sha256(json.dumps(source_hashes,sort_keys=True).encode()).hexdigest()
    (results/"source_manifest.json").write_text(json.dumps({"implementation_sha256":implementation_sha256,"files":source_hashes},indent=2),encoding="utf-8",newline="\n")
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
    capture_title="FlyCraft Recording "+args.run_id
    (client_dir / "flycraft-phase8-client.properties").write_text(f"controlFile={java_path(control)}\ncapture.windowTitle={capture_title}\n", encoding="utf-8")
    camera_trace=results / "camera.jsonl"
    camera_probe=results / "camera_probe.jsonl"
    with (client_dir / "flycraft-phase8-client.properties").open("a",encoding="utf-8") as handle:
        handle.write(f"camera.mode={args.camera_mode}\ncamera.turnDegrees={args.turn_degrees}\n")
        if args.camera_mode!="legacy": handle.write(f"camera.traceFile={java_path(camera_trace)}\n")
        if args.camera_probe: handle.write(f"camera.probe=true\ncamera.probeFile={java_path(camera_probe)}\n")
    if args.camera_probe:
        with (server_dir / "flycraft-phase8.properties").open("a",encoding="utf-8") as handle:
            handle.write(f"cameraProbeResult={java_path(Path(str(camera_probe)+'.complete.json'))}\n")
    if args.headless:
        (server_dir/"flycraft-headless.properties").write_text(
            f"controlFile={java_path(control)}\ntraceFile={java_path(results/'headless.jsonl')}\n"
            f"camera.mode={args.camera_mode}\ncamera.traceFile={java_path(camera_trace)}\n",encoding="utf-8")
    if args.spectator:
        (client_dir/"flycraft-spectator.properties").write_text(
            f"controlFile={java_path(control)}\nreadyFile={java_path(runtime/'spectator.ready')}\nview={args.spectator_view}\n"
            f"windowTitle={capture_title}\nframeFile={java_path(runtime/'spectator-frame.png')}\n",
            encoding="utf-8")
    with (server_dir / "flycraft-phase8.properties").open("a", encoding="utf-8") as handle:
        handle.write(f"startGate={java_path(runtime / 'start.enabled')}\n")
    # Reuse the user's existing local-test EULA acceptance; never open a saved player world.
    (server_dir / "eula.txt").write_text("eula=true\n", encoding="utf-8")
    (server_dir / "server.properties").write_text(
        "server-ip=127.0.0.1\nserver-port=25567\nonline-mode=false\nenforce-secure-profile=false\n"
        f"level-name=world\nlevel-seed={args.world_seed}\nlevel-type=minecraft:flat\n"
        "gamemode=survival\nforce-gamemode=true\ndifficulty=peaceful\ngenerate-structures=false\n"
        f"spawn-protection=0\nmax-players={2 if args.spectator else 1}\nview-distance=2\nsimulation-distance=2\nallow-flight=false\n", encoding="utf-8")
    (client_dir / "options.txt").write_text("maxFps:30\nrenderDistance:2\nsimulationDistance:5\nparticles:2\nfullscreen:false\npauseOnLostFocus:false\nsoundCategory_master:0.0\n", encoding="utf-8")
    java = ROOT / ".runtime/jdk-25/bin/java.exe"
    gradle = [str(java), "-Xmx64m", "-classpath", "gradle/wrapper/gradle-wrapper.jar", "org.gradle.wrapper.GradleWrapperMain",
              "--offline", "--no-daemon", "--max-workers=2", "--console=plain", "-Dorg.gradle.jvmargs=-Xmx512m",
              "-PflycraftBuildDir=" + java_path(args.build_dir.resolve()),
              "-PflycraftServerHeapMiB="+str(args.server_heap_mib),"-PflycraftClientHeapMiB="+str(args.client_heap_mib),
              "-PflycraftCaptureWidth="+str(args.capture_width),"-PflycraftCaptureHeight="+str(args.capture_height)]
    environment = os.environ | {"JAVA_HOME": str(java.parents[1])}
    processes, handles, temperatures = [], [], []
    named_processes={}
    peak_process_rss={}
    started, last_rows, stop_reason = time.perf_counter(), 0, "wall_budget"
    started_unix=time.time()
    minimum_available_ram = None
    low_ram_samples = 0
    capture_proof=None
    capture_proof_error=None
    try:
        def launch(command, name, cwd):
            handle = (results / (name + "_launcher.log")).open("x", encoding="utf-8")
            handles.append(handle)
            process = subprocess.Popen(command, cwd=cwd, stdout=handle, stderr=subprocess.STDOUT,
                                       stdin=subprocess.PIPE, env=environment, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            processes.append(process)
            named_processes[name]=process
            return process
        direct_commands = {}
        if args.launcher == "direct":
            export_dir = runtime / "launch"
            preparation = launch(gradle + ["-PflycraftRunDir=" + java_path(runtime / "prepare"),
                "-PflycraftAutotest", "-PflycraftServer=127.0.0.1:25567", "-PflycraftGraphicsBackend="+args.graphics_backend,
                "-PflycraftExportLaunchDir="+java_path(export_dir), "runServer"] + (["runClient"] if graphical else []), "prepare", ROOT / "minecraft_mod")
            preparation_deadline=time.perf_counter()+min(90,args.seconds)
            while preparation.poll() is None:
                if time.perf_counter()>=preparation_deadline:
                    raise RuntimeError("launch_preparation_timeout")
                time.sleep(.5)
            if preparation.returncode != 0:
                raise RuntimeError("launch_preparation_failed")
            for name in (("server", "client") if graphical else ("server",)):
                direct_commands[name]=command_from_export(export_dir / ("run"+name.title()+".json"),
                    export_dir / (name+".args"), expected_java=java)
        bridge_command = [sys.executable, str(ROOT / "minecraft_bridge.py"), "--phase8-checkpoint", str(args.checkpoint.resolve()),
                          "--phase8-results", str(results / "controller.jsonl"), "--log", str(results / "bridge.jsonl"),
                          "--phase8-control", str(control)]
        if args.frozen_checkpoint:
            bridge_command += ["--phase8-frozen-checkpoint", str(args.frozen_checkpoint.resolve())]
        if args.train:
            bridge_command += ["--phase8-save-dir", str(ROOT / "checkpoints" / phase / args.run_id)]
        bridge = launch(bridge_command, "bridge", ROOT)
        server = launch(direct_commands["server"] if direct_commands else
            gradle + ["-PflycraftRunDir=" + java_path(server_dir), "runServer", "--args=nogui"],
            "server", server_dir if direct_commands else ROOT / "minecraft_mod")
        client = None
        next_thermal = 0
        while time.perf_counter() - started < args.seconds:
            elapsed = time.perf_counter() - started
            available_ram = psutil.virtual_memory().available / 1024**2
            for process_name,owned_process in named_processes.items():
                observed_rss=owned_rss_mib(owned_process)
                if observed_rss is not None:
                    peak_process_rss[process_name]=max(peak_process_rss.get(process_name,0),observed_rss)
            minimum_available_ram = available_ram if minimum_available_ram is None else min(minimum_available_ram, available_ram)
            low_ram_samples = low_ram_samples + 1 if available_ram < args.minimum_available_ram_mib else 0
            if low_ram_samples >= 3:
                stop_reason = "available_ram_guard"; break
            recording_active=recorder.pulse()
            graphics_ready=not graphical
            client_launcher=results / "client_launcher.log"
            if graphical and client_launcher.exists():
                graphics_log=client_launcher.read_text(encoding="utf-8",errors="replace")
                graphics_ready, graphics_error = graphics_readiness(graphics_log,args.graphics_backend)
                if graphics_error:
                    stop_reason=graphics_error; break
            spectator_ready=not args.spectator or (runtime/"spectator.ready").exists()
            if args.spectator and recording_active and spectator_ready and capture_proof is None:
                state=recorder.state()
                game_frame=runtime/"spectator-frame.png"
                obs_frame=Path(state[6]) if state and state[6] else None
                if game_frame.is_file() and obs_frame is not None and obs_frame.is_file() and obs_frame.stat().st_mtime>=game_frame.stat().st_mtime:
                    try:
                        proof=compare_capture_frames(game_frame,obs_frame)
                        if proof["matched"]:
                            capture_proof=proof
                            recorder.mark_capture_verified()
                            print(json.dumps({"capture_proof":"matched_real_Minecraft_frame","rgb_error":proof["mean_absolute_rgb_error"]}),flush=True)
                        else:
                            capture_proof_error=proof
                    except (ValueError,OSError,subprocess.SubprocessError) as error:
                        capture_proof_error=str(error)
            content_ready=not args.spectator or capture_proof is not None
            if recording_active and graphics_ready and spectator_ready and content_ready and (not args.headless or listening(8765)) and not (runtime / "start.enabled").exists():
                (runtime / "start.enabled").write_text("OBS confirmed active\n" if graphical else "Event logging ready\n", encoding="utf-8")
            if graphical and client is None and listening(25567) and listening(8765):
                client = launch(direct_commands["client"] if direct_commands else
                    gradle + ["-PflycraftRunDir=" + java_path(client_dir), "-PflycraftAutotest", "-PflycraftServer=127.0.0.1:25567",
                    "-PflycraftGraphicsBackend="+args.graphics_backend, "runClient"],
                    "client", client_dir if direct_commands else ROOT / "minecraft_mod")
            server_rows = (results / "server.jsonl").read_text(encoding="utf-8").splitlines() if (results / "server.jsonl").exists() else []
            if len(server_rows) != last_rows:
                last_rows = len(server_rows)
                print(json.dumps({"elapsed_seconds": round(elapsed, 1), "completed": last_rows, "requested": len(rows), "last": json.loads(server_rows[-1])}), flush=True)
            if control.exists() and json.loads(control.read_text()).get("suite_complete"):
                stop_reason = "suite_complete"
                closing_deadline=time.perf_counter()+10
                while any(process.poll() is None for name,process in named_processes.items() if name in {"client","server"}) and time.perf_counter()<closing_deadline:
                    recorder.pulse(); time.sleep(.25)
                break
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
        natural_exits={name:process.poll() for name,process in named_processes.items()}
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
        summary["milestone"] = args.milestone
        summary["experiment_stage"] = "development"
        summary["redo_of"] = args.redo_of
        summary["execution_kind"] = "new_execution_not_replay"
        summary["headless"] = args.headless
        summary["spectator"] = args.spectator
        summary["spectator_view"] = args.spectator_view if args.spectator else None
        summary["capture_requested_size"] = [args.capture_width,args.capture_height] if graphical else None
        summary["client_fps_limit"] = 30 if graphical else None
        summary["capture_content_proof"] = capture_proof
        summary["capture_content_proof_error"] = capture_proof_error
        summary["recording_mode"] = "OBS_isolated_spectator" if args.spectator else "OBS_Minecraft_window" if graphical else "structured_event_logs_no_video"
        summary["generated_world_instances"] = int((server_dir/"world/level.dat").exists())
        summary["episodes_in_generated_world"] = last_rows
        summary["environment_kind"] = "controlled_flat_survival_fixture"
        summary["server_heap_mib"] = args.server_heap_mib
        summary["client_heap_mib"] = args.client_heap_mib if graphical else None
        summary["trial_tick_limit"] = args.trial_ticks
        summary["policy_rng_seed"] = 9001
        summary["camera_mode"] = args.camera_mode
        summary["turn_degrees"] = args.turn_degrees
        summary["experiment_kind"] = "scripted_camera_probe_not_policy" if args.camera_probe else "policy_goal"
        summary["interaction_assistance"] = "visible_target_aim_macro" if args.camera_mode=="legacy" else "crosshair_only_no_automatic_aim"
        summary["requested_graphics_backend"] = args.graphics_backend
        summary["launcher"] = args.launcher
        summary["minimum_sampled_available_ram_mib"] = minimum_available_ram
        summary["available_ram_guard_mib"] = args.minimum_available_ram_mib
        summary["peak_sampled_process_tree_rss_mib"] = peak_process_rss
        summary["exit_codes_before_cleanup"] = natural_exits
        summary["client_exited_cleanly"] = natural_exits.get("client")==0 if graphical else None
        summary["server_exited_cleanly"] = natural_exits.get("server")==0
        client_log=results / "client_launcher.log"
        client_log_text=client_log.read_text(encoding="utf-8",errors="replace") if client_log.exists() else ""
        if natural_exits.get("client") in (-1073741819,3221225477) or any(marker in client_log_text for marker in ("0xC0000005", "exit value -1073741819", "exit value 3221225477")):
            summary["native_client_crash"] = True
            summary["stop_reason"] = "native_client_crash"
        if client_log.exists():
            graphics_lines=client_log_text.splitlines()
            summary["actual_graphics"]=[line.split("(Minecraft)",1)[-1].strip() for line in graphics_lines
                if "Using graphics backend " in line or "Using graphics device:" in line]
        summary["policy_label"] = args.policy_label
        summary["checkpoint"] = str(args.checkpoint.resolve())
        summary["checkpoint_sha256"] = hashlib.sha256(args.checkpoint.read_bytes()).hexdigest()
        summary["implementation_sha256"] = implementation_sha256
        if args.frozen_checkpoint:
            summary["frozen_label"] = args.frozen_label
            summary["frozen_checkpoint"] = str(args.frozen_checkpoint.resolve())
            summary["frozen_checkpoint_sha256"] = hashlib.sha256(args.frozen_checkpoint.read_bytes()).hexdigest()
        if args.milestone is not None:
            summary["milestone_video_status"]="missing"
            try:
                if recording is None or not recorder.started:
                    raise ValueError("No confirmed recording source exists")
                if Path(recording).stat().st_mtime<started_unix-2:
                    raise ValueError("Recording path predates this run")
                video_name=f"FlyCraft_Development_Milestone_{args.milestone:05d}_{args.run_id}.mp4"
                destination=ROOT/"recordings/phase9"/video_name
                # Independent server episode time is a conservative coverage
                # minimum; OBS was gated before any policy action.
                scores=[json.loads(line) for line in (results/"server.jsonl").read_text().splitlines()]
                minimum_seconds=sum(row["ticks"]/20 for row in scores)
                verified=preserve_milestone(recording,destination,minimum_seconds=minimum_seconds)
                complete=last_rows==len(rows) and summary["stop_reason"]=="suite_complete" and capture_proof is not None
                verified["episode_coverage_complete"]=complete
                verified["visual_content_preflight_verified"]=capture_proof is not None
                summary["milestone_video_status"]="verified" if complete else "partial"
                summary["milestone_video"]=verified
                if args.video_export_dir is not None:
                    args.video_export_dir.mkdir(parents=True,exist_ok=True)
                    export=args.video_export_dir/video_name
                    if export.exists(): raise FileExistsError("Refusing to overwrite exported video")
                    shutil.copy2(destination,export)
                    summary["milestone_video_export"]=str(export)
            except Exception as error:
                summary["milestone_video_error"]=str(error)
            media_folder=ROOT/"recordings/phase9/youtube"
            media_folder.mkdir(parents=True,exist_ok=True)
            media={"run_id":args.run_id,"milestone":args.milestone,"stage":"development",
                "status":summary["milestone_video_status"],"video":summary.get("milestone_video"),
                "error":summary.get("milestone_video_error"),"episode_log":str(results/"server.jsonl"),
                "action_log":str(results/"headless.jsonl"),"observation_log":str(results/"bridge.jsonl"),
                "checkpoint":summary["checkpoint"],"checkpoint_sha256":summary["checkpoint_sha256"],
                "checkpoint_timing":"before_episode_update","camera_role":"recording_only",
                "recording_kind":"synchronized_spectator_capture","redo_of":args.redo_of,
                "replay":False,"actions_altered_for_video":False}
            with (media_folder/(args.run_id+".json")).open("x",encoding="utf-8",newline="\n") as handle:
                json.dump(media,handle,indent=2)
        (results / "run.json").write_text(json.dumps(summary, indent=2), encoding="utf-8",newline="\n")
        print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
