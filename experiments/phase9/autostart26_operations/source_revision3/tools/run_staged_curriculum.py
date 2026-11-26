"""Run the user-selected curriculum with independently checked evidence gates."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import psutil

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from autonomy.experiment import CampaignLock, atomic_json
from autonomy.official import cleanup_world
from autonomy.staged import StagedCampaign
from tools.obs_session import BackgroundRecorder
from tools.resource_readiness import ResourceReadiness
from tools.run_phase9 import dashboard, worker_command
from tools.supervise_phase9 import gpu_temperature, request_fix, wait_resources


def run(campaign, args):
    worker, recorder = None, None
    try:
        recovered = campaign.recover()
        if recovered and recovered["status"] != "committed":
            raise ValueError("interrupted worker requires evidence review before resuming")
        with ResourceReadiness(ROOT, gpu_temperature) as readiness:
            for _ in range(args.max_attempts):
                if (campaign.folder / "STOP").exists() or (campaign.folder / "fix_request.json").exists():
                    break
                cell = campaign.next_cell()
                if cell is None:
                    break
                filming = cell["split"] == "training" and campaign.training_worlds()+1 in campaign.config["recording_milestones"]
                threshold = 3000 if filming else 1800
                # Keep waiting safely under pressure; never lower the reserves.
                if not wait_resources(campaign, time.monotonic()+60, required_ram_mib=threshold, readiness=readiness):
                    continue
                attempt = campaign.begin_next(args.work_dir)
                if attempt is None:
                    break
                cycle = time.monotonic()
                atomic_json(campaign.folder / "executor.json", dict(status="running", pid=os.getpid(),
                    process_created=psutil.Process().create_time(), curriculum_stage=attempt["curriculum_stage"],
                    official_training_worlds=campaign.training_worlds(), active_run=attempt["run_id"]))
                if attempt["video_required"]:
                    recorder = BackgroundRecorder(args.obs_control_dir, campaign.folder / "recorder" / attempt["run_id"])
                    recorder.ensure_ready(lambda: (campaign.folder / "STOP").exists())
                with (campaign.folder / (attempt["run_id"] + ".log")).open("x", encoding="utf-8") as log:
                    worker = subprocess.Popen(worker_command(campaign, attempt, args, 300), cwd=ROOT,
                        stdout=log, stderr=subprocess.STDOUT, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                    owner = psutil.Process(worker.pid)
                    row = campaign.state["attempts"][-1]
                    row.update(worker_pid=worker.pid, worker_created=owner.create_time())
                    campaign.save()
                    while worker.poll() is None:
                        dashboard(campaign, "broader curriculum: " + attempt["curriculum_stage"], ROOT / "experiments/phase9" / attempt["run_id"])
                        time.sleep(2)
                outcome = campaign.recover()
                if recorder:
                    recorder.close()
                    recorder = None
                campaign.state["attempts"][-1]["coordinator_cycle_seconds"] = time.monotonic()-cycle
                campaign.save()
                if outcome["status"] != "committed":
                    raise ValueError(outcome.get("error", "worker evidence incomplete"))
                cleanup_world(campaign, campaign.state["attempts"][-1], args.work_dir)
                print(json.dumps(dict(run_id=attempt["run_id"], stage=attempt["curriculum_stage"],
                    split=attempt["split"], condition=attempt["condition"], success=outcome["success"],
                    actions=outcome["actions"], update=outcome["update"])), flush=True)
                # Review a weak skill rather than spending the entire budget on it.
                recent = [a for a in campaign.state["attempts"] if a["status"] == "committed" and a["train"]
                          and a["curriculum_stage"] == attempt["curriculum_stage"]
                          and a.get("curriculum_round",0) == attempt.get("curriculum_round",0) and not a["retention"]][-10:]
                if len(recent) == 10 and sum(a["success"] for a in recent) <= 1:
                    raise ValueError("at least nine of ten primary training episodes failed; inspect before more training")
        status = "paused" if (campaign.folder / "STOP").exists() else campaign.state["status"]
        atomic_json(campaign.folder / "executor.json", dict(status=status, updated_unix=time.time(),
            official_training_worlds=campaign.training_worlds(), automatic_shutdown_ready=False))
        dashboard(campaign, status)
        return 0
    except (Exception, KeyboardInterrupt) as error:
        if worker is not None and worker.poll() is None:
            (campaign.folder / "STOP").touch(exist_ok=True)
            worker.wait(timeout=40)
        if campaign.state["active_attempt"] is not None:
            campaign.recover()
        request_fix(campaign.folder, str(error), code="staged_curriculum_review", attempt=campaign.state["attempts"][-1] if campaign.state["attempts"] else None)
        atomic_json(campaign.folder / "executor.json", dict(status="needs_attention", error=str(error), updated_unix=time.time(), automatic_shutdown_ready=False))
        return 2
    finally:
        if recorder:
            recorder.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init")
    for name in ("campaign", "handoff", "cache"):
        init.add_argument("--" + name, type=Path, required=True)
    init.add_argument("--authorization", required=True)
    launch = sub.add_parser("run")
    for name in ("campaign", "work-dir", "build-dir", "obs-control-dir", "video-export-dir"):
        launch.add_argument("--" + name, type=Path, required=True)
    launch.add_argument("--max-attempts", type=int, default=1000)
    args = parser.parse_args()
    if args.command == "init":
        campaign = StagedCampaign.create_from_foundation(args.campaign, project_root=ROOT,
            handoff=args.handoff, cache=args.cache, authorization=args.authorization)
        print(campaign.folder)
        return 0
    if not 1 <= args.max_attempts <= 10000:
        parser.error("max-attempts must be 1..10000")
    with CampaignLock(args.campaign):
        return run(StagedCampaign(args.campaign, project_root=ROOT), args)


if __name__ == "__main__":
    raise SystemExit(main())
