"""Freeze a selected Phase 8 readout before drawing fresh held-out seeds."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from autonomy.experiment import source_manifest
from learning.policy import LinearSoftmaxPolicy

FOLDER = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--forward-ticks", type=int, choices=(2, 5), required=True)
    parser.add_argument("--selection-note", required=True)
    args = parser.parse_args()
    if (FOLDER / "heldout_plan.json").exists():
        parser.error("The plan is already frozen")
    checkpoint = args.checkpoint.resolve()
    policy, _ = LinearSoftmaxPolicy.load(checkpoint)
    assert policy.weights.shape == (66, 12)
    used = set()
    for path in (ROOT / "experiments/phase9").glob("*/run.json"):
        meta = json.loads(path.read_text(encoding="utf-8"))
        if "world_seed" in meta:
            used.add(meta["world_seed"])
        used.update(meta.get("layout_seeds", []))
    nonce = 0

    def seed():
        nonlocal nonce
        while True:
            value = int.from_bytes(hashlib.sha256(
                f"FlyCraft-phase8-heldout-20261124:{nonce}".encode()).digest()[:8], "big") & ((1 << 63) - 1)
            nonce += 1
            if value not in used:
                used.add(value)
                return value

    plan = {
        "state": "frozen before first held-out episode",
        "phase": 8,
        "selection_note": args.selection_note,
        "phase9_campaign_authorized": False,
        "git_commit_at_freeze": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "implementation_sha256": source_manifest(ROOT)["implementation_sha256"],
        "policy": {
            "checkpoint": checkpoint.relative_to(ROOT).as_posix(),
            "sha256": hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
            "policy_rng_seed": 9001, "policy_action_limit": 120,
            "condition": "trained", "training": False, "pitch_actions": True,
            "camera_mode": "bounded", "turn_degrees": 15, "forward_ticks": args.forward_ticks,
            "movement_feedback": "displacement", "jump_on_blocked_forward": False, "explore_forward": False,
        },
        "goals": {
            goal: {"trials": 30, "success_target": target, "trial_ticks": ticks}
            for goal, target, ticks in (("one_log", 24, 400), ("three_logs", 21, 1500),
                                        ("planks", 21, 400), ("wooden_pickaxe", 15, 1500))
        },
        "environment": "Disposable flat survival fixtures; empty inventory. Three trees and mined-column memory only for longer goals.",
        "dependence": "Five relative layouts per generated world; Wilson intervals are descriptive, not adjusted for shared world clusters.",
        "gate": "Complete one_log first. Release the longer goals only at 24/30 verified one-log successes.",
        "seed_derivation": "SHA256 FlyCraft-phase8-heldout-20261124:nonce, first 8 bytes, signed63, excluding every previously recorded world/layout seed",
        "blocks": [{"world_seed": seed(), "layout_seeds": [seed() for _ in range(5)]} for _ in range(6)],
    }
    with (FOLDER / "heldout_plan.json").open("x", encoding="utf-8", newline="\n") as output:
        json.dump(plan, output, indent=2)
        output.write("\n")
    with (FOLDER / "excluded_runs.json").open("x", encoding="utf-8", newline="\n") as output:
        output.write("[]\n")
    print(json.dumps({"frozen_checkpoint": plan["policy"]["sha256"], "fresh_seed_pairs": 30}))


if __name__ == "__main__":
    main()
