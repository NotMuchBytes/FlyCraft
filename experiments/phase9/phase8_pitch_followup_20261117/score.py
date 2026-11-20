"""Score explicit pitch-candidate runs against the frozen Phase 8 plan."""

import argparse
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys

FOLDER = Path(__file__).resolve().parent
sys.path.insert(0, str(FOLDER.parents[2]))

from experiments.phase9.phase75_reliability_20261117.audit import audit, summarize


def score(run_ids):
    plan = json.loads((FOLDER / "heldout_plan.json").read_text(encoding="utf-8"))
    expected_layouts = {block["world_seed"]: set(block["layout_seeds"]) for block in plan["blocks"]}
    policy = plan["policy"]
    goal_specs = plan["goals"]
    excluded = json.loads((FOLDER / "excluded_runs.json").read_text(encoding="utf-8"))
    run_records = []
    episodes = {goal: [] for goal in goal_specs}
    identities = set()
    implementations = set()
    for run_id in run_ids:
        if run_id in excluded:
            raise ValueError(f"{run_id}: explicitly excluded repeat")
        meta = json.loads((FOLDER.parent / run_id / "run.json").read_text(encoding="utf-8"))
        goals = meta["goals"]
        if (not goals or not set(goals) <= goal_specs.keys()
                or len(goals) != 1 and goals != ["three_logs", "wooden_pickaxe"]):
            raise ValueError(f"{run_id}: incompatible goals in one run")
        world = meta["world_seed"]
        layouts = meta["layout_seeds"]
        long_goal = goals[0] in ("three_logs", "wooden_pickaxe")
        if not layouts or not set(layouts) <= expected_layouts.get(world, set()):
            raise ValueError(f"{run_id}: unexpected seed block")
        expected = {key: policy[key] for key in ("pitch_actions", "camera_mode", "turn_degrees",
                                               "forward_ticks", "movement_feedback", "policy_rng_seed",
                                               "jump_on_blocked_forward", "explore_forward")}
        expected.update(conditions=[policy["condition"]], train=policy["training"], headless=True,
                        spectator=False, environment_kind=("controlled_flat_three_tree_fixture" if long_goal
                                                           else "controlled_flat_survival_fixture"),
                        remember_mined_columns=long_goal, unplaced_table_fixture=False,
                        checkpoint_sha256=policy["sha256"], trial_tick_limit=goal_specs[goals[0]]["trial_ticks"])
        for setting, value in expected.items():
            if meta.get(setting) != value:
                raise ValueError(f"{run_id}: {setting} differs from the plan")
        implementations.add(meta["implementation_sha256"])
        report = audit(run_id)
        order = [(seed, goal) for seed in layouts for goal in goals]
        if [(row["layout_seed"], row["goal"]) for row in report["episodes"]] != order[:len(report["episodes"])]:
            raise ValueError(f"{run_id}: episode order differs from requested layouts")
        run_records.append({key: report[key] for key in ("run", "stop_reason", "requested", "verified_trials")}
                           | {key: meta.get(key) for key in (
                               "server_heap_mib", "elapsed_seconds", "generated_world_instances",
                               "minimum_sampled_available_ram_mib", "maximum_sampled_gpu_c")})
        for row in report["episodes"]:
            goal = row["goal"]
            identity = (goal, world, row["layout_seed"])
            if identity in identities:
                raise ValueError(f"{run_id}: duplicate scored trial {identity}")
            identities.add(identity)
            inventory = row["inventory"]
            target_item, target_count = {"one_log": ("log", 1), "three_logs": ("log", 3),
                                         "planks": ("planks", 4), "wooden_pickaxe": ("wooden_pickaxe", 1)}[goal]
            if row["success"] != (inventory[target_item] >= target_count):
                raise ValueError(f"{run_id}: server success disagrees with its inventory")
            if row["actions"] > policy["policy_action_limit"]:
                raise ValueError(f"{run_id}: policy action budget exceeded")
            if row["success"]:
                recipe_actions = {"planks": ("CRAFT_PLANKS",),
                                  "wooden_pickaxe": ("CRAFT_PLANKS", "CRAFT_STICKS", "CRAFT_TABLE",
                                                     "PLACE_TABLE", "CRAFT_PICKAXE")}.get(goal, ())
                minimum_breaks = 3 if long_goal else 1
                if (row["confirmed_breaks"] < minimum_breaks
                        or any(not row["confirmed_crafting_and_placement"].get(action) for action in recipe_actions)):
                    raise ValueError(f"{run_id}: successful inventory lacks required transaction evidence")
            evidence = {key: value for key, value in row.items() if key != "initial"}
            initial = row["initial"]
            if initial["world_seed"] != world:
                raise ValueError(f"{run_id}: initial world seed disagrees with run metadata")
            origin = [math.floor(value) for value in initial["position_xyz_yaw_pitch"][:3]]
            blocks = sorted((tuple(value - offset for value, offset in zip(block["position"], origin)),
                             block["state"]) for block in initial["fixture_blocks"])
            evidence["relative_fixture_sha256"] = hashlib.sha256(json.dumps(blocks).encode()).hexdigest()
            episodes[goal].append(evidence | {"run_id": run_id, "world_seed": world})
    if len(implementations) > 1:
        raise ValueError("Run set contains more than one implementation hash")

    totals = {}
    for goal, spec in goal_specs.items():
        summary = summarize(episodes[goal])
        verified = [row for row in episodes[goal] if row["verified"]]
        complete = summary["verified_trials"] == spec["trials"]
        totals[goal] = summary | {"scheduled_trials": spec["trials"], "target_successes": spec["success_target"],
                                  "target_met": complete and summary["successes"] >= spec["success_target"],
                                  "complete": complete,
                                  "median_game_seconds": statistics.median(row["game_seconds"] for row in verified) if verified else None,
                                  "distinct_world_seeds": len({row["world_seed"] for row in verified}),
                                  "distinct_relative_fixtures": len({row["relative_fixture_sha256"] for row in verified}),
                                  "failed_after_at_least_three_breaks": sum(
                                      not row["success"] and row["confirmed_breaks"] >= 3 for row in verified)}
    return {"implementation_sha256": next(iter(implementations), None),
            "runs": run_records, "goals": totals, "episodes": episodes}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    results = score(args.runs)
    with args.output.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(results, handle, indent=2, allow_nan=False)
        handle.write("\n")
    print(json.dumps(results["goals"], indent=2))


if __name__ == "__main__":
    main()
