"""Run only the predeclared Phase 8 control sample on the frozen interface."""

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
from experiments.phase9.phase8_finish_20261124.score_controls import score, CONDITIONS, FROZEN_SHA

FOLDER = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--stop-file", type=Path, required=True)
    args = parser.parse_args()
    args.work_dir.mkdir(parents=True, exist_ok=True)
    plan = json.loads((FOLDER / "heldout_plan.json").read_text())
    block = plan["blocks"][0]
    checkpoint = ROOT / plan["policy"]["checkpoint"]
    frozen = ROOT / "checkpoints/phase7/curriculum_v3_seed29.npz"
    assert hashlib.sha256(checkpoint.read_bytes()).hexdigest() == plan["policy"]["sha256"]
    assert hashlib.sha256(frozen.read_bytes()).hexdigest() == FROZEN_SHA
    assert source_manifest(ROOT)["implementation_sha256"] == plan["implementation_sha256"]
    parent = psutil.Process(os.getpid())
    for goal in ("one_log", "wooden_pickaxe"):
        batches = [block["layout_seeds"][:3]] if goal == "one_log" else [[seed] for seed in block["layout_seeds"][:3]]
        for batch_index, layouts in enumerate(batches, 1):
            if args.stop_file.exists():
                return
            run_id = f"p8_control_20261124_{goal}_b{batch_index}"
            directory = FOLDER.parent / run_id
            if directory.exists():
                result = score()
                meta = json.loads((directory / "run.json").read_text())
                if meta["completed"] != len(layouts) * len(CONDITIONS):
                    raise RuntimeError(f"Partial control block needs inspection: {run_id}")
                continue
            ready = 0
            while ready < 2:
                if args.stop_file.exists():
                    return
                available = psutil.virtual_memory().available / 1024**2
                ready = ready + 1 if available >= 1800 else 0
                print(json.dumps({"available_ram_mib": round(available), "ready_samples": ready}), flush=True)
                if ready < 2:
                    time.sleep(30)
            command = [sys.executable, str(ROOT / "tools/run_phase8_live.py"), "--run-id", run_id,
                       "--work-dir", str(args.work_dir / "game"), "--build-dir", str(ROOT / ".runtime/build_reply_loss_20261107"),
                       "--checkpoint", str(checkpoint), "--frozen-checkpoint", str(frozen),
                       "--policy-label", "phase8_frozen_offline_progress_fit", "--headless", "--pitch-actions",
                       "--conditions", ",".join(CONDITIONS), "--goals", goal,
                       "--world-seed", str(block["world_seed"]), "--layout-seeds", ",".join(map(str, layouts)),
                       "--trials", str(len(layouts)), "--trial-ticks", str(plan["goals"][goal]["trial_ticks"]),
                       "--policy-seed", "9001", "--forward-ticks", str(plan["policy"]["forward_ticks"]),
                       "--seconds", "600", "--server-heap-mib", "384", "--stop-file", str(args.stop_file),
                       "--parent-pid", str(parent.pid), "--parent-created", str(parent.create_time())]
            if goal == "wooden_pickaxe":
                command += ["--three-tree-fixture", "--remember-mined-columns"]
            print(json.dumps({"starting_control": run_id, "layouts": layouts}), flush=True)
            with (args.work_dir / (run_id + ".supervisor.log")).open("x") as output:
                run = subprocess.run(command, cwd=ROOT, stdout=output, stderr=subprocess.STDOUT)
            if run.returncode:
                raise RuntimeError(f"Inspect control runner error: {run_id}")
            result = score()
            atomic_json(FOLDER / "control_progress.json", result)
            print(json.dumps({"finished_control": run_id, "groups": result["groups"]}), flush=True)
            if args.stop_file.exists():
                return
            meta = json.loads((directory / "run.json").read_text())
            if meta["stop_reason"] != "suite_complete":
                raise RuntimeError(f"Inspect partial control block before any new attempt: {run_id}")
    result = score()
    assert len(result["groups"]) == 10 and all(value["verified_trials"] == 3 for value in result["groups"].values())
    assert all(pair["absolute_pose_matched"] and pair["fixture_matched"] for pair in result["pairs"])
    assert result["complete"]
    with (FOLDER / "control_results.json").open("x", encoding="utf-8", newline="\n") as output:
        json.dump(result, output, indent=2, allow_nan=False)
        output.write("\n")


if __name__ == "__main__":
    main()
