"""Resume the frozen 120-episode Phase 8 evaluation; never starts Phase 9."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import psutil

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from autonomy.experiment import atomic_json, source_manifest
from experiments.phase9.phase8_pitch_followup_20261117.score import score

FOLDER = Path(__file__).resolve().parent
PHASE = FOLDER.parent
PREFIX = "p8_gate_20261124_"


def collect(plan):
    run_ids = []
    for directory in sorted(PHASE.glob(PREFIX + "*")):
        if not (directory / "run.json").exists():
            raise RuntimeError(f"Inspect unfinished attempt: {directory}")
        meta = json.loads((directory / "run.json").read_text())
        assert meta["implementation_sha256"] == plan["implementation_sha256"]
        run_ids.append(directory.name)
    result = score(run_ids, plan_folder=FOLDER)
    completed = set()
    for goal, rows in result["episodes"].items():
        for row in rows:
            if not row["verified"]:
                raise RuntimeError(f"Inspect unverified score: {row['run_id']}/{row['episode_id']}")
            completed.add((row["world_seed"], row["layout_seed"], goal))
    atomic_json(FOLDER / "progress.json", result)
    return result, completed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--stop-file", type=Path, required=True)
    parser.add_argument("--launch-ram-mib", type=int, default=1800)
    args = parser.parse_args()
    if args.launch_ram_mib < 1536:
        parser.error("Launch margin must cover the live reserve and owned runtime")
    plan = json.loads((FOLDER / "heldout_plan.json").read_text())
    assert plan["phase"] == 8 and not plan["phase9_campaign_authorized"]
    checkpoint = ROOT / plan["policy"]["checkpoint"]
    assert hashlib.sha256(checkpoint.read_bytes()).hexdigest() == plan["policy"]["sha256"]
    assert source_manifest(ROOT)["implementation_sha256"] == plan["implementation_sha256"]
    args.work_dir.mkdir(parents=True, exist_ok=True)
    parent = psutil.Process(os.getpid())
    for goal_group in (("one_log",), ("three_logs", "wooden_pickaxe"), ("planks",)):
        if goal_group != ("one_log",):
            result, _ = collect(plan)
            if not result["goals"]["one_log"]["target_met"]:
                raise RuntimeError("The 24/30 one-log gate is not met; longer-goal evaluation stays closed")
        for block_index, block in enumerate(plan["blocks"], 1):
            unscored_stops = 0
            while True:
                if args.stop_file.exists():
                    return
                result, completed = collect(plan)
                pending = {}
                for seed in block["layout_seeds"]:
                    missing = tuple(goal for goal in goal_group if (block["world_seed"], seed, goal) not in completed)
                    if missing:
                        pending.setdefault(missing, []).append(seed)
                if not pending:
                    break
                goals, layouts = next(iter(pending.items()))
                long_goal = goals[0] in ("three_logs", "wooden_pickaxe")
                label = "long" if len(goals) == 2 else goals[0]
                attempt = 1
                while (PHASE / f"{PREFIX}b{block_index}_{label}_a{attempt}").exists():
                    attempt += 1
                run_id = f"{PREFIX}b{block_index}_{label}_a{attempt}"
                ready = 0
                while ready < 2:
                    if args.stop_file.exists():
                        return
                    available = psutil.virtual_memory().available / 1024**2
                    ready = ready + 1 if available >= args.launch_ram_mib else 0
                    print(json.dumps({"available_ram_mib": round(available), "ready_samples": ready}), flush=True)
                    if ready < 2:
                        time.sleep(30)
                command = [sys.executable, str(ROOT / "tools/run_phase8_live.py"),
                           "--run-id", run_id, "--work-dir", str(args.work_dir / "game"),
                           "--build-dir", str(ROOT / ".runtime/build_reply_loss_20261107"),
                           "--checkpoint", str(checkpoint), "--policy-label", "phase8_frozen_offline_progress_fit",
                           "--headless", "--pitch-actions", "--forward-ticks", str(plan["policy"]["forward_ticks"]),
                           "--world-seed", str(block["world_seed"]), "--layout-seeds", ",".join(map(str, layouts)),
                           "--trials", str(len(layouts)), "--goals", ",".join(goals), "--policy-seed", "9001",
                           "--trial-ticks", str(plan["goals"][goals[0]]["trial_ticks"]),
                           "--seconds", "900" if long_goal else "300", "--server-heap-mib", "384",
                           "--stop-file", str(args.stop_file), "--parent-pid", str(parent.pid),
                           "--parent-created", str(parent.create_time())]
                if long_goal:
                    command += ["--three-tree-fixture", "--remember-mined-columns"]
                print(json.dumps({"starting": run_id, "goals": goals, "layouts": layouts}), flush=True)
                with (args.work_dir / (run_id + ".supervisor.log")).open("x") as output:
                    run = subprocess.run(command, cwd=ROOT, stdout=output, stderr=subprocess.STDOUT)
                if run.returncode:
                    raise RuntimeError(f"Inspect runner error: {run_id}")
                meta = json.loads((PHASE / run_id / "run.json").read_text())
                result, _ = collect(plan)
                print(json.dumps({"finished": run_id, "stop_reason": meta["stop_reason"],
                                  "goals": {goal: [value["successes"], value["verified_trials"]]
                                            for goal, value in result["goals"].items()}}), flush=True)
                if args.stop_file.exists():
                    return
                if meta["stop_reason"] not in {"suite_complete", "wall_budget", "available_ram_guard"}:
                    raise RuntimeError(f"Inspect technical stop: {run_id}: {meta['stop_reason']}")
                unscored_stops = unscored_stops + 1 if not meta["completed"] else 0
                if unscored_stops >= 3:
                    raise RuntimeError("Three consecutive unscored technical stops; preserve evidence and inspect")
    result, _ = collect(plan)
    assert all(goal["complete"] for goal in result["goals"].values())
    with (FOLDER / "final_results.json").open("x", encoding="utf-8", newline="\n") as output:
        json.dump(result, output, indent=2, allow_nan=False)
        output.write("\n")
    print(json.dumps({"phase8_targets_met": all(goal["target_met"] for goal in result["goals"].values()),
                      "scores": {goal: value["successes"] for goal, value in result["goals"].items()}}), flush=True)


if __name__ == "__main__":
    main()
