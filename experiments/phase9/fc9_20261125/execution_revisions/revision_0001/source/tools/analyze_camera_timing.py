#!/usr/bin/env python3
"""Measure pre-controller timing from existing live bridge logs, without moving a camera."""
import argparse
import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def decoded(value):
    return json.loads(value) if isinstance(value, str) else value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output must be new")
    primitive_ticks, feedback_ticks, latencies = [], [], []
    for run in args.runs:
        commands, seen = {}, set()
        with (ROOT / "experiments/phase8" / run / "bridge.jsonl").open() as handle:
            for line in handle:
                row = json.loads(line)
                request, response = decoded(row["request"]), decoded(row["response"])
                if not isinstance(request, dict) or not isinstance(response, dict):
                    continue
                ack = request.get("ack") or {}
                identity = ack.get("command_id")
                if identity in commands and identity not in seen and ack.get("action", "").startswith("TURN_"):
                    feedback_ticks.append(request["tick_id"] - commands[identity])
                    primitive_ticks.append(ack["ticks"])
                    seen.add(identity)
                if response.get("command_id", 0) > 0:
                    commands[response["command_id"]] = request["tick_id"]
                if "latency_ms" in response:
                    latencies.append(response["latency_ms"])
    result = {"runs": args.runs, "environment": "Real Minecraft bridge logs; original instantaneous camera",
              "turns_with_ack": len(feedback_ticks),
              "median_turn_primitive_ticks": statistics.median(primitive_ticks) if primitive_ticks else None,
              "median_ticks_to_next_observation": statistics.median(feedback_ticks) if feedback_ticks else None,
              "median_bridge_ms": statistics.median(latencies) if latencies else None,
              "maximum_bridge_ms": max(latencies) if latencies else None,
              "angular_overshoot_and_settling": "Not measured by these logs; require pose instrumentation",
              "interpretation": "Timing evidence does not by itself distinguish policy quantization, target tracking and physical camera overshoot."}
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
