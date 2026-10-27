#!/usr/bin/env python3
"""Aggregate retained Phase 7 evidence without treating repeated controls as new trials."""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from autonomy import AutonomousAgent
from autonomy.features import FEATURE_COUNT
from autonomy.metrics import summarize
from autonomy.world import ACTIONS
from learning import LinearSoftmaxPolicy
from tools.train_phase7 import feature_table


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output must be new")
    grouped = defaultdict(list)
    training = []
    table = feature_table()
    for seed in (11, 29, 47):
        directory = ROOT / "experiments/phase7"
        with (directory / f"evaluation_v3_seed{seed}.jsonl").open(encoding="utf-8") as handle:
            for line in handle:
                row = json.loads(line)
                if row["condition"] == "uniform_same_planner" and seed != 11:
                    continue
                grouped[row["condition"], row["goal"]].append(row)
        with (directory / f"curriculum_v3_seed{seed}.jsonl").open(encoding="utf-8") as handle:
            rows = [json.loads(line) for line in handle]
        agent, _ = AutonomousAgent.load(ROOT / f"checkpoints/phase7/curriculum_v3_seed{seed}.npz", table)
        previous, _ = LinearSoftmaxPolicy.load(ROOT / f"checkpoints/phase5/followup_2000ep/seed_{seed}_trained_final.npz")
        initial = previous.expanded(FEATURE_COUNT, ACTIONS)
        training.append({"seed": seed, "episodes": len(rows), "nonzero_policy_updates": sum(row["update"]["weight_delta_norm"] > 0 for row in rows),
                         "weight_change_from_frozen_transfer": float(np.linalg.norm(agent.policy.weights - initial.weights)),
                         "metrics": summarize(rows), "curriculum": agent.curriculum.to_dict()})
    report = {"environment": "seeded World2D extension", "training": training, "evaluation": {}}
    for (condition, goal), rows in grouped.items():
        report["evaluation"].setdefault(condition, {})[goal] = summarize(rows) | {"distinct_world_seeds": len({r["world_seed"] for r in rows})}
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    for condition in ("uniform_same_planner", "phase7_frozen_transfer", "phase7_trained"):
        print(condition)
        for goal, result in report["evaluation"][condition].items():
            print(f"  {goal}: {result['successes']}/{result['episodes']} ({result['goal_completion_rate']:.2%}), actions/success={result['average_actions_per_success']}")


if __name__ == "__main__":
    main()
