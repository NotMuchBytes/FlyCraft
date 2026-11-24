"""Predeclared small checker validation, never the official Phase 9 campaign."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from autonomy.experiment import Campaign, atomic_json, source_manifest

FOLDER = Path(__file__).resolve().parent
CHECKPOINT = ROOT / "checkpoints/phase8/finish_20261123/progress_readout_mining.npz"
FROZEN = ROOT / "checkpoints/phase7/curriculum_v3_seed29.npz"
JOBS = [("one", "one_log", 2, "eval_a"), ("three", "three_logs", 1, "eval_a"),
        ("planks", "planks", 1, "eval_a"), ("pick", "wooden_pickaxe", 1, "eval_a"),
        ("stop", "one_log", 1, "eval_a"), ("train", "planks", 2, "pilot")]


def run(campaign, args, attempts, split, *, interrupt=False):
    command = [sys.executable, str(ROOT / "tools/supervise_phase9.py"), "run", "--campaign", str(campaign.folder),
               "--split", split, "--max-attempts", str(attempts), "--seconds", "900",
               "--work-dir", str(args.work_dir / "game"), "--build-dir", str(ROOT / ".runtime/build_reply_loss_20261107"),
               "--obs-control-dir", str(args.obs_control_dir), "--video-export-dir", str(args.export_dir)]
    index = len(campaign.state["attempts"])
    log = FOLDER / f"{campaign.config['name']}_batch_{index:02d}.log"
    with log.open("x", encoding="utf-8", newline="\n") as output:
        child = subprocess.Popen(command, cwd=ROOT, stdout=output, stderr=subprocess.STDOUT,
                                 creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        stopped = False
        deadline = time.monotonic() + 920
        while child.poll() is None:
            if args.stop_file.exists() or time.monotonic() > deadline:
                (campaign.folder / "STOP").touch(exist_ok=True)
            if interrupt and not stopped:
                state = json.loads((campaign.folder / "state.json").read_text())
                if state["attempts"]:
                    latest = state["attempts"][-1]
                    path = ROOT / "experiments/phase9" / latest["run_id"] / "headless.jsonl"
                    lines = path.read_text().splitlines() if path.exists() else []
                    if any('"action":"COLLECT_LOG"' in line and '"event":"action_start"' in line for line in lines):
                        (campaign.folder / "STOP").touch(exist_ok=True)
                        atomic_json(FOLDER / "intentional_stop.json", {"run_id": latest["run_id"],
                            "trigger": "Observed actual mining action_start; no actor inputs were changed",
                            "wall_time_unix": time.time(), "kind": "operator interruption diagnostic, excluded from benchmark"})
                        stopped = True
            time.sleep(.2 if interrupt else 2)
        if child.returncode:
            raise RuntimeError(f"Inspect checker handoff/log before continuing: {log}")
    return Campaign(campaign.folder, project_root=ROOT), stopped


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("work-dir", "obs-control-dir", "export-dir", "stop-file"):
        parser.add_argument("--" + key, type=Path, required=True)
    args = parser.parse_args()
    args.work_dir.mkdir(parents=True, exist_ok=True)
    plan_path = FOLDER / "pilot_plan.json"
    if plan_path.exists():
        raise RuntimeError("Pilot has already been declared; inspect records rather than overwriting/repeating it")
    plan = {"phase": "Phase 9 checker development only", "official_campaign_authorized": False,
            "expected_scored_episodes": 8, "expected_training_episodes": 2,
            "jobs": JOBS, "source": source_manifest(ROOT),
            "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "milestone": "First and only pickaxe evaluation; retain its actual outcome",
            "stop_diagnostic": "Stop during mining, preserve interrupted attempt and resume in a fresh world; never credit an interrupted command",
            "conditions": "trained only; this is functional validation, not a policy comparison or reliability benchmark"}
    atomic_json(plan_path, plan)
    summaries = []
    for number, (label, goal, episodes, split) in enumerate(JOBS):
        if args.stop_file.exists():
            return
        name = "checker24_" + label
        campaign = Campaign.create(ROOT / "experiments/phase9" / name, project_root=ROOT, name=name,
            checkpoint=CHECKPOINT, frozen_checkpoint=FROZEN, master=202611249101+number,
            worlds=episodes+2, checked=True, compact=True, forward_ticks=2, goal=goal,
            recording_policy="milestones", recording_milestones=(1,) if label == "pick" else (100,))
        campaign.save()
        print(json.dumps({"starting": name, "goal": goal, "episodes": episodes, "split": split}), flush=True)
        if label == "stop":
            campaign, stopped = run(campaign, args, 1, split, interrupt=True)
            if not stopped:
                raise RuntimeError("Mining interruption did not trigger; retain outcome and inspect")
            subprocess.run([sys.executable, str(ROOT / "tools/run_phase9.py"), "clear-stop", "--campaign", str(campaign.folder)],
                           check=True, cwd=ROOT, capture_output=True)
            # Resume only if the diagnostic never produced a valid scored episode.
            if campaign.summary()["committed_episodes"] == 0 and not args.stop_file.exists():
                campaign, _ = run(campaign, args, 1, split)
        elif label == "one":
            # Separate invocations exercise durable resume without rescoring.
            campaign, _ = run(campaign, args, 1, split)
            if not args.stop_file.exists():
                campaign, _ = run(campaign, args, 1, split)
        else:
            campaign, _ = run(campaign, args, episodes, split)
        summary = campaign.summary()
        if not args.stop_file.exists() and summary["committed_episodes"] != episodes:
            raise RuntimeError(f"Pilot cell incomplete; inspect {campaign.folder}")
        summaries.append({"name": name, "summary": summary, "attempts": campaign.state["attempts"]})
        atomic_json(FOLDER / "pilot_progress.json", {"campaigns": summaries})
        print(json.dumps({"finished": name, "committed": summary["committed_episodes"],
                          "updates": summary["training_updates"]}), flush=True)
    atomic_json(FOLDER / "pilot_results.json", {"complete": len(summaries) == len(JOBS), "campaigns": summaries,
                "official_training_worlds": 0, "source_sha256": plan["source"]["implementation_sha256"]})


if __name__ == "__main__":
    main()
