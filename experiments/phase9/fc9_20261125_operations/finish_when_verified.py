"""User-authorized completion shutdown; read-only toward the frozen campaign.

This separate host-operation companion was requested after the training plan
was frozen. It never changes Minecraft, policy, campaign data or source hashes.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def digest(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while block := handle.read(1024 * 1024):
            value.update(block)
    return value.hexdigest()


def completion_ready(folder):
    """A stopped, failed or partially completed campaign cannot trigger shutdown."""
    folder = Path(folder)
    if any((folder / name).exists() for name in ("STOP", "fix_request.json")):
        return False
    config, state, executor = (read(folder / name) for name in ("config.json", "state.json", "executor.json"))
    if config.get("stage") != "official_training" or config.get("world_limit") != 10000 \
            or config.get("official_experiment_authorized") is not True \
            or executor.get("status") != "training_budget_complete" \
            or state.get("active_attempt") is not None or state.get("final_policy") is None:
        return False
    if digest(folder / "config.json") != state["config_sha256"]:
        raise ValueError("completion configuration integrity mismatch")
    if state["final_policy"] != state["current_checkpoint"] or executor["final_checkpoint"] != state["final_policy"]:
        raise ValueError("final checkpoint selection mismatch")
    rows = [a for a in state["attempts"] if a["split"] == "training"]
    if any(type(a.get("generated_world_instances")) is not int or a["generated_world_instances"] not in (0, 1) for a in rows):
        raise ValueError("invalid world count at completion")
    created = [a for a in rows if a["generated_world_instances"] == 1]
    if len(created) != 10000 or sorted(a["official_world_number"] for a in created) != list(range(1, 10001)):
        return False
    catalog = read(folder / "seeds.json")
    if digest(folder / "seeds.json") != config["catalog_sha256"]:
        raise ValueError("seed catalog changed")
    for row in created:
        number = row["official_world_number"]
        if row["world_seed"] != catalog["training"][number - 1] \
                or row["goal"] != config["goal_schedule"][(number - 1) % len(config["goal_schedule"])]:
            raise ValueError("completion seed/goal schedule mismatch")
    for number in config["recording_milestones"]:
        selected = [a for a in created if a["official_world_number"] == number]
        if len(selected) != 1 or selected[0]["status"] != "committed" or not selected[0].get("video_required"):
            raise ValueError(f"missing verified milestone {number}; refusing shutdown")
    return True


def verify_artifacts(folder, ffmpeg):
    config, state = read(folder / "config.json"), read(folder / "state.json")
    for artifact in (config["initial_checkpoint"], config["frozen_checkpoint"],
                     config["checker"]["graph"], state["final_policy"]):
        if digest(artifact["path"]) != artifact["sha256"]:
            raise ValueError("preserved graph/checkpoint integrity mismatch")
    verified, videos = 0, []
    for attempt in state["attempts"]:
        if attempt["status"] != "committed":
            continue
        if attempt.get("checker_status") != "verified":
            raise ValueError("committed episode lacks evidence verification")
        audit = read(attempt["checker_report"])
        implementation = attempt.get("implementation_sha256", config["implementation_sha256"])
        permitted = {config["implementation_sha256"]} | {r["implementation_sha256"] for r in config.get("execution_revisions", [])}
        if audit["status"] != "verified" or audit["run_id"] != attempt["run_id"] \
                or implementation not in permitted or audit["implementation_sha256"] != implementation:
            raise ValueError("episode audit differs from frozen campaign")
        evidence = Path(attempt["results"])
        for name, expected in audit["evidence_sha256"].items():
            if Path(name).name != name or digest(evidence / name) != expected:
                raise ValueError(f"changed episode evidence: {attempt['run_id']}/{name}")
        verified += 1
        if attempt.get("video_required"):
            video = attempt["video"]
            if not all(video.get(key) for key in ("full_decode_verified", "episode_coverage_complete", "visual_content_preflight_verified")) \
                    or digest(video["path"]) != video["sha256"]:
                raise ValueError("milestone video changed or was not verified")
            subprocess.run([str(ffmpeg), "-nostdin", "-v", "error", "-xerror", "-threads", "2",
                "-i", video["path"], "-map", "0:v:0", "-f", "null", "-"],
                check=True, capture_output=True, timeout=300)
            videos.append({"path": video["path"], "sha256": video["sha256"]})
    return {"verified_scored_episodes": verified, "milestone_videos": videos,
            "final_checkpoint": state["final_policy"], "verified_unix": time.time()}


def write(path, payload):
    payload = dict(payload, updated_unix=time.time(), pid=os.getpid())
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    deadline = time.monotonic() + 1
    while True:
        try:
            os.replace(temporary, path)
            return
        except PermissionError:
            if time.monotonic() >= deadline:
                raise
            time.sleep(.01)


def shutdown_after_verification(folder, guard_state, status_path, proof, *, sleep=time.sleep, invoke=subprocess.run):
    # The user can cancel with CANCEL_SHUTDOWN or campaign STOP. Preserve Brave's
    # opportunity to block shutdown: no /f and no OS countdown implying /f.
    for remaining in range(60, 0, -1):
        if (status_path.parent / "CANCEL_SHUTDOWN").exists() or not completion_ready(folder):
            write(status_path, {"status": "shutdown_cancelled", "proof": proof})
            return False
        write(status_path, {"status": "shutdown_countdown", "remaining_seconds": remaining, "proof": proof})
        sleep(1)
    (guard_state / "RELEASE").touch(exist_ok=True)
    for _ in range(10):
        guard = read(guard_state / "status.json")
        if not guard.get("blocks_normal_shutdown"):
            break
        sleep(1)
    else:
        raise ValueError("power guard did not acknowledge release; refusing shutdown")
    if not completion_ready(folder) or (status_path.parent / "CANCEL_SHUTDOWN").exists():
        return False
    write(status_path, {"status": "shutdown_requested", "proof": proof, "forced": False})
    invoke([str(Path(os.environ.get("SystemRoot", "C:/Windows")) / "System32/shutdown.exe"),
            "/s", "/t", "0"], check=True, timeout=10)
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("campaign", "guard-state", "state-dir", "ffmpeg"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--shutdown-on-complete", action="store_true")
    args = parser.parse_args()
    args.state_dir.mkdir(parents=True, exist_ok=True)
    status_path = args.state_dir / "status.json"
    while not (args.state_dir / "CANCEL_SHUTDOWN").exists():
        try:
            if completion_ready(args.campaign):
                write(status_path, {"status": "verifying_completion"})
                proof = verify_artifacts(args.campaign, args.ffmpeg)
                write(args.state_dir / "completion_verification.json", proof)
                if args.shutdown_on_complete:
                    shutdown_after_verification(args.campaign, args.guard_state, status_path, proof)
                else:
                    write(status_path, {"status": "verified_dry_run", "proof": proof})
                return
            write(status_path, {"status": "waiting_for_full_campaign", "shutdown_authorized": args.shutdown_on_complete,
                               "world_target": 10000, "no_shutdown_on_pause_or_error": True})
        except Exception as error:
            write(status_path, {"status": "needs_attention", "error": str(error), "shutdown_requested": False})
            return
        time.sleep(30)
    write(status_path, {"status": "shutdown_cancelled"})


if __name__ == "__main__":
    main()
