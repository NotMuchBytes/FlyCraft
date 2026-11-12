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


def bridge_trace(folder):
    offers = collections.Counter()
    selections = collections.Counter()
    outcomes = collections.defaultdict(collections.Counter)
    terminal_inventories = {}
    for row in rows(folder, "bridge.jsonl"):
        request = json.loads(row["request"])
        control = request.get("control", {})
        episode = control.get("episode_id")
        response = row.get("response") or {}
        terminal = control.get("terminal")
        if terminal and response.get("terminal_acknowledged"):
            terminal_inventories[episode] = terminal["inventory"]
        if control.get("goal") != "wooden_pickaxe" or not control.get("active"):
            continue
        if "PLACE_TABLE" in request.get("telemetry", {}).get("allowed_actions", []):
            offers[episode] += 1
        if response.get("action") == "PLACE_TABLE" and response.get("command_id") is not None:
            selections[episode] += 1
    for row in rows(folder, "headless.jsonl"):
        ack = row["data"].get("ack", {})
        if ack.get("action") == "PLACE_TABLE":
            outcomes[row["episode_id"]][ack.get("error") or ack["status"]] += 1
    return terminal_inventories, offers, selections, outcomes


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
        layout_seeds = retry["layout_seeds"] if "layout_seeds" in retry else [retry["layout_seed"]]
        retry_goals = retry["goals"] if "goals" in retry else [retry["goal"]]
        assert layout_seeds and set(layout_seeds) <= set(parent["layout_seeds"])
        assert retry_goals and retry_goals == [goal for goal in goals if goal in retry_goals]
        runs.append({"run_id": retry["run_id"], "world_seed": parent["world_seed"],
                     "layout_seeds": layout_seeds, "goals": retry_goals,
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
        settings = plan["settings"]
        assert run["goals"] == run_goals and run["train"] == settings["training"]
        assert run["conditions"] == [settings["condition"]] and run["headless"]
        if "retry_of" in block:
            assert run["redo_of"] == block["retry_of"]
        assert run["trial_tick_limit"] == settings["trial_ticks"]
        assert run["policy_rng_seed"] == settings["policy_seed"]
        for key in ("forward_ticks", "camera_mode", "turn_degrees", "movement_feedback", "remember_mined_columns"):
            assert run[key] == settings[key], (run["run_id"], key)
        assert run["environment_kind"] == "controlled_flat_three_tree_fixture" and not run["unplaced_table_fixture"]
        deliveries = {row["episode_id"]: row for row in rows(folder, "server.jsonl.delivery.jsonl")}
        controller = {row["episode_id"]: row for row in rows(folder, "controller.jsonl")}
        completed_actions = collections.defaultdict(set)
        for event in rows(folder, "headless.jsonl"):
            if event["event"] == "action_end" and event["data"]["ack"]["status"] == "success":
                completed_actions[event["episode_id"]].add(event["data"]["ack"]["action"])
        expected = [(seed, goal) for seed in block["layout_seeds"] for goal in run_goals]
        scores = rows(folder, "server.jsonl")
        assert [(row["layout_seed"], row["goal"]) for row in scores] == expected[:len(scores)]
        bridge_inventory, offers, selections, outcomes = bridge_trace(folder)
        blocks.append({"run_id": block["run_id"], "world_seed": block["world_seed"],
                       "requested": len(expected), "scored": len(scores), "stop_reason": run["stop_reason"]})
        for score in scores:
            identity = (block["world_seed"], score["layout_seed"], score["goal"])
            assert identity not in scored_pairs
            scored_pairs.add(identity)
            own = score["inventory"]
            ctrl = controller.get(score["episode_id"], {})
            threshold = own["log"] >= 3 if score["goal"] == "three_logs" else own["wooden_pickaxe"] >= 1
            assert score["success"] == threshold and score["condition"] == settings["condition"]
            recorded_inventory = ctrl.get("terminal_inventory")
            inventory_evidence = "controller"
            if recorded_inventory is None:
                recorded_inventory = bridge_inventory.get(score["episode_id"])
                inventory_evidence = "acknowledged_bridge_packet" if recorded_inventory is not None else None
            verified = (deliveries.get(score["episode_id"], {}).get("acknowledged", False)
                        and recorded_inventory is not None
                        and all(recorded_inventory.get(key) == value for key, value in own.items()))
            failure_stage = None
            if not threshold:
                confirmed = completed_actions[score["episode_id"]]
                stages = [("PLACE_TABLE", "table_placed"), ("CRAFT_TABLE", "table_crafted"),
                          ("CRAFT_STICKS", "sticks_crafted"), ("CRAFT_PLANKS", "planks_crafted"),
                          ("COLLECT_LOG", "log_mined")]
                failure_stage = next((stage for action, stage in stages if action in confirmed), "before_mining")
            episodes.append(score | {"run_id": block["run_id"], "verified": verified,
                                     "actions": ctrl.get("actions"),
                                     "terminal_inventory_evidence": inventory_evidence,
                                     "failure_stage": failure_stage,
                                     "controller_success": ctrl.get("success"),
                                     "block_changes": ctrl.get("confirmed_block_changes")})
            if score["goal"] == "wooden_pickaxe":
                episode = score["episode_id"]
                episodes[-1]["table_placement"] = {
                    "bridge_offers": offers[episode], "bridge_selections": selections[episode],
                    "minecraft_outcomes": dict(outcomes[episode]),
                }
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
            "median_game_ticks": statistics.median(row["ticks"] for row in valid) if valid else None,
            "failed_terminal_log_or_table_counts": dict(sorted(failure_inventory.items())),
            "failed_stages": dict(collections.Counter(row["failure_stage"] for row in valid if not row["success"])),
        }
    result = {"blocks": blocks, "goals": summary, "episodes": episodes}
    (FOLDER / "results.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
