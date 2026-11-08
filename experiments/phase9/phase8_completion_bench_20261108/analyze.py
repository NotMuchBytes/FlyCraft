"""Summarize scored trials against the fixed Phase 8 completion plan."""
import collections
import json
from pathlib import Path
import statistics
import sys

FOLDER = Path(__file__).resolve().parent
sys.path.insert(0, str(FOLDER.parents[2]))
from tools.analyze_phase8 import wilson


def rows(folder, name):
    path = folder / name
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def main():
    plan = json.loads((FOLDER / "plan.json").read_text(encoding="utf-8"))
    goals = plan["settings"]["goals"]
    episodes, blocks = [], []
    parents = {block["run_id"]: block for block in plan["blocks"]}
    retry_file = FOLDER / "retries.json"
    retries = json.loads(retry_file.read_text(encoding="utf-8")) if retry_file.is_file() else []
    runs = plan["blocks"].copy()
    for retry in retries:
        parent = parents[retry["parent"]]
        assert retry["layout_seed"] in parent["layout_seeds"] and retry["goal"] in goals
        runs.append({"run_id": retry["run_id"], "world_seed": parent["world_seed"],
                     "layout_seeds": [retry["layout_seed"]], "goals": [retry["goal"]],
                     "retry_of": parent["run_id"]})
    scored_pairs = set()
    for block in runs:
        folder = FOLDER.parent / block["run_id"]
        manifest = folder / "run.json"
        if not manifest.is_file():
            continue
        run = json.loads(manifest.read_text(encoding="utf-8"))
        assert run["implementation_sha256"] == plan["implementation_sha256"]
        assert run["checkpoint_sha256"] == plan["checkpoint"]["sha256"]
        assert run["world_seed"] == block["world_seed"] and run["layout_seeds"] == block["layout_seeds"]
        run_goals = block.get("goals", goals)
        assert run["goals"] == run_goals and not run["train"]
        if "retry_of" in block:
            assert run["redo_of"] == block["retry_of"]
        assert run["trial_tick_limit"] == plan["settings"]["trial_ticks"]
        assert run["policy_rng_seed"] == plan["settings"]["policy_seed"]
        assert run["forward_ticks"] == plan["settings"]["forward_ticks"]
        assert run["remember_mined_columns"] and run["environment_kind"] == "controlled_flat_three_tree_fixture"
        deliveries = {row["episode_id"]: row for row in rows(folder, "server.jsonl.delivery.jsonl")}
        controller = {row["episode_id"]: row for row in rows(folder, "controller.jsonl")}
        completed_actions = collections.defaultdict(set)
        for event in rows(folder, "headless.jsonl"):
            if event["event"] == "action_end" and event["data"]["ack"]["status"] == "success":
                completed_actions[event["episode_id"]].add(event["data"]["ack"]["action"])
        expected = [(seed, goal) for seed in block["layout_seeds"] for goal in run_goals]
        scores = rows(folder, "server.jsonl")
        assert [(row["layout_seed"], row["goal"]) for row in scores] == expected[:len(scores)]
        blocks.append({"run_id": block["run_id"], "world_seed": block["world_seed"],
                       "requested": len(expected), "scored": len(scores), "stop_reason": run["stop_reason"]})
        for score in scores:
            identity = (block["world_seed"], score["layout_seed"], score["goal"])
            assert identity not in scored_pairs
            scored_pairs.add(identity)
            own = score["inventory"]
            ctrl = controller.get(score["episode_id"], {})
            threshold = own["log"] >= 3 if score["goal"] == "three_logs" else own["wooden_pickaxe"] >= 1
            assert score["success"] == threshold and score["condition"] == "trained"
            recorded_inventory = ctrl.get("terminal_inventory")
            verified = (deliveries.get(score["episode_id"], {}).get("acknowledged", False)
                        and (recorded_inventory is None
                             or all(recorded_inventory.get(key) == value for key, value in own.items())))
            failure_stage = None
            if not threshold:
                confirmed = completed_actions[score["episode_id"]]
                stages = [("PLACE_TABLE", "table_placed"), ("CRAFT_TABLE", "table_crafted"),
                          ("CRAFT_STICKS", "sticks_crafted"), ("CRAFT_PLANKS", "planks_crafted"),
                          ("COLLECT_LOG", "log_mined")]
                failure_stage = next((stage for action, stage in stages if action in confirmed), "before_mining")
            episodes.append(score | {"run_id": block["run_id"], "verified": verified,
                                     "actions": ctrl.get("actions"),
                                     "failure_stage": failure_stage,
                                     "controller_success": ctrl.get("success"),
                                     "block_changes": ctrl.get("confirmed_block_changes")})
    summary = {}
    for goal in goals:
        valid = [row for row in episodes if row["goal"] == goal and row["verified"]]
        successes = sum(row["success"] for row in valid)
        actions = [row["actions"] for row in valid if row["actions"] is not None]
        failure_inventory = collections.Counter(
            (row["inventory"]["log"] if goal == "three_logs" else row["inventory"]["crafting_table"])
            for row in valid if not row["success"]
        )
        summary[goal] = {
            "successes": successes, "verified_trials": len(valid),
            "wilson_95_descriptive": wilson(successes, len(valid)),
            "median_actions": statistics.median(actions) if actions else None,
            "failed_terminal_log_or_table_counts": dict(sorted(failure_inventory.items())),
            "failed_stages": dict(collections.Counter(row["failure_stage"] for row in valid if not row["success"])),
        }
    result = {"blocks": blocks, "goals": summary, "episodes": episodes}
    (FOLDER / "results.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
