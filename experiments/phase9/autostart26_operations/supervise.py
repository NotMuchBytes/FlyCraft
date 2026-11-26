"""User-authorized restart supervisor. Never selects a Minecraft action."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import psutil


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def digest(path):
    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle,"sha256").hexdigest()


def publish(path, value):
    """Readers can hold Windows files briefly; retain the previous full frame."""
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name(path.name+f".{os.getpid()}.tmp")
    try:
        temporary.write_text(json.dumps(value,indent=2)+"\n",encoding="utf-8")
        deadline=time.monotonic()+2
        while True:
            try:
                os.replace(temporary,path);return True
            except PermissionError:
                if time.monotonic()>=deadline:return False
                time.sleep(.02)
    except OSError:
        return False


class Lease:
    def __init__(self, path):self.path=Path(path)
    def __enter__(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        self.handle=self.path.open("a+b");self.handle.seek(0,2)
        if self.handle.tell()==0:self.handle.write(b"0");self.handle.flush()
        self.handle.seek(0)
        try:
            if os.name=="nt":
                import msvcrt
                msvcrt.locking(self.handle.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(self.handle.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError:
            self.handle.close();raise RuntimeError("restart supervisor already owns the lease")
        return self
    def __exit__(self,*unused):self.handle.close()


def alive(record, marker):
    """PID reuse or a similarly named process does not grant ownership."""
    try:
        process=psutil.Process(record["pid"])
        return abs(process.create_time()-record["process_created"])<.01 and any(marker in arg for arg in process.cmdline())
    except (KeyError,psutil.Error):return False


def source_hash(root):
    root=Path(root)
    files=[root/"minecraft_bridge.py",root/"minecraft_mod/build.gradle",root/"requirements.txt"]
    for folder in ("autonomy","learning","simulator","interface","minecraft_mod/src","tools"):
        files.extend(p for p in (root/folder).rglob("*") if p.is_file() and p.suffix in {".py",".java",".json",".png",".lua"})
    hashes={p.relative_to(root).as_posix():digest(p) for p in sorted(set(files)) if p.is_file()}
    return hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()


def decision(folder):
    folder=Path(folder)
    if (folder/"STOP").exists():return "paused_by_stop"
    if (folder/"fix_request.json").exists():return "needs_review"
    state=read(folder/"state.json")
    if state.get("status") in {"stage_gate_failed","awaiting_next_skill_implementation","curriculum_complete"}:
        return state["status"]
    return "resume"


def clear_critical_stop(folder, battery):
    """Clear only a STOP created by this guard at critical battery, never manual STOP."""
    folder=Path(folder);stop=folder/"STOP";proof=folder/"STOP.reason.json"
    if battery is None or not battery.power_plugged or battery.percent<=10 or not stop.exists() or not proof.exists():return False
    try:
        data=read(proof)
        if data.get("reason")!="critical_battery" or data.get("stop_mtime_ns")!=stop.stat().st_mtime_ns:return False
        archived=folder/f"critical_stop_recovered_{time.time_ns()}.json"
        if not publish(archived,data):return False
        stop.unlink();proof.unlink();return True
    except (OSError,ValueError):return False


def launch(command, root, log):
    Path(log).parent.mkdir(parents=True,exist_ok=True)
    with Path(log).open("ab") as output:
        process=subprocess.Popen(command,cwd=root,stdout=output,stderr=subprocess.STDOUT,
            creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
    return dict(pid=process.pid,process_created=psutil.Process(process.pid).create_time())


def ensure_companion(command, marker, root, state, name, *, adopt=None):
    record=read(state/(name+".owner.json")) if (state/(name+".owner.json")).exists() else {}
    if alive(record,marker):return record
    if adopt:
        try:
            current=read(adopt)
            if current.get("status")=="active":
                process=psutil.Process(current["pid"])
                candidate=dict(pid=process.pid,process_created=process.create_time())
                if alive(candidate,marker):publish(state/(name+".owner.json"),candidate);return candidate
        except (OSError,ValueError,KeyError,psutil.Error):pass
    record=launch(command,root,state/(name+".log"));publish(state/(name+".owner.json"),record);return record


def run(plan_path, *, once=False):
    plan=read(plan_path);root=Path(plan["root"]);folder=Path(plan["campaign"]);state=Path(plan["state_dir"])
    state.mkdir(parents=True,exist_ok=True)
    with Lease(state/"supervisor.lock"):
        while True:
            try:
                if (state/"DISABLE_AUTOSTART").exists():return 0
                completion=read(state/"completion/status.json") if (state/"completion/status.json").exists() else {}
                if completion.get("status") in {"shutdown_countdown","shutdown_requested"}:return 0
                battery=psutil.sensors_battery()
                clear_critical_stop(folder,battery)
                if battery is not None and not battery.power_plugged and battery.percent<=5:
                    status="critical_battery"
                elif (state/"power_guard/RELEASE").exists():
                    status="power_guard_released"
                else:
                    ensure_companion([plan["python"],str(root/"tools/power_guard.py"),"--state-dir",str(state/"power_guard"),
                        "--stop-file",str(folder/"STOP"),"--stop-file",plan["foundation_stop"]],
                        "power_guard.py",root,state,"power_guard",adopt=state/"power_guard/status.json")
                    ensure_companion([plan["python"],str(root/"experiments/phase9/staged25_operations/finish_when_staged_verified.py"),
                        "--campaign",str(folder),"--guard-state",str(state/"power_guard"),"--state-dir",str(state/"completion"),
                        "--ffmpeg",plan["ffmpeg"],"--shutdown-on-complete"],"finish_when_staged_verified.py",root,state,"completion")
                    config,ledger=read(folder/"config.json"),read(folder/"state.json")
                    if digest(folder/"config.json")!=ledger["config_sha256"] or source_hash(root)!=config["implementation_sha256"]:
                        status="implementation_mismatch"
                    else:
                        executor=read(folder/"executor.json") if (folder/"executor.json").exists() else {}
                        owner=read(state/"runner.owner.json") if (state/"runner.owner.json").exists() else {}
                        if alive(executor,"run_staged_curriculum.py") or alive(owner,"run_staged_curriculum.py"):
                            status="running"
                        elif ledger["active_attempt"] is not None or (folder/"fix_request.json").exists() and time.time()-getattr(run,"last_recovery",0)>60:
                            run.last_recovery=time.time()
                            recovered=subprocess.run([plan["python"],str(Path(__file__).with_name("recover.py")),"--plan",str(plan_path)],cwd=root,
                                capture_output=True,text=True,timeout=120)
                            publish(state/"last_recovery.json",dict(exit_code=recovered.returncode,output=recovered.stdout[-8000:],error=recovered.stderr[-2000:]))
                            status="recovered" if recovered.returncode==0 else "needs_review"
                        else:
                            status=decision(folder)
                            if status=="resume":
                                power=read(state/"power_guard/status.json") if (state/"power_guard/status.json").exists() else {}
                                battery=psutil.sensors_battery()
                                if battery is not None and not battery.power_plugged and battery.percent<=5:
                                    status="critical_battery"
                                elif power.get("status")!="active" or time.time()-power.get("updated_unix",0)>10:
                                    status="waiting_power_guard"
                                else:
                                    command=[plan["python"],str(root/"tools/run_staged_curriculum.py"),"run","--campaign",str(folder),
                                        "--work-dir",plan["work_dir"],"--build-dir",plan["build_dir"],"--obs-control-dir",plan["obs_control_dir"],
                                        "--video-export-dir",plan["video_export_dir"],"--max-attempts","1000"]
                                    owner=launch(command,root,state/"runner.log");publish(state/"runner.owner.json",owner)
                                    status="launched"
                publish(state/"status.json",dict(status=status,pid=os.getpid(),process_created=psutil.Process().create_time(),
                    updated_unix=time.time(),campaign=str(folder),automatic_gate_bypass=False,manual_stop_preserved=True))
            except Exception as error:
                publish(state/"status.json",dict(status="needs_review",error=str(error),pid=os.getpid(),updated_unix=time.time()))
            if once:return 0
            time.sleep(5)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--plan",type=Path,required=True);parser.add_argument("--once",action="store_true")
    args=parser.parse_args()
    try:raise SystemExit(run(args.plan,once=args.once))
    except RuntimeError as error:
        if "already owns the lease" not in str(error):raise
