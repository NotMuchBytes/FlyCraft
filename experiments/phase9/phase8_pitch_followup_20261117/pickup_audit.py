"""Trace policy decisions after the final confirmed break in failed three-log trials."""

import argparse
import json
from collections import Counter
from pathlib import Path

FOLDER = Path(__file__).resolve().parent
PHASE = FOLDER.parent


def rows(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def failed_pickups(episodes):
    result = []
    for episode in episodes:
        if episode["goal"] != "three_logs" or episode["success"]:
            continue
        folder = PHASE / episode["run_id"]
        episode_id = episode["episode_id"]
        acknowledgments = {row["data"]["ack"]["command_id"]: row["data"]["ack"]
                           for row in rows(folder / "headless.jsonl")
                           if row["episode_id"] == episode_id and row["event"] == "action_end"}
        breaks = [ack for ack in acknowledgments.values()
                  if ack["action"] == "COLLECT_LOG" and ack["status"] == "success" and ack["block_changed"]]
        if len(breaks) < 3:
            continue
        final_command = breaks[-1]["command_id"]
        decisions = []
        for reply in rows(folder / "bridge.jsonl"):
            response = reply.get("response") or {}
            if response.get("episode_id") != episode_id or response.get("command_id", 0) <= final_command:
                continue
            request = json.loads(reply["request"])
            seen = request["telemetry"]
            decisions.append({
                "tick": request["tick_id"], "command_id": response["command_id"],
                "action": response["action"], "target_id": seen["target_id"],
                "target_kind": seen["target_kind"], "distance": seen["target_distance"],
                "pitch_error": seen.get("target_pitch_error"),
            })
        drops = [decision for decision in decisions if decision["target_kind"] == "drop"]
        first = drops[0] if drops else None
        after_first = decisions[decisions.index(first)+1:] if first else []
        forward_errors = Counter()
        comparable = closer = 0
        for before, after in zip(decisions, decisions[1:]):
            if before["target_kind"] == "drop" and before["action"] == "FORWARD":
                ack = acknowledgments.get(before["command_id"])
                forward_errors[(ack["error"] or ack["status"]) if ack else "unacknowledged"] += 1
                if before["target_id"] == after["target_id"]:
                    comparable += 1
                    closer += int(after["distance"] < before["distance"] - 0.02)
        result.append({
            "run_id": episode["run_id"], "episode_id": episode_id, "layout_seed": episode["layout_seed"],
            "log_inventory": episode["inventory"]["log"], "confirmed_breaks": len(breaks),
            "decisions_after_final_break": len(decisions),
            "drop_visible_decisions": len(drops),
            "closest_visible_drop": min((row["distance"] for row in drops), default=None),
            "first_drop_decision": first,
            "next_target_after_first_seen_drop": after_first[0] if after_first else None,
            "actions_while_drop_selected": dict(Counter(row["action"] for row in drops)),
            "forward_outcomes_before_next_decision": dict(forward_errors),
            "forward_with_same_drop_in_next_decision": comparable,
            "forward_with_same_drop_at_least_0_02_blocks_closer": closer,
        })
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    historical = json.loads((PHASE / "phase8_completion_bench_20261108/results.json").read_text(encoding="utf-8"))
    pilot_id = "p8_pitch_dev_20261112_pitch"
    pilot = [episode | {"run_id": pilot_id} for episode in rows(PHASE / pilot_id / "server.jsonl")]
    output = {"historical_yaw_trials": failed_pickups(historical["episodes"]),
              "pitch_development_pilot": failed_pickups(pilot)}
    with args.output.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(output, handle, indent=2, allow_nan=False)
        handle.write("\n")


if __name__ == "__main__":
    main()
