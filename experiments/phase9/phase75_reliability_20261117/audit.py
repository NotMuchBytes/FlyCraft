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
    terminal_packets = {}
    for event in rows(path / "bridge.jsonl"):
        request = json.loads(event["request"])
        response = event.get("response", {})
        if not isinstance(response, dict):
            continue
        terminal = request.get("control", {}).get("terminal")
        if terminal and response.get("terminal_acknowledged"):
            terminal_packets[response["episode_id"]] = terminal["inventory"]
        if response.get("command_id") and "telemetry" in request:
            observations.append((request, response))
    headless = rows(path / "headless.jsonl")
    episodes = []
    for score in rows(path / "server.jsonl"):
        episode = score["episode_id"]
        start = initial[episode]
        controller = controllers.get(episode, {})
        events = [event["data"] for event in headless
                  if event["episode_id"] == episode and event["event"] == "action_end"]
        episode_observations = [(request["telemetry"], response) for request, response in observations
                                if response["episode_id"] == episode]
        decisions = [(obs, response["action"]) for obs, response in episode_observations]
        forward = [event for event in events if event["ack"]["action"] == "FORWARD"]
        jumps = [event for event in forward if event["ack"].get("jump_assisted")]
        visible = [obs for obs, _ in decisions if obs["target_kind"] == "block"]
        legal_mine = sum("COLLECT_LOG" in obs["allowed_actions"] for obs, _ in decisions)
        breaks = [event for event in events if event["ack"]["action"] == "COLLECT_LOG"
                  and event["ack"]["status"] == "success" and event["ack"]["block_changed"]]
        completed_crafting = Counter(event["ack"]["action"] for event in events
                                     if event["ack"]["status"] == "success"
                                     and (event["ack"]["action"].startswith("CRAFT_")
                                          or event["ack"]["action"] == "PLACE_TABLE"))
        after_break = [(obs, response["action"]) for obs, response in episode_observations
                       if breaks and response["command_id"] > breaks[-1]["ack"]["command_id"]]
        terminal = controller.get("terminal_inventory") or terminal_packets.get(episode, {})
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
            outcome = "break_with_partial_or_no_pickup"
            if score["goal"] == "wooden_pickaxe":
                for action, failure in (("PLACE_TABLE", "table_placed_pickaxe_unconfirmed"),
                                        ("CRAFT_TABLE", "table_crafted_placement_unconfirmed"),
                                        ("CRAFT_STICKS", "sticks_crafted_table_unconfirmed"),
                                        ("CRAFT_PLANKS", "planks_crafted_sticks_unconfirmed")):
                    if completed_crafting[action]:
                        outcome = failure
                        break
            elif score["goal"] == "planks" and score["inventory"]["log"]:
                outcome = "log_picked_up_planks_unconfirmed"
        elif legal_mine:
            outcome = "mineable_without_confirmed_break"
        else:
            outcome = "visible_outside_mining_affordance" if visible else "no_log_visible"
        x, _, z, *_ = start["position_xyz_yaw_pitch"]
        episodes.append(score | {
            "verified": verified, "strict_success": verified and score["success"] and bool(breaks),
            "outcome": outcome, "initial": start,
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
            "after_final_break_decisions": len(after_break),
            "after_final_break_visible_drop_decisions": sum(obs["target_kind"] == "drop" for obs, _ in after_break),
            "after_final_break_forward_with_drop": sum(obs["target_kind"] == "drop" and action == "FORWARD"
                                                       for obs, action in after_break),
            "confirmed_crafting_and_placement": dict(completed_crafting),
            "legal_placement_decisions": sum("PLACE_TABLE" in obs["allowed_actions"] for obs, _ in decisions),
            "placement_outcomes": dict(Counter(event["ack"]["error"] or event["ack"]["status"] for event in events
                                               if event["ack"]["action"] == "PLACE_TABLE")),
        })
    configuration = {key: meta.get(key) for key in (
        "environment_kind", "world_seed", "policy_rng_seed", "trial_tick_limit", "checkpoint_sha256",
        "frozen_checkpoint_sha256", "implementation_sha256", "forward_ticks", "turn_degrees",
        "movement_feedback", "pitch_actions", "camera_mode", "jump_on_blocked_forward", "explore_forward")}
    return {"run": run, "settings": configuration, "requested": meta["requested"], "stop_reason": meta["stop_reason"],
            **summarize(episodes), "episodes": episodes}


def summarize(episodes):
    verified = [episode for episode in episodes if episode["verified"]]
    successes = sum(episode["strict_success"] for episode in verified)
    return {"verified_trials": len(verified), "successes": successes, "wilson_95": wilson(successes, len(verified)),
            "median_actions": statistics.median(e["actions"] for e in verified) if verified else None,
            "median_elapsed_seconds": statistics.median(e["elapsed_seconds"] for e in verified) if verified else None,
            "outcomes": dict(Counter(episode["outcome"] for episode in episodes))}


def matched(reference, comparison, factor):
    a, b = (run["episodes"] for run in (reference, comparison))
    ignored = {factor}
    differences = [key for key, value in reference["settings"].items()
                   if key not in ignored and value != comparison["settings"][key]]
    if len(a) != 1 or len(b) != 1:
        differences.append("missing_or_ambiguous_episode")
    else:
        if not a[0]["verified"] or not b[0]["verified"]:
            differences.append("unverified_episode")
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
    groups = {}
    for report in reports.values():
        for episode in report["episodes"]:
            condition = episode["condition"]
            if report["settings"]["explore_forward"]:
                condition += "_forward_prior"
            if report["settings"]["jump_on_blocked_forward"]:
                condition += "_jump"
            groups.setdefault(f"{episode['goal']}/{condition}", []).append(episode)
    result = {"groups": {name: summarize(episodes) for name, episodes in groups.items()},
              "runs": list(reports.values()), "pairs": [
        matched(reports[ref], reports[comp], factor) for ref, comp, factor in args.pair]}
    with args.output.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
        handle.write("\n")


if __name__ == "__main__":
    main()
