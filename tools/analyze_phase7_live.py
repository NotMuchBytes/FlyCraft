#!/usr/bin/env python3
"""Analyze actual Fabric/server/Python logs from a bounded navigation test."""

import argparse
import collections
import json
import re
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix", type=Path, required=True, help="Paths PREFIX_{server.log,client.log,bridge.jsonl}")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output must be new")
    prefix = str(args.prefix)
    server = Path(prefix + "_server.log").read_text(encoding="utf-8")
    client = Path(prefix + "_client.log").read_text(encoding="utf-8")
    rows = [json.loads(line) for line in Path(prefix + "_bridge.jsonl").read_text(encoding="utf-8").splitlines()]
    outcomes = re.findall(r"FLYCRAFT_PHASE7 scene_end success=(true|false) distance=([\d.Ee+-]+) ticks=(\d+)", server)
    responses = [row["response"] for row in rows]
    goal_results = [response["goal_result"] for response in responses if response.get("goal_result")]
    errors = sum(response["status"] != "ok" for response in responses)
    failures = client.count("FLYCRAFT bridge request failed")
    stale = client.count("FLYCRAFT stale action ignored")
    result = {"environment": "real Minecraft 26.2 / Fabric 0.19.5, fresh local flat world",
              "server_outcomes": [{"success": success == "true", "distance": float(distance), "ticks": int(ticks)} for success, distance, ticks in outcomes],
              "goal_result": goal_results[-1] if goal_results else None, "requests": len(rows), "response_errors": errors,
              "client_request_failures": failures, "stale_actions": stale,
              "actions_applied": client.count("FLYCRAFT action_applied"),
              "neural_windows": sum(response.get("neural_steps", 0) == 18 for response in responses),
              "action_distribution": dict(collections.Counter(response.get("action") for response in responses)),
              "passed": bool(outcomes and outcomes[-1][0] == "true" and goal_results and goal_results[-1]["success"] and not (errors or failures or stale))}
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
