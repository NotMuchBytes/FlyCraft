"""Audit recorded decisions and matched acknowledgments; never execute actions."""

import argparse
from collections import Counter
import json
import math
from pathlib import Path
import statistics


def analyze_run(folder):
    folder = Path(folder)
    run = json.loads((folder / "run.json").read_text(encoding="utf-8"))
    pending, completed = {}, set()
    actions, statuses, motions = Counter(), Counter(), []
    unexecuted, unseen, longest_unseen, near_without_mining = 0, 0, 0, 0
    for line in (folder / "bridge.jsonl").read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        request = row["request"]
        if isinstance(request, str):
            request = json.loads(request)
        telemetry, response = request.get("telemetry"), row.get("response", {})
        if telemetry is None:
            continue
        episode = request["control"]["episode_id"]
        ack = request.get("ack")
        key = (episode, ack.get("command_id")) if ack else None
        if key in pending and key not in completed:
            completed.add(key)
            before, action = pending.pop(key)
            # A stale/mismatched ack cannot establish that this action happened.
            if ack.get("action") != action:
                statuses["ack_action_mismatch"] += 1
            elif ack.get("status") == "not_executed":
                unexecuted += 1
            else:
                actions[action] += 1
                statuses[ack.get("status", "missing")] += 1
                p, q = before["position"], telemetry["position"]
                yaw = (q[2] - p[2] + math.pi) % (2 * math.pi) - math.pi
                movement = {"command_id": key[1], "episode_id": episode,
                    "action": action, "ack_status": ack.get("status"),
                    "horizontal_displacement": math.hypot(q[0]-p[0], q[1]-p[1]),
                    "observed_yaw_delta_degrees": math.degrees(yaw),
                    "visible_before": before["visible"], "visible_after": telemetry["visible"],
                    "same_visible_target": bool(before["visible"] and telemetry["visible"]
                        and before.get("target_id") == telemetry.get("target_id"))}
                if action in ("TURN_LEFT", "TURN_RIGHT"):
                    requested = run.get("turn_degrees", 15) * (-1 if action == "TURN_LEFT" else 1)
                    movement["requested_yaw_degrees"] = requested
                    movement["endpoint_error_degrees"] = (math.degrees(yaw)-requested+180) % 360-180
                motions.append(movement)
        command = response.get("command_id", 0)
        if command and not response.get("observe_only", False):
            command_key = (episode, command)
            if command_key not in completed and command_key not in pending:
                pending[command_key] = (telemetry, response["action"])
                unseen = unseen + 1 if not telemetry["visible"] else 0
                longest_unseen = max(longest_unseen, unseen)
                near_without_mining += int(telemetry["near"] and "COLLECT_LOG" not in telemetry["allowed_actions"])
    forward = [m for m in motions if m["action"] == "FORWARD" and m["ack_status"] == "success"]
    turns = [m for m in motions if "endpoint_error_degrees" in m and m["ack_status"] == "success"]
    return {"run_id": run.get("run_id", folder.name), "environment": run.get("environment_kind"),
        "forward_ticks": run.get("forward_ticks", 5), "actions_acknowledged": dict(actions),
        "ack_statuses": dict(statuses), "not_executed_commands": unexecuted,
        "unmatched_commands": len(pending), "longest_unseen_decision_streak": longest_unseen,
        "near_samples_without_mining_affordance": near_without_mining,
        "forward_target_losses": sum(m["visible_before"] and not m["visible_after"] for m in forward),
        "median_forward_displacement": statistics.median(m["horizontal_displacement"] for m in forward) if forward else None,
        "max_absolute_turn_endpoint_error": max((abs(m["endpoint_error_degrees"]) for m in turns), default=None),
        "measurement_scope": "Pose difference between decision and next matched acknowledgment observation; includes inertia and observation delay, not per-tick overshoot or causal action attribution.",
        "motions": motions}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", nargs="+", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    results = {"schema": 1, "runs": [analyze_run(folder) for folder in args.runs]}
    # Historical reports must not be overwritten by an adaptive new analysis.
    with args.output.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(results, handle, indent=2, allow_nan=False)
        handle.write("\n")
    print(args.output)


if __name__ == "__main__":
    main()
