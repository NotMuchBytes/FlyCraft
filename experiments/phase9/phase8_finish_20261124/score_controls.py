"""Audit the predeclared small matched control sample, separate from primary scores."""

from collections import defaultdict
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from experiments.phase9.phase75_reliability_20261117.audit import audit, summarize

FOLDER = Path(__file__).resolve().parent
CONDITIONS = ("trained", "frozen", "uniform", "no_neural", "shuffled")
FROZEN_SHA = "a2b86d257882ebbd0faf7011588a30e91039e255ce3e3eb624985db82cc81ba6"


def score():
    plan = json.loads((FOLDER / "heldout_plan.json").read_text())
    block = plan["blocks"][0]
    layouts = set(block["layout_seeds"][:3])
    groups, indexed, runs = defaultdict(list), {}, []
    for directory in sorted(FOLDER.parent.glob("p8_control_20261124_*")):
        if not (directory / "run.json").exists():
            raise RuntimeError(f"Inspect unfinished control attempt: {directory}")
        meta = json.loads((directory / "run.json").read_text())
        goal, = meta["goals"]
        assert goal in ("one_log", "wooden_pickaxe")
        expected = {key: plan["policy"][key] for key in (
            "camera_mode", "turn_degrees", "pitch_actions", "forward_ticks", "policy_rng_seed",
            "movement_feedback", "jump_on_blocked_forward", "explore_forward")}
        expected.update(world_seed=block["world_seed"], conditions=list(CONDITIONS), train=False,
                        checkpoint_sha256=plan["policy"]["sha256"], frozen_checkpoint_sha256=FROZEN_SHA,
                        implementation_sha256=plan["implementation_sha256"], headless=True, spectator=False,
                        trial_tick_limit=plan["goals"][goal]["trial_ticks"],
                        remember_mined_columns=goal == "wooden_pickaxe",
                        environment_kind="controlled_flat_three_tree_fixture" if goal == "wooden_pickaxe"
                                         else "controlled_flat_survival_fixture")
        assert all(meta.get(key) == value for key, value in expected.items()), directory.name
        assert set(meta["layout_seeds"]) <= layouts
        report = audit(directory.name)
        runs.append({"run_id": directory.name, "stop_reason": meta["stop_reason"],
                     "scored": len(report["episodes"]), "requested": report["requested"]})
        for row in report["episodes"]:
            key = row["goal"], row["layout_seed"], row["condition"]
            assert key not in indexed, f"Duplicate control cell: {key}"
            assert row["verified"] and row["actions"] <= 120
            target = "wooden_pickaxe" if goal == "wooden_pickaxe" else "log"
            assert row["success"] == (row["inventory"][target] >= 1)
            if row["success"]:
                assert row["confirmed_breaks"] >= (3 if goal == "wooden_pickaxe" else 1)
                if goal == "wooden_pickaxe":
                    assert all(row["confirmed_crafting_and_placement"].get(action) for action in
                               ("CRAFT_PLANKS", "CRAFT_STICKS", "CRAFT_TABLE", "PLACE_TABLE", "CRAFT_PICKAXE"))
            row = row | {"run_id": directory.name}
            indexed[key] = row
            groups[f"{goal}/{row['condition']}"].append(row)
    pairs = []
    for (goal, seed, condition), row in indexed.items():
        baseline = indexed.get((goal, seed, "trained"))
        if condition == "trained" or baseline is None:
            continue
        same_pose = baseline["initial"]["position_xyz_yaw_pitch"] == row["initial"]["position_xyz_yaw_pitch"]
        same_fixture = baseline["initial"]["fixture_blocks"] == row["initial"]["fixture_blocks"]
        pairs.append({"goal": goal, "layout_seed": seed, "condition": condition,
                      "absolute_pose_matched": same_pose, "fixture_matched": same_fixture,
                      "trained_success": baseline["strict_success"], "control_success": row["strict_success"]})
    return {"sample_kind": "predeclared control repeats, excluded from primary 30-trial scores",
            "interval_note": "Descriptive Wilson intervals for three layouts in one world seed; no neural-benefit claim",
            "groups": {key: summarize(value) for key, value in groups.items()},
            "pairs": pairs, "runs": runs, "episodes": dict(groups)}


if __name__ == "__main__":
    result = score()
    with (FOLDER / "control_results.json").open("x", encoding="utf-8", newline="\n") as output:
        json.dump(result, output, indent=2, allow_nan=False)
        output.write("\n")
    print(json.dumps(result["groups"], indent=2))
