#!/usr/bin/env python3
"""Checked development batches and Codex repair handoffs; no official campaign."""

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
from autonomy.evidence import audit_run, EvidenceError, file_sha256
from autonomy.experiment import Campaign, CampaignLock, atomic_json
from tools.run_phase9 import worker_command, dashboard
from tools.obs_session import BackgroundRecorder


def request_fix(folder, reason, *, code="supervisor_error", attempt=None):
    """Save a local handoff for Codex; never run commands suggested by evidence."""
    folder = Path(folder)
    directory = folder / "attention"
    directory.mkdir(parents=True, exist_ok=True)
    number = len(list(directory.glob("request_*.json"))) + 1
    record = {"schema": 1, "id": f"request_{number:04d}", "created_unix": time.time(),
              "reviewer": "Codex", "status": "needs_attention", "code": code, "reason": str(reason),
              "attempt": attempt, "automatic_code_changes": False,
              "campaign": str(folder.resolve()),
              "next_step": "Codex should inspect the preserved evidence, fix the cause, run tests and a fresh small live validation. Changed source requires a new frozen development campaign. Never rescore valid failures or change benchmark rules."}
    evidence = Path((attempt or {}).get("results") or folder / "no_worker_evidence")
    record["evidence_sha256"] = {path.name: file_sha256(path) for path in sorted(evidence.glob("*"))
                                  if path.is_file() and path.suffix in (".json", ".jsonl", ".log", ".png")}
    path = directory / (record["id"] + ".json")
    atomic_json(path, record)
    atomic_json(folder / "fix_request.json", record)
    (directory / (record["id"] + ".md")).write_text(
        f"# FlyCraft needs Codex attention\n\n{record['code']}: {record['reason']}\n\n"
        f"Campaign: `{record['campaign']}`\n\n"
        f"Run: `{(attempt or {}).get('run_id', 'not launched')}`\n\n"
        f"Evidence: `{(attempt or {}).get('results', '')}`\n\n"
        f"{record['next_step']}\n", encoding="utf-8", newline="\n")
    atomic_json(folder / "supervisor.json", {"status": "needs_attention", "fix_request": str(path),
                "official_training_worlds": 0, "automatic_code_changes": False})
    print(json.dumps({"status": "needs_attention", "fix_request": str(path), "reason": str(reason)}), flush=True)
    return record


def gpu_temperature():
    try:
        result = subprocess.run(["nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv,noheader,nounits"],
                                capture_output=True, text=True, timeout=3)
        return max(int(line.strip()) for line in result.stdout.splitlines()) if result.returncode == 0 else None
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return None


def wait_resources(campaign, deadline, *, sleep=time.sleep, clock=time.monotonic, memory=psutil.virtual_memory, disk=psutil.disk_usage, temperature=gpu_temperature):
    """Two stable launch samples; the worker retains its own live guards."""
    ready, next_sample = 0, 0
    while clock() < deadline and not (campaign.folder / "STOP").exists():
        now = clock()
        if now >= next_sample:
            ram = memory().available / 1024**2
            free = disk(str(campaign.root)).free / 1024**2
            thermal = temperature()
            ready = ready + 1 if (ram >= campaign.config["checker"]["launch_ram_mib"] and free >= 2048
                                  and (thermal is None or thermal < 75)) else 0
            atomic_json(campaign.folder / "supervisor.json", {"status": "ready" if ready >= 2 else "waiting_resources",
                "available_ram_mib": ram, "free_disk_mib": free, "gpu_temperature_c": thermal, "ready_samples": ready,
                "official_training_worlds": 0})
            if ready >= 2:
                return True
            next_sample = now + 30
        sleep(min(1, max(0, deadline-clock())))
    return False


def repeated_failure(campaign, split, condition):
    if condition != "trained":
        return False
    size = campaign.config["checker"]["failure_window"]
    rows = [a for a in campaign.state["attempts"] if a["status"] == "committed"
            and a["split"] == split and a["condition"] == condition][-size:]
    return len(rows) == size and sum(not row["success"] for row in rows) >= campaign.config["checker"]["failure_limit"]


def classify(campaign, outcome):
    if outcome["status"] == "committed":
        return "continue"
    if outcome.get("checker_status") != "technical_stop":
        return "needs_attention"
    report = json.loads(Path(outcome["checker_report"]).read_text())
    if report["stop_reason"] not in ("available_ram_guard", "free_disk_guard", "gpu_temperature_guard", "wall_budget"):
        return "paused"
    failures = 0
    for row in reversed(campaign.state["attempts"]):
        if row["status"] == "committed":
            break
        failures += 1
    return "retry" if failures <= campaign.config["checker"]["technical_retries"] else "needs_attention"


def supervise(campaign, args):
    if not campaign.config.get("checker"):
        raise ValueError("Initialize a new --checked development campaign first")
    if (campaign.config.get("stage") != "development" or campaign.config.get("official_experiment_authorized") is not False
            or not 1 <= campaign.config["world_limit"] <= 100):
        raise ValueError("This supervisor permits only development campaigns of at most 100 worlds")
    if (campaign.folder / "fix_request.json").exists():
        print(json.dumps({"status": "needs_attention", "fix_request": str(campaign.folder / "fix_request.json")}), flush=True)
        return 2
    deadline = time.monotonic() + args.seconds
    recorder = BackgroundRecorder(args.obs_control_dir, campaign.folder / "recorder")
    worker = None
    try:
        recovered = campaign.recover()
        if recovered:
            recovered_action = classify(campaign, recovered)
            if recovered_action == "needs_attention":
                request_fix(campaign.folder, recovered.get("error", "Recovered attempt requires inspection"), attempt=recovered)
                return 2
            if recovered_action == "paused":
                return 0
        for _ in range(args.max_attempts):
            if (campaign.folder / "STOP").exists() or time.monotonic() + 180 >= deadline:
                break
            if sum(a.get("generated_world_instances") or 0 for a in campaign.state["attempts"]) >= campaign.config["world_limit"]:
                break
            if not wait_resources(campaign, deadline-180):
                break
            attempt = campaign.begin(args.split, args.condition, runtime_root=args.work_dir)
            if attempt["video_required"]:
                recorder.ensure_ready(lambda: (campaign.folder / "STOP").exists())
            remaining = min(args.worker_seconds, int(deadline-time.monotonic())-10)
            if remaining < 120:
                raise RuntimeError("Insufficient batch time remains after recorder preparation; no worker launched")
            results = ROOT / "experiments/phase9" / attempt["run_id"]
            with (campaign.folder / (attempt["run_id"] + ".log")).open("x", encoding="utf-8") as output:
                worker = subprocess.Popen(worker_command(campaign, attempt, args, remaining), cwd=ROOT,
                    stdout=output, stderr=subprocess.STDOUT, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                owner = psutil.Process(worker.pid)
                campaign.state["attempts"][campaign.state["active_attempt"]].update(
                    worker_pid=worker.pid, worker_created=owner.create_time())
                campaign.save()
                while worker.poll() is None:
                    if time.monotonic() >= deadline:
                        (campaign.folder / "STOP").touch(exist_ok=True)
                    dashboard(campaign, "checked development batch running", results)
                    time.sleep(2)
            outcome = campaign.recover()
            action = classify(campaign, outcome)
            dashboard(campaign, action, results)
            print(json.dumps({"run_id": attempt["run_id"], "decision": action, "success": outcome.get("success"),
                              "checker_report": outcome.get("checker_report"), "error": outcome.get("error")}), flush=True)
            if action == "needs_attention" or repeated_failure(campaign, args.split, args.condition):
                request_fix(campaign.folder, outcome.get("error", "At least nine verified failures in ten trained episodes"),
                            code=outcome.get("checker_error_code", "repeated_policy_failure"), attempt=outcome)
                return 2
            if action == "paused":
                break
        atomic_json(campaign.folder / "supervisor.json", {"status": "paused" if (campaign.folder / "STOP").exists() else "batch_finished",
                    "official_training_worlds": 0, "summary": campaign.summary()})
        dashboard(campaign, "checked batch paused" if (campaign.folder / "STOP").exists() else "checked batch finished")
        return 0
    except (Exception, KeyboardInterrupt) as error:
        if worker is not None and worker.poll() is None:
            (campaign.folder / "STOP").touch(exist_ok=True)
            try:
                worker.wait(timeout=40)
            except subprocess.TimeoutExpired:
                # Its parent ownership / STOP guard remains active; do not spawn another worker.
                request_fix(campaign.folder, "Owned worker did not acknowledge STOP within 40 seconds", code="worker_shutdown")
                return 2
        if campaign.state["active_attempt"] is not None:
            campaign.recover()
        if isinstance(error, KeyboardInterrupt) or (campaign.folder / "STOP").exists():
            atomic_json(campaign.folder / "supervisor.json", {"status": "paused", "official_training_worlds": 0})
            return 130
        request_fix(campaign.folder, error, code=getattr(error, "code", "supervisor_error"),
                    attempt=campaign.state["attempts"][-1] if campaign.state["attempts"] else None)
        return 2
    finally:
        recorder.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    audit = commands.add_parser("audit", help="Read-only audit of existing logs and milestone MP4s")
    audit.add_argument("--runs", nargs="+", type=Path, required=True)
    audit.add_argument("--output", type=Path, required=True)
    run = commands.add_parser("run", help="Run a bounded checked development batch")
    run.add_argument("--campaign", type=Path, required=True)
    run.add_argument("--split", choices=("pilot", "eval_a"), default="eval_a")
    run.add_argument("--condition", choices=("trained", "frozen", "uniform", "no_neural", "shuffled"), default="trained")
    run.add_argument("--max-attempts", type=int, default=5)
    run.add_argument("--seconds", type=int, default=1800)
    run.add_argument("--worker-seconds", type=int, default=240)
    for name in ("work-dir", "build-dir", "obs-control-dir"):
        run.add_argument("--" + name, type=Path, required=True)
    run.add_argument("--video-export-dir", type=Path)
    args = parser.parse_args()
    if args.command == "audit":
        if args.output.exists():
            parser.error("audit output must be new")
        reports, errors = [], []
        for directory in args.runs:
            try:
                reports.append(audit_run(directory))
            except (OSError, ValueError, KeyError, TypeError) as error:
                errors.append({"run": str(directory), "code": getattr(error, "code", "evidence_schema"), "error": str(error)})
        atomic_json(args.output, {"reports": reports, "errors": errors, "read_only": True})
        print(json.dumps({"runs": len(reports), "episodes": sum(len(r["episodes"]) for r in reports), "errors": errors}))
        return 2 if errors else 0
    if not 1 <= args.max_attempts <= 100 or not 120 <= args.seconds <= 3600 or not 120 <= args.worker_seconds <= 300:
        parser.error("development only: 1–100 launches, 120–3600 batch seconds, 120–300 worker seconds")
    acquired = False
    try:
        with CampaignLock(args.campaign):
            acquired = True
            campaign = Campaign(args.campaign, project_root=ROOT)
            return supervise(campaign, args)
    except (OSError, ValueError, RuntimeError) as error:
        if acquired and args.campaign.is_dir():
            request_fix(args.campaign, error, code="campaign_preflight")
        else:
            print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
