#!/usr/bin/env python3
"""Analyze explicitly selected live runs using independent server inventory scores."""
import argparse
import collections
import json
import math
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def wilson(successes, total):
    if not total:
        return None
    z = 1.959963984540054
    p = successes / total
    center = (p + z*z/(2*total)) / (1 + z*z/total)
    half = z * math.sqrt(p*(1-p)/total + z*z/(4*total*total)) / (1 + z*z/total)
    return [max(0, center-half), min(1, center+half)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output must be new")
    grouped = collections.defaultdict(list)
    missing, rows = [], []
    for run in args.runs:
        directory = ROOT / "experiments/phase8" / run
        metadata = json.loads((directory / "run.json").read_text())
        controllers = {}
        if (directory / "controller.jsonl").exists():
            controllers = {row["episode_id"]: row for row in map(json.loads, (directory / "controller.jsonl").read_text().splitlines())}
        scores = list(map(json.loads, (directory / "server.jsonl").read_text().splitlines())) if (directory / "server.jsonl").exists() else []
        for score in scores:
            controller = controllers.get(score["episode_id"])
            row = score | {"run": run, "world_seed": metadata["world_seed"], "actions": controller["actions"] if controller else None,
                           "controller_termination": controller["termination"] if controller else "missing_controller_result"}
            rows.append(row)
            grouped[score["condition"], score["goal"]].append(row)
        if len(scores) != metadata["requested"]:
            missing.append({"run": run, "requested": metadata["requested"], "completed": len(scores), "stop_reason": metadata["stop_reason"]})
    summary = {"runs": args.runs, "incomplete_runs": missing, "conditions": {}, "raw_episodes": rows,
               "interval": "95% Wilson score interval, descriptive over controlled fixture trials"}
    for (condition, goal), group in grouped.items():
        successes = [row for row in group if row["success"]]
        action_rows = [row["actions"] for row in successes if row["actions"] is not None]
        summary["conditions"].setdefault(condition, {})[goal] = {
            "trials": len(group), "successes": len(successes), "success_rate": len(successes) / len(group),
            "wilson_95": wilson(len(successes), len(group)), "world_seeds": sorted({row["world_seed"] for row in group}),
            "mean_success_actions": statistics.fmean(action_rows) if action_rows else None,
            "mean_success_game_seconds": statistics.fmean(row["ticks"] / 20 for row in successes) if successes else None,
            "controller_terminations": dict(collections.Counter(row["controller_termination"] for row in group))}
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)
    print(json.dumps({key: value for key, value in summary.items() if key != "raw_episodes"}, indent=2))


if __name__ == "__main__":
    main()
