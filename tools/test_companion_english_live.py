"""Disposable companion-language diagnostic; never counts as campaign evaluation.

Use launch exports from this checkout's Gradle runServer/runClient tasks. The
fixture supplies synthetic chat, initial poses and a tree, never gameplay actions.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

import psutil

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.java_launch import command_from_export
from autonomy.experiment import source_manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--launch-dir', type=Path, required=True)
    parser.add_argument('--runtime', type=Path, required=True, help='New disposable directory')
    parser.add_argument('--checkpoint', type=Path, required=True)
    parser.add_argument('--request', default='FlyCraft, get me one log')
    parser.add_argument('--lesson', default='')
    parser.add_argument('--vocabulary', type=Path, help='Reload a prior fixture vocabulary into this new world')
    parser.add_argument('--seconds', type=int, default=240)
    parser.add_argument('--server-port', type=int, default=25577)
    parser.add_argument('--bridge-port', type=int, default=8875)
    parser.add_argument('--video', type=Path, help='Record a fresh milestone with OBS, then fully decode it')
    parser.add_argument('--obs-control-dir', type=Path)
    args = parser.parse_args()
    if args.video and not args.obs_control_dir: parser.error('--video requires --obs-control-dir')
    if args.video and args.video.exists(): parser.error('Refusing to overwrite existing milestone footage')
    runtime = args.runtime.resolve()
    runtime.mkdir(parents=True, exist_ok=False)
    checkpoint = args.checkpoint.resolve(strict=True)
    if args.vocabulary: shutil.copyfile(args.vocabulary.resolve(strict=True),runtime/'learned_item_names.properties')
    control = runtime / 'control.json'
    result = runtime / 'fixture.json'
    props = dict(worldName='world', controlFile=control.as_posix(), maxRunTicks=2400,
        projectDirectory=ROOT.as_posix(), pythonExecutable=sys.executable.replace('\\', '/'),
        checkpointFile=checkpoint.as_posix(), bridgePort=args.bridge_port,
        integrationTestDedicated='true', **{'fixture.result': result.as_posix(),
        'fixture.request': args.request, 'fixture.lesson': args.lesson})
    if args.video: props['fixture.startGate']=(runtime/'start.enabled').as_posix()
    def write_props(name, values):
        (runtime/name).write_text(''.join(f'{key}={value}\n' for key,value in values.items()), encoding='utf-8')
    write_props('flycraft-companion.properties', props)
    write_props('flycraft-headless.properties', dict(**{'companion.enabled':'true',
        'controlFile':control.as_posix(), 'traceFile':(runtime/'headless').as_posix(),
        'bridgePort':args.bridge_port, 'camera.mode':'bounded', 'camera.turnDegrees':15,
        'camera.pitchActions':'true', 'motor.forwardTicks':2, 'motor.verifyMovement':'true'}))
    write_props('server.properties', {'server-ip':'127.0.0.1','server-port':args.server_port,
        'online-mode':'false','enforce-secure-profile':'false','level-name':'world','level-seed':9172501,
        'level-type':'minecraft:flat','gamemode':'survival','force-gamemode':'true','difficulty':'peaceful',
        'generate-structures':'false','spawn-protection':0,'max-players':5,'view-distance':2,
        'simulation-distance':2,'allow-flight':'false'})
    (runtime/'eula.txt').write_text('eula=true\n')  # Existing local-test acceptance.
    (runtime/'source_manifest.json').write_text(json.dumps(source_manifest(ROOT),indent=2))
    checkpoint_digest=hashlib.sha256(checkpoint.read_bytes()).hexdigest()
    command = command_from_export(args.launch_dir/'runServer.json', runtime/'server.args',
        expected_java=ROOT/'.runtime/jdk-25/bin/java.exe')
    # Launch exports carry absolute classpaths; working directory is disposable.
    with (runtime/'server.args').open('a') as handle: handle.write('"nogui"\n')
    report = dict(environment='controlled_companion_language_fixture', request=args.request,
        lesson=args.lesson, checkpoint=str(checkpoint), server_port=args.server_port,
        bridge_port=args.bridge_port, success=False, stop_reason='not_started')
    report['checkpoint_sha256']=checkpoint_digest
    if args.vocabulary: report['reloaded_vocabulary_sha256']=hashlib.sha256(args.vocabulary.read_bytes()).hexdigest()
    process = client = background = recorder = client_log = None
    capture_proof = None
    started = time.monotonic()
    low_ram = 0
    try:
        minimum_ram=3000 if args.video else 1800
        if psutil.virtual_memory().available/1024**2 < minimum_ram: raise RuntimeError(f'launch_ram_guard_{minimum_ram}_mib')
        if shutil.disk_usage(runtime).free/1024**2 < 2048: raise RuntimeError('disk_guard_2048_mib')
        for port in (args.server_port, args.bridge_port):
            import socket
            with socket.socket() as probe:
                if probe.connect_ex(('127.0.0.1',port))==0: raise RuntimeError(f'port_in_use_{port}')
        if args.video:
            from tools.obs_session import BackgroundRecorder
            from tools.obs_control import ObsRecorder
            from tools.milestone_video import require_video_tools
            require_video_tools()
            background=BackgroundRecorder(args.obs_control_dir,runtime/'recorder')
            report['capture_profile']=background.ensure_ready()
            recorder=ObsRecorder(args.obs_control_dir,runtime.name)
        with (runtime/'server.log').open('x',encoding='utf-8') as log:
            process = subprocess.Popen(command,cwd=runtime,stdout=log,stderr=subprocess.STDOUT,
                stdin=subprocess.PIPE,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            while process.poll() is None:
                elapsed = time.monotonic()-started
                available = psutil.virtual_memory().available/1024**2
                low_ram = low_ram+1 if available<768 else 0
                thermal = subprocess.run(['nvidia-smi','--query-gpu=temperature.gpu','--format=csv,noheader,nounits'],
                    capture_output=True,text=True,timeout=4,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                if thermal.returncode: raise RuntimeError('temperature_probe_unavailable')
                temperature = max(map(int,thermal.stdout.split()))
                (runtime/'status.json').write_text(json.dumps(dict(elapsed_seconds=elapsed,
                    available_ram_mib=available,gpu_temperature_c=temperature)))
                if temperature>=75: raise RuntimeError('gpu_temperature_guard_75_c')
                if low_ram>=3: raise RuntimeError('available_ram_guard_768_mib')
                if shutil.disk_usage(runtime).free/1024**2<2048: raise RuntimeError('disk_guard_2048_mib')
                if elapsed>args.seconds: raise RuntimeError('diagnostic_timeout')
                if args.video:
                    if client is None and 'Done (' in (runtime/'server.log').read_text(encoding='utf-8',errors='replace'):
                        folder=runtime/'client';folder.mkdir()
                        (runtime/'spectator_control.json').write_text('{"suite_complete":false}')
                        (folder/'flycraft-spectator.properties').write_text(
                            f'controlFile={(runtime/"spectator_control.json").as_posix()}\n'
                            f'readyFile={(runtime/"spectator.ready").as_posix()}\n'
                            f'frameFile={(runtime/"spectator-frame.png").as_posix()}\n'
                            f'captureGate={(runtime/"start.enabled").as_posix()}\n'
                            f'windowTitle=FlyCraft Recording {runtime.name}\nview=first_person\n')
                        # Enables the existing non-focus-requesting GLFW window
                        # redirect; spectator mode takes precedence over this marker.
                        (folder/'flycraft-phase8-client.properties').write_text('recording_only=true\n')
                        (folder/'options.txt').write_text('maxFps:30\nrenderDistance:2\nsimulationDistance:5\nparticles:2\nfullscreen:false\npauseOnLostFocus:false\nsoundCategory_master:0.0\n')
                        exported=json.loads((args.launch_dir/'runClient.json').read_text())
                        index=exported['arguments'].index('--quickPlayMultiplayer')
                        exported['arguments'][index+1]=f'127.0.0.1:{args.server_port}'
                        (folder/'launch.json').write_text(json.dumps(exported))
                        client_command=command_from_export(folder/'launch.json',folder/'client.args',
                            expected_java=ROOT/'.runtime/jdk-25/bin/java.exe')
                        client_log=(runtime/'client.log').open('x',encoding='utf-8')
                        client=subprocess.Popen(client_command,cwd=folder,stdout=client_log,stderr=subprocess.STDOUT,
                            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                    active=recorder.pulse()
                    if client is not None and client.poll() is not None: raise RuntimeError('spectator_exited')
                    if client is not None and not result.exists() and 'Client disconnected with reason:' in (runtime/'client.log').read_text(encoding='utf-8',errors='replace'):
                        raise RuntimeError('spectator_disconnected_before_completion')
                    if active and (runtime/'spectator.ready').exists() and capture_proof is None:
                        from tools.milestone_video import compare_capture_frames
                        from tools.run_phase8_live import graphics_readiness
                        graphics=(runtime/'client.log').read_text(encoding='utf-8',errors='replace')
                        ready,error=graphics_readiness(graphics,'opengl')
                        if error: raise RuntimeError(error)
                        device=[line for line in graphics.splitlines() if 'using graphics device:' in line.lower()]
                        if ready and device and 'rtx 4050' not in device[-1].lower(): raise RuntimeError('rtx_4050_not_selected')
                        state=recorder.state();game=runtime/'spectator-frame.png'
                        observed=Path(state[6]) if state and state[6] else None
                        if ready and game.exists() and observed and observed.exists() and abs(game.stat().st_mtime-observed.stat().st_mtime)<=3:
                            try:
                                shutil.copyfile(game,runtime/'capture-game.png');shutil.copyfile(observed,runtime/'capture-obs.png')
                                proof=compare_capture_frames(runtime/'capture-game.png',runtime/'capture-obs.png')
                                if proof['matched']:
                                    capture_proof=proof;recorder.mark_capture_verified()
                                    report['capture_proof']=proof;report['graphics_device']=device[-1]
                                    (runtime/'start.enabled').write_text('Verified Minecraft-only OBS capture\n')
                            except (OSError,ValueError,subprocess.SubprocessError): pass
                time.sleep(1)
            if not result.exists(): raise RuntimeError('no_fixture_result')
            report.update(json.loads(result.read_text()))
            report['stop_reason']='fixture_complete'
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as error:
        report['stop_reason']=str(error)
    finally:
        if process is not None and process.poll() is None:
            try:
                process.communicate(b'stop\n',timeout=15)
            except (subprocess.TimeoutExpired,OSError):
                process.terminate()
                process.wait(timeout=10)
        if recorder is not None:
            try:
                recorded=recorder.stop()
                if recorded and args.video:
                    from tools.milestone_video import preserve_milestone
                    args.video.parent.mkdir(parents=True,exist_ok=True)
                    report['video_verification']=preserve_milestone(recorded,args.video,minimum_seconds=5)
                    report['video_path']=str(args.video.resolve())
            except (OSError,RuntimeError,ValueError,subprocess.SubprocessError) as error: report['recording_error']=str(error)
        if client is not None and client.poll() is None:
            (runtime/'spectator_control.json').write_text('{"suite_complete":true}')
            try: client.wait(timeout=10)
            except subprocess.TimeoutExpired: client.terminate();client.wait(timeout=10)
        if client_log is not None: client_log.close()
        if background is not None:
            try: background.close()
            except (OSError,RuntimeError) as error: report['recorder_close_error']=str(error)
        report['checkpoint_unchanged']=hashlib.sha256(checkpoint.read_bytes()).hexdigest()==checkpoint_digest
        report['elapsed_seconds']=time.monotonic()-started
        (runtime/'summary.json').write_text(json.dumps(report,indent=2))
        print(json.dumps(report),flush=True)
    verified_capture=not args.video or bool(report.get('video_verification') and report.get('capture_proof'))
    return 0 if report['success'] and verified_capture and report['checkpoint_unchanged'] else 1


if __name__=='__main__': raise SystemExit(main())
