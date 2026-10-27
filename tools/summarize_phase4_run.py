#!/usr/bin/env python3
"""Extract synchronized Phase 4 evidence from the Minecraft logs."""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "experiments" / "phase4" / "raw"
SERVER_PATTERN = re.compile(r"\[(\d\d:\d\d:\d\d)] .* FLYCRAFT_AUTOTEST phase=(\w+) server_tick=(\d+) target=([^\r\n]+)")
OBS_PATTERN = re.compile(r"\[(\d\d:\d\d:\d\d)] .* FLYCRAFT observation tick=(\d+) sector=(\w+)")
ACTION_PATTERN = re.compile(r"\[(\d\d:\d\d:\d\d)] .* FLYCRAFT action_applied tick=(\d+) sector=(\w+) action=(\w+) latency_ms=([0-9.]+)")


def clock(value: str) -> datetime:
    return datetime.strptime(value, "%H:%M:%S")


def main() -> None:
    server_text = (RAW / "run2_server.log").read_text(encoding="utf-8", errors="replace")
    client_text = (RAW / "run2_client.log").read_text(encoding="utf-8", errors="replace")
    phases = [
        {"time": clock(match[0]), "condition": match[1], "server_tick": int(match[2]), "target": match[3]}
        for match in SERVER_PATTERN.findall(server_text)
    ]
    observations = [
        {"time": clock(match[0]), "tick_id": int(match[1]), "sector": match[2]}
        for match in OBS_PATTERN.findall(client_text)
    ]
    actions = {
        int(match[1]): {"action_time": clock(match[0]), "sector": match[2], "action": match[3], "latency_ms": float(match[4])}
        for match in ACTION_PATTERN.findall(client_text)
    }
    trials = []
    for index, phase in enumerate(phases):
        end = phases[index + 1]["time"] if index + 1 < len(phases) else phase["time"] + timedelta(seconds=7)
        # The logs have one-second timestamps. Skip that same second so a client
        # observation emitted just before the server phase update is not paired
        # with the new phase.
        start = phase["time"] + timedelta(seconds=1)
        candidates = [item for item in observations if start <= item["time"] < end]
        if not candidates:
            continue
        observation = candidates[0]
        action = actions.get(observation["tick_id"])
        trials.append(
            {
                "cycle": index // 4 + 1,
                "condition": phase["condition"],
                "server_tick": phase["server_tick"],
                "target": phase["target"],
                "first_observation": {"tick_id": observation["tick_id"], "sector": observation["sector"]},
                "first_action": None if action is None else {key: value for key, value in action.items() if key != "action_time"},
            }
        )
    latencies = [item["latency_ms"] for item in actions.values()]
    expected = {"left": "TURN_LEFT", "center": "TURN_LEFT", "right": "TURN_RIGHT", "not_visible": "NO_OP"}
    verified = [trial for trial in trials if trial["cycle"] <= 2]
    payload = {
        "source_logs": ["raw/run2_server.log", "raw/run2_client.log"],
        "architecture": "Minecraft raycast -> five-sector observation -> TCP newline JSON -> fixed 139255-neuron bounded-rate simulation -> visual_projection side decoder -> tick-matched Minecraft action",
        "all_action_count": len(actions),
        "stale_action_count": client_text.count("stale action ignored"),
        "bridge_error_count": client_text.count("bridge request failed"),
        "latency_ms": {
            "minimum": min(latencies),
            "median": sorted(latencies)[len(latencies) // 2],
            "maximum": max(latencies),
        },
        "first_two_cycles_match_phase35_predictions": all(
            trial["first_observation"]["sector"] == trial["condition"]
            and trial["first_action"] is not None
            and trial["first_action"]["action"] == expected[trial["condition"]]
            for trial in verified
        ),
        "trials": trials,
    }
    output = ROOT / "experiments" / "phase4" / "phase4_metrics.json"
    output.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(json.dumps(payload, indent=2, default=str))


if __name__ == "__main__":
    main()
