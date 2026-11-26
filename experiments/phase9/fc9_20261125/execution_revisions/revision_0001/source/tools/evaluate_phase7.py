#!/usr/bin/env python3
"""Matched simulation evaluation, frozen controls, and neural/recovery ablations."""

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from autonomy import AutonomousAgent, GOALS
from autonomy.metrics import summarize
from learning import LinearSoftmaxPolicy
from tools.train_phase7 import evaluate, feature_table


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--phase65", type=Path, required=True)
    parser.add_argument("--episodes", type=int, default=100)
    parser.add_argument("--seed", type=int, default=9_000_000_000)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--ablations", action="store_true")
    args = parser.parse_args()
    raw_path = args.output.with_suffix(".jsonl")
    if args.episodes <= 0 or args.output.exists() or raw_path.exists():
        parser.error("episodes must be positive and output paths must be new")
    table = feature_table()
    trained, _ = AutonomousAgent.load(args.checkpoint, table)
    phase65, _ = LinearSoftmaxPolicy.load(args.phase65)
    baseline = AutonomousAgent.transfer_phase65(table, phase65, config=trained.config)
    uniform = AutonomousAgent(table, config=trained.config)
    conditions = {"uniform_same_planner": (uniform, {}), "phase65_navigation_only": (baseline, {"navigation_only": True}),
                  "phase7_frozen_transfer": (baseline, {}), "phase7_trained": (trained, {})}
    if args.ablations:
        conditions["phase7_shuffled_neural"] = (trained, {"shuffle_neural": True})
        no_recovery = AutonomousAgent(table, policy=LinearSoftmaxPolicy(trained.policy.weights.shape[0], trained.policy.weights,
                                    actions=trained.policy.actions), config=replace(trained.config, max_recoveries=0, stagnation_limit=trained.config.max_steps + 1))
        conditions["phase7_no_recovery"] = (no_recovery, {})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    summary = {"environment": "World2D resource simulator; not live Minecraft", "seed": args.seed,
               "episodes_per_goal": args.episodes, "world_seeds_unseen": True,
               "planning_assistance": "recipe DAG, objective completion, target sensor, physical action masks, bounded recovery",
               "learned_parameters": "linear softmax readout only; fixed 139255-neuron connectome",
               "conditions": {}}
    # Evaluation domain is kept separate from training and curriculum seeds.
    if args.seed < 9_000_000_000:
        parser.error("evaluation seed domain must be >= 9000000000")
    with raw_path.open("x", encoding="utf-8") as handle:
        for condition, (agent, options) in conditions.items():
            summary["conditions"][condition] = {}
            for level, goal in enumerate(GOALS):
                rows = evaluate(agent, goal, range(args.seed + level * 100_000, args.seed + level * 100_000 + args.episodes), **options)
                metrics = summarize(rows)
                summary["conditions"][condition][goal] = metrics
                for row in rows:
                    handle.write(json.dumps({"condition": condition, **row}, separators=(",", ":")) + "\n")
                print(json.dumps({"condition": condition, "goal": goal, "metrics": metrics}), flush=True)
        obstacle_rows = evaluate(trained, GOALS[2], range(args.seed + 700_000, args.seed + 700_000 + args.episodes), obstacles=True)
        summary["obstacle_stress"] = summarize(obstacle_rows)
        for row in obstacle_rows:
            handle.write(json.dumps({"condition": "phase7_obstacle_stress", **row}, separators=(",", ":")) + "\n")
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)


if __name__ == "__main__":
    main()
