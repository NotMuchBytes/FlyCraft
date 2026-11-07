import json
import math
import statistics
from pathlib import Path

FOLDER = Path(__file__).resolve().parent
ROOT = FOLDER.parent
PLAN = json.loads((FOLDER / "plan.json").read_text())
CONDITIONS = PLAN["blocks"][0]["condition_order"]

def rows(folder, name):
    path = folder / name
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()] if path.is_file() else []

def indexed(folder, name):
    return {row["episode_id"]: row for row in rows(folder, name)}

def wilson(k, n):
    if not n:
        return None
    z = 1.959963984540054
    p = k / n
    denominator = 1 + z ** 2 / n
    midpoint = (p + z ** 2 / (2 * n)) / denominator
    radius = z * math.sqrt(p * (1 - p) / n + z ** 2 / (4 * n ** 2)) / denominator
    return [0.0 if k == 0 else midpoint - radius, 1.0 if k == n else midpoint + radius]

blocks = []
for plan in PLAN["blocks"]:
    folder = ROOT / plan["run_id"]
    run_path = folder / "run.json"
    if not run_path.is_file():
        continue
    run = json.loads(run_path.read_text())
    assert run["implementation_sha256"] == PLAN["implementation_sha256"]
    assert run["checkpoint_sha256"] == PLAN["checkpoint"]["sha256"]
    assert run["frozen_checkpoint_sha256"] == PLAN["frozen_checkpoint"]["sha256"]
    assert run["conditions"] == plan["condition_order"]
    assert run["world_seed"] == plan["world_seed"] and run["layout_start"] == plan["layout_seed"]
    assert run["forward_ticks"] == 2 and run["trial_tick_limit"] == 400 and not run["train"]
    initial = indexed(folder, "server.jsonl.initial.jsonl")
    controller = indexed(folder, "controller.jsonl")
    delivery = indexed(folder, "server.jsonl.delivery.jsonl")
    trace = rows(folder, "headless.jsonl")
    scored = []
    snapshots = []
    for score in rows(folder, "server.jsonl"):
        episode = score["episode_id"]
        ctrl = controller.get(episode, {})
        start = initial[episode]
        snapshots.append((start["position_xyz_yaw_pitch"], start["inventory"], start["fixture_blocks"]))
        actions = [event for event in trace if event["episode_id"] == episode and event["event"] == "action_start"]
        broken = [event for event in trace if event["episode_id"] == episode and event["event"] == "action_end"
                  and event["data"]["ack"].get("block_changed")]
        log_count = score["inventory"]["log"]
        boundary = ctrl.get("terminal_inventory", {}).get("log")
        valid = (delivery.get(episode, {}).get("acknowledged", False)
                 and boundary == log_count and ctrl.get("success") == score["success"]
                 and score["success"] == (log_count >= 1))
        failure = None if score["success"] else "mined_without_pickup" if broken else "no_block_broken"
        scored.append({"condition": score["condition"], "episode_id": episode, "success": score["success"],
                       "inventory_logs": log_count, "ticks": score["ticks"], "action_starts": len(actions),
                       "block_changes": len(broken), "verified": valid,
                       "failure": failure, "controller_termination": ctrl.get("termination")})
    matched = bool(snapshots) and all(snapshot == snapshots[0] for snapshot in snapshots)
    complete = (len(scored) == len(CONDITIONS) and matched and all(row["verified"] for row in scored)
                and [row["condition"] for row in scored] == plan["condition_order"])
    blocks.append({"run_id": plan["run_id"], "world_seed": plan["world_seed"], "layout_seed": plan["layout_seed"],
                   "stop_reason": run["stop_reason"], "matched_initial_snapshots": matched,
                   "eligible_complete_block": complete, "episodes": scored})
complete_blocks = [block for block in blocks if block["eligible_complete_block"]]
by_condition = {}
for condition in CONDITIONS:
    episodes = [row for block in complete_blocks for row in block["episodes"] if row["condition"] == condition]
    k, n = sum(row["success"] for row in episodes), len(episodes)
    by_condition[condition] = {
        "successes": k, "trials": n, "wilson_95": wilson(k, n),
        "median_action_starts": statistics.median(row["action_starts"] for row in episodes) if episodes else None,
        "failure_modes": {kind: sum(row["failure"] == kind for row in episodes)
                          for kind in ("no_block_broken", "mined_without_pickup")},
    }
output = {"complete_matched_blocks": len(complete_blocks), "blocks": blocks, "summary": by_condition}
(FOLDER / "results.json").write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8", newline="\n")
print(json.dumps(by_condition, indent=2))
