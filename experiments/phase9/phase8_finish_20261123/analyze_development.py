"""Audit explicit Phase 8 development variants and their relative fixtures."""

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from experiments.phase9.phase75_reliability_20261117.audit import audit, summarize

FOLDER = Path(__file__).resolve().parent
PHASE = FOLDER.parent
OLD_CHECKPOINT = "acdde37f8d3288764bcaad9dc9eea7c4f916c9894f54a019684fc3f555dd37f5"
CANDIDATES = {
    OLD_CHECKPOINT: "reference",
    "53491b1d8ad80dd5323a6cda6794c992dd248a4f479a80a57b0e75618941b07c": "progress_trained",
    "0dc48b845f66029cd5c5855e1835713a8c0dd6577b1c4901ffa388e0f34f38a4": "mining_trained",
}


def fixture_digest(initial):
    origin = [math.floor(value) for value in initial["position_xyz_yaw_pitch"][:3]]
    blocks = sorted((tuple(value - offset for value, offset in zip(block["position"], origin)), block["state"])
                    for block in initial["fixture_blocks"])
    return hashlib.sha256(json.dumps(blocks).encode()).hexdigest()


def analyze():
    plan = json.loads((FOLDER / "development_plan.json").read_text())
    groups, runs, identities = {}, [], set()
    for directory in sorted(PHASE.iterdir()):
        if not directory.name.startswith(("p8_stride_20261123_", "p8_progress_20261123_", "p8_mining_20261123_")):
            continue
        manifest = directory / "run.json"
        if not manifest.exists():
            continue
        meta = json.loads(manifest.read_text())
        expected = {"world_seed": plan["world_seed"], "pitch_actions": True, "train": False,
                    "camera_mode": "bounded", "turn_degrees": 15, "movement_feedback": "displacement",
                    "policy_rng_seed": 9001, "trial_tick_limit": 1500, "remember_mined_columns": True,
                    "environment_kind": "controlled_flat_three_tree_fixture"}
        for key, value in expected.items():
            if meta.get(key) != value:
                raise ValueError(f"{directory.name}: unexpected {key}")
        if not set(meta["layout_seeds"]) <= set(plan["layout_seeds"]):
            raise ValueError(f"{directory.name}: unexpected development layout")
        kind = CANDIDATES[meta["checkpoint_sha256"]]
        variant = f"{kind}_forward{meta['forward_ticks']}"
        report = audit(directory.name)
        runs.append({"run_id": directory.name, "variant": variant, "stop_reason": meta["stop_reason"],
                     "requested": report["requested"], "scored": len(report["episodes"]),
                     "checkpoint_sha256": meta["checkpoint_sha256"],
                     "implementation_sha256": meta["implementation_sha256"]})
        for row in report["episodes"]:
            identity = variant, row["layout_seed"], row["goal"]
            if identity in identities:
                raise ValueError(f"Duplicate scored development cell {identity}")
            identities.add(identity)
            if not row["verified"] or row["actions"] > 120:
                raise ValueError(f"Unverified or over-budget episode {identity}")
            if row["success"]:
                if row["confirmed_breaks"] < 3:
                    raise ValueError(f"Successful inventory lacks block confirmations {identity}")
                required = ("CRAFT_PLANKS", "CRAFT_STICKS", "CRAFT_TABLE", "PLACE_TABLE", "CRAFT_PICKAXE")
                if row["goal"] == "wooden_pickaxe" and any(
                        not row["confirmed_crafting_and_placement"].get(action) for action in required):
                    raise ValueError(f"Successful pickaxe lacks recipe confirmations {identity}")
            initial = row.pop("initial")
            row.update(run_id=directory.name, relative_fixture_sha256=fixture_digest(initial),
                       absolute_start_pose=initial["position_xyz_yaw_pitch"])
            groups.setdefault(variant, {}).setdefault(row["goal"], []).append(row)
    summaries = {variant: {goal: summarize(episodes) for goal, episodes in goals.items()}
                 for variant, goals in groups.items()}
    paired = []
    reference = groups.get("reference_forward2", {})
    for variant, goals in groups.items():
        if variant == "reference_forward2":
            continue
        for goal, episodes in goals.items():
            baseline = {row["layout_seed"]: row for row in reference.get(goal, [])}
            for row in episodes:
                before = baseline.get(row["layout_seed"])
                if before is None:
                    continue
                paired.append({"variant": variant, "goal": goal, "layout_seed": row["layout_seed"],
                               "relative_fixture_matched": before["relative_fixture_sha256"] == row["relative_fixture_sha256"],
                               "absolute_pose_matched": before["absolute_start_pose"] == row["absolute_start_pose"]})
    return {"stage": "development", "summaries": summaries, "runs": runs, "episodes": groups,
            "paired_fixture_checks": paired, "stops": dict(Counter(run["stop_reason"] for run in runs))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = analyze()
    with args.output.open("x", newline="\n") as output:
        json.dump(result, output, indent=2)
        output.write("\n")
    print(json.dumps(result["summaries"], indent=2))


if __name__ == "__main__":
    main()
