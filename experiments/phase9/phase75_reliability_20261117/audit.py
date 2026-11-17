"""Audit matched Phase 7.5 development and held-out live runs."""

import argparse
from collections import Counter
import json
import math
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from tools.analyze_phase8 import wilson


def rows(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()] if path.exists() else []


def audit(run):
    path = ROOT / "experiments" / "phase9" / run
    meta = json.loads((path / "run.json").read_text(encoding="utf-8"))
    initial = {row["episode_id"]: row for row in rows(path / "server.jsonl.initial.jsonl")}
    delivered = {row["episode_id"] for row in rows(path / "server.jsonl.delivery.jsonl") if row["acknowledged"]}
    controllers = {row["episode_id"]: row for row in rows(path / "controller.jsonl")}
    observations = []
    for event in rows(path / "bridge.jsonl"):
        request = json.loads(event["request"])
        response = event.get("response", {})
        if isinstance(response, dict) and response.get("command_id") and "telemetry" in request:
            observations.append((request, response))
    headless = rows(path / "headless.jsonl")
    episodes = []
    for score in rows(path / "server.jsonl"):
        episode = score["episode_id"]
        start = initial[episode]
        controller = controllers.get(episode, {})
        events = [event["data"] for event in headless
                  if event["episode_id"] == episode and event["event"] == "action_end"]
        decisions = [(request["telemetry"], response["action"]) for request, response in observations
                     if response["episode_id"] == episode]
        forward = [event for event in events if event["ack"]["action"] == "FORWARD"]
        jumps = [event for event in forward if event["ack"].get("jump_assisted")]
        visible = [obs for obs, _ in decisions if obs["target_kind"] == "block"]
        legal_mine = sum("COLLECT_LOG" in obs["allowed_actions"] for obs, _ in decisions)
        breaks = [event for event in events if event["ack"]["action"] == "COLLECT_LOG"
                  and event["ack"]["status"] == "success" and event["ack"]["block_changed"]]
        terminal = controller.get("terminal_inventory", {})
        inventory_matches = all(terminal.get(item) == count for item, count in score["inventory"].items())
        verified = (episode in delivered and inventory_matches
                    and controller.get("success") == score["success"]
                    and controller.get("confirmed_block_changes") == len(breaks)
                    and not any(start["inventory"].values()))
        if not verified:
            outcome = "unverified_episode"
        elif score["success"]:
            outcome = "success" if breaks else "success_without_confirmed_break"
        elif breaks:
            outcome = "break_with_partial_or_no_pickup" if score["goal"] in {"one_log", "three_logs"} else "craft_goal_unmet"
        elif legal_mine:
            outcome = "mineable_without_confirmed_break"
        else:
            outcome = "visible_outside_mining_affordance" if visible else "no_log_visible"
        x, _, z, *_ = start["position_xyz_yaw_pitch"]
        episodes.append(score | {
            "verified": verified, "outcome": outcome, "initial": start,
            "actions": controller.get("actions"), "game_seconds": score["ticks"] / 20,
            "elapsed_seconds": controller.get("elapsed_seconds"),
            "decisions": len(decisions), "visible_block_decisions": len(visible),
            "closest_visible_log": min((obs["target_distance"] for obs in visible), default=None),
            "first_visible_log_decision": next((i for i, (obs, _) in enumerate(decisions, 1)
                                                if obs["target_kind"] == "block"), None),
            "farthest_observed_from_start": max((math.hypot(obs["position"][0]-x, obs["position"][1]-z)
                                                 for obs, _ in decisions), default=0),
            "blind_forward_decisions": sum(not obs["visible"] and action == "FORWARD" for obs, action in decisions),
            "blind_decisions": sum(not obs["visible"] for obs, _ in decisions),
            "legal_mine_decisions": legal_mine, "confirmed_breaks": len(breaks),
            "first_legal_mine_decision": next((i for i, (obs, _) in enumerate(decisions, 1)
                                              if "COLLECT_LOG" in obs["allowed_actions"]), None),
            "blocked_forward_actions": sum(event["ack"]["error"] == "movement_blocked" for event in forward),
            "jump_actions": [{"ack": event["ack"], "end_position_x_z_yaw": event["position"]}
                             for event in jumps],
            "max_observed_z": max((obs["position"][1] for obs, _ in decisions), default=z),
        })
    configuration = {key: meta.get(key) for key in (
        "environment_kind", "world_seed", "policy_rng_seed", "trial_tick_limit", "checkpoint_sha256",
        "frozen_checkpoint_sha256", "implementation_sha256", "forward_ticks", "turn_degrees",
        "movement_feedback", "pitch_actions", "camera_mode", "jump_on_blocked_forward", "explore_forward")}
    verified = [episode for episode in episodes if episode["verified"]]
    successes = sum(episode["success"] for episode in verified)
    return {"run": run, "settings": configuration, "requested": meta["requested"], "stop_reason": meta["stop_reason"],
            "verified_trials": len(verified), "successes": successes, "wilson_95": wilson(successes, len(verified)),
            "median_actions": statistics.median(e["actions"] for e in verified) if verified else None,
            "median_elapsed_seconds": statistics.median(e["elapsed_seconds"] for e in verified) if verified else None,
            "outcomes": dict(Counter(episode["outcome"] for episode in episodes)), "episodes": episodes}


def matched(reference, comparison, factor):
    a, b = (run["episodes"] for run in (reference, comparison))
    ignored = {factor}
    differences = [key for key, value in reference["settings"].items()
                   if key not in ignored and value != comparison["settings"][key]]
    if len(a) != 1 or len(b) != 1:
        differences.append("missing_or_ambiguous_episode")
    else:
        for key in ("goal", "layout_seed", "game_mode", "position_xyz_yaw_pitch", "inventory", "fixture_blocks"):
            if a[0]["initial"].get(key) != b[0]["initial"].get(key):
                differences.append(key)
    return {"reference": reference["run"], "comparison": comparison["run"], "factor": factor,
            "matched": not differences, "differences": differences}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", nargs="+", required=True)
    parser.add_argument("--pair", nargs=3, action="append", default=[], metavar=("REFERENCE", "COMPARISON", "FACTOR"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    reports = {run: audit(run) for run in args.runs}
    result = {"runs": list(reports.values()), "pairs": [
        matched(reports[ref], reports[comp], factor) for ref, comp, factor in args.pair]}
    with args.output.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
        handle.write("\n")


if __name__ == "__main__":
    main()
