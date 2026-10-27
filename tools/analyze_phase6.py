#!/usr/bin/env python3
"""Parse the locked Phase 6 Minecraft logs and create Phase 6.5 metrics."""

from __future__ import annotations

import argparse
import csv
import json
import re
import statistics
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt


END_PATTERN = re.compile(
    r"FLYCRAFT_PHASE6 episode_end episode=(?P<episode>\d+) task=(?P<task>\S+) "
    r"seed=(?P<seed>\d+) success=(?P<success>true|false) termination=(?P<termination>\S+) "
    r"steps=(?P<steps>\d+) reward=(?P<reward>[-+\d.eE]+) initial_distance=(?P<initial_distance>[-+\d.eE]+) "
    r"final_distance=(?P<final_distance>[-+\d.eE]+) initial_angle_error=(?P<initial_angle_error>[-+\d.eE]+) "
    r"final_angle_error=(?P<final_angle_error>[-+\d.eE]+)"
)


def parse_log(path: Path, condition: str) -> list[dict[str, object]]:
    episodes: list[dict[str, object]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = END_PATTERN.search(line)
        if not match:
            continue
        item: dict[str, object] = {"condition": condition}
        for key, value in match.groupdict().items():
            if key in {"episode", "seed", "steps"}:
                item[key] = int(value)
            elif key == "success":
                item[key] = value == "true"
            elif key in {"task", "termination"}:
                item[key] = value
            else:
                item[key] = float(value)
        episodes.append(item)
    return episodes


def summarize(items: list[dict[str, object]]) -> dict[str, object]:
    rewards = [float(item["reward"]) for item in items]
    successful_steps = [int(item["steps"]) for item in items if item["success"]]
    successes = sum(bool(item["success"]) for item in items)
    return {
        "episodes": len(items),
        "successes": successes,
        "success_rate": successes / len(items),
        "mean_reward": statistics.fmean(rewards),
        "median_reward": statistics.median(rewards),
        "reward_population_stddev": statistics.pstdev(rewards),
        "mean_steps_to_success": statistics.fmean(successful_steps) if successful_steps else None,
        "failures": len(items) - successes,
        "timeouts": sum(item["termination"] == "timeout" for item in items),
        "best_reward": max(rewards),
        "worst_reward": min(rewards),
    }


def plot(metrics: dict[str, object], output: Path) -> None:
    conditions = ["baseline", "trained"]
    tasks = ["T1_ORIENT", "T2_APPROACH", "T3_GENERALIZE"]
    colors = {"baseline": "#858c94", "trained": "#2d7dd2"}
    fig, axes = plt.subplots(1, 3, figsize=(12, 4.1))
    overall = metrics["overall"]
    axes[0].bar(conditions, [100 * overall[c]["success_rate"] for c in conditions], color=[colors[c] for c in conditions])
    axes[0].set_title("Minecraft success rate")
    axes[0].set_ylabel("Success (%)")
    axes[0].set_ylim(0, 100)
    axes[1].bar(conditions, [overall[c]["mean_reward"] for c in conditions], color=[colors[c] for c in conditions])
    axes[1].set_title("Mean outcome reward")
    x = range(len(tasks))
    width = 0.35
    for offset, condition in [(-width / 2, "baseline"), (width / 2, "trained")]:
        values = [100 * metrics["by_task"][condition][task]["success_rate"] for task in tasks]
        axes[2].bar([i + offset for i in x], values, width=width, label=condition.title(), color=colors[condition])
    axes[2].set_xticks(list(x), ["Orient", "Approach", "Generalize"])
    axes[2].set_ylim(0, 100)
    axes[2].set_ylabel("Success (%)")
    axes[2].set_title("Success by task")
    axes[2].legend(frameon=False)
    fig.suptitle("FlyCraft Phase 6.5 — same nine Minecraft scenarios", fontweight="bold")
    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=180, bbox_inches="tight")
    fig.savefig(output.with_suffix(".svg"), bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--trained", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--plot", type=Path, required=True)
    args = parser.parse_args()

    by_condition = {
        "baseline": parse_log(args.baseline, "baseline"),
        "trained": parse_log(args.trained, "trained"),
    }
    for condition, items in by_condition.items():
        if len(items) != 9:
            raise RuntimeError(f"expected 9 {condition} episodes, found {len(items)}")
    scenario_keys = lambda items: [(item["episode"], item["task"], item["seed"]) for item in items]
    if scenario_keys(by_condition["baseline"]) != scenario_keys(by_condition["trained"]):
        raise RuntimeError("baseline and trained scenario sets differ")

    by_task: dict[str, dict[str, object]] = {}
    for condition, items in by_condition.items():
        grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
        for item in items:
            grouped[str(item["task"])].append(item)
        by_task[condition] = {task: summarize(task_items) for task, task_items in grouped.items()}

    overall = {condition: summarize(items) for condition, items in by_condition.items()}
    phase6_passed = all(by_task["trained"][task]["successes"] >= 1 for task in by_task["trained"])
    phase65_passed = (
        overall["trained"]["success_rate"] > overall["baseline"]["success_rate"]
        and overall["trained"]["mean_reward"] > overall["baseline"]["mean_reward"]
    )
    metrics = {
        "protocol": {
            "policy_mode": "stochastic",
            "bridge_seed": 9001,
            "scenarios_identical": True,
            "trained_checkpoint": "checkpoints/phase5/followup_2000ep/seed_29_trained_final.npz",
        },
        "overall": overall,
        "by_task": by_task,
        "phase6_operational_gate_passed": phase6_passed,
        "phase65_improvement_gate_passed": phase65_passed,
        "episodes": by_condition,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    with args.csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(by_condition["baseline"][0]))
        writer.writeheader()
        writer.writerows(by_condition["baseline"] + by_condition["trained"])
    plot(metrics, args.plot)
    print(json.dumps({"overall": overall, "phase6_passed": phase6_passed, "phase65_passed": phase65_passed}, indent=2))


if __name__ == "__main__":
    main()
