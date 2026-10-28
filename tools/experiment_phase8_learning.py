#!/usr/bin/env python3
"""Bounded paired tests of retention rehearsal and per-goal return baselines."""
import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from autonomy import AutonomousAgent, ResourceWorld, GOALS
from autonomy.metrics import summarize
from tools.train_phase7 import evaluate, feature_table


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--episodes", type=int, default=300)
    args = parser.parse_args()
    if args.output.exists() or not 1 <= args.episodes <= 600:
        parser.error("output must be new; use at most 600 episodes per condition")
    table = feature_table()
    conditions = ("focused_global_baseline", "rehearsal_global_baseline", "rehearsal_goal_baseline")
    result = {"episodes_per_condition": args.episodes, "conditions": {}}
    for condition in conditions:
        agent, _ = AutonomousAgent.load(args.checkpoint, table)
        agent.rng = np.random.default_rng(8181)
        agent.config = replace(agent.config, goal_baselines=condition.endswith("goal_baseline"))
        rows = []
        for i in range(args.episodes):
            # Identical world/decision seeds; rehearsal replaces every fourth
            # pickaxe episode with a rotating earlier skill, without playing scripts.
            goal = GOALS[(i // 4) % 5] if condition.startswith("rehearsal") and i % 4 == 0 else "wooden_pickaxe"
            rows.append(agent.run_episode(ResourceWorld(7_800_000_000 + i, goal), goal, train=True))
        evaluation = {}
        for level, goal in enumerate(GOALS):
            evaluation[goal] = summarize(evaluate(agent, goal, range(9_500_000_000 + level * 1000, 9_500_000_000 + level * 1000 + 40)))
        variance = [row["update"].get("return_variance", 0) for row in rows]
        path = ROOT / "checkpoints/phase8" / (condition + ".npz")
        agent.save(path)
        result["conditions"][condition] = {"training": summarize(rows), "mean_return_variance": float(np.mean(variance)),
            "evaluation": evaluation, "checkpoint": str(path)}
        print(json.dumps({"condition": condition, "pickaxe_rate": evaluation["wooden_pickaxe"]["goal_completion_rate"],
                          "mean_return_variance": float(np.mean(variance))}), flush=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2)


if __name__ == "__main__":
    main()
