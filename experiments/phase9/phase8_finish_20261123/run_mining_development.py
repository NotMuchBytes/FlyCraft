"""Resume only unscored cells of the corrected Phase 8 development pilot."""

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
PHASE = ROOT / "experiments/phase9"
CHECKPOINT = ROOT / "checkpoints/phase8/finish_20261123/progress_readout_mining.npz"
CHECKPOINT_SHA = "0dc48b845f66029cd5c5855e1835713a8c0dd6577b1c4901ffa388e0f34f38a4"
LAYOUTS = (728310449, 461992637, 890173251)
GOALS = ("three_logs", "wooden_pickaxe")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--forward-ticks", type=int, choices=(2, 5), default=2)
    parser.add_argument("--stop-file", type=Path, required=True)
    args = parser.parse_args()
    assert hashlib.sha256(CHECKPOINT.read_bytes()).hexdigest() == CHECKPOINT_SHA
    args.work_dir.mkdir(parents=True, exist_ok=True)
    parent = psutil.Process(os.getpid())
    prefix = f"p8_mining_20261123_stride{args.forward_ticks}_"
    for attempt in range(1, 21):
        if args.stop_file.exists():
            return
        completed = set()
        for directory in PHASE.glob(prefix + "*"):
            manifest = directory / "run.json"
            if not manifest.exists():
                raise RuntimeError(f"Inspect unfinished attempt before resuming: {directory}")
            meta = json.loads(manifest.read_text())
            assert meta["checkpoint_sha256"] == CHECKPOINT_SHA
            assert meta["world_seed"] == 202611230801
            assert meta["forward_ticks"] == args.forward_ticks
            scores = directory / "server.jsonl"
            for line in scores.read_text().splitlines() if scores.exists() else []:
                score = json.loads(line)
                identity = score["layout_seed"], score["goal"]
                assert identity not in completed, f"Duplicate scored cell: {identity}"
                completed.add(identity)
        pending = {}
        for seed in LAYOUTS:
            missing = tuple(goal for goal in GOALS if (seed, goal) not in completed)
            if missing:
                pending.setdefault(missing, []).append(seed)
        if not pending:
            print(json.dumps({"development_complete": True, "scored": len(completed)}), flush=True)
            return
        run_id = prefix + f"a{attempt}"
        if (PHASE / run_id).exists():
            continue
        goals, seeds = next(iter(pending.items()))
        ready_samples = 0
        while ready_samples < 2:
            if args.stop_file.exists():
                return
            available = psutil.virtual_memory().available / 1024**2
            ready_samples = ready_samples + 1 if available >= 2400 else 0
            print(json.dumps({"available_ram_mib": round(available), "ready_samples": ready_samples}), flush=True)
            if ready_samples < 2:
                time.sleep(30)
        command = [sys.executable, str(ROOT / "tools/run_phase8_live.py"),
                   "--run-id", run_id, "--work-dir", str(args.work_dir / "game"),
                   "--build-dir", str(ROOT / ".runtime/build_reply_loss_20261107"),
                   "--checkpoint", str(CHECKPOINT), "--policy-label", "offline_progress_and_confirmed_breaks",
                   "--headless", "--pitch-actions", "--three-tree-fixture", "--remember-mined-columns",
                   "--world-seed", "202611230801", "--layout-seeds", ",".join(map(str, seeds)),
                   "--trials", str(len(seeds)), "--goals", ",".join(goals), "--policy-seed", "9001",
                   "--trial-ticks", "1500", "--seconds", "900", "--server-heap-mib", "384",
                   "--forward-ticks", str(args.forward_ticks), "--stop-file", str(args.stop_file),
                   "--parent-pid", str(parent.pid), "--parent-created", str(parent.create_time())]
        print(json.dumps({"starting": run_id, "layouts": seeds, "goals": goals}), flush=True)
        with (args.work_dir / (run_id + ".supervisor.log")).open("x") as output:
            result = subprocess.run(command, cwd=ROOT, stdout=output, stderr=subprocess.STDOUT)
        if result.returncode:
            raise RuntimeError(f"Inspect runner failure: {run_id}")
        meta = json.loads((PHASE / run_id / "run.json").read_text())
        print(json.dumps({"finished": run_id, "completed": meta["completed"],
                          "stop_reason": meta["stop_reason"]}), flush=True)
        if meta["stop_reason"] not in {"suite_complete", "available_ram_guard", "wall_budget"}:
            raise RuntimeError(f"Inspect technical stop: {run_id}: {meta['stop_reason']}")
    raise RuntimeError("Development pilot still incomplete after twenty attempts")


if __name__ == "__main__":
    main()
