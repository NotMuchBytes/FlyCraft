#!/usr/bin/env python3
"""Bounded curriculum training with separate promotion evaluations and exact resume."""

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from autonomy import AutonomousAgent, AutonomyConfig, GOALS, ResourceWorld
from autonomy.metrics import summarize
from learning import LinearSoftmaxPolicy, NeuralFeatureTable


def feature_table():
    return NeuralFeatureTable.from_phase35(ROOT / "experiments/phase35/results/rate_decoder_evaluation.json")


def evaluate(agent, goal, seeds, *, obstacles=False, navigation_only=False, shuffle_neural=False):
    # Evaluation has its own memory, RNG, and curriculum and never changes the learner.
    evaluator = AutonomousAgent(agent.table, seed=agent.seed, policy=LinearSoftmaxPolicy(
        agent.policy.weights.shape[0], agent.policy.weights, actions=agent.policy.actions), config=agent.config)
    if shuffle_neural:
        keys = sorted(agent.table.features)
        permutation = np.random.default_rng(7007).permutation(len(keys))
        evaluator.table = NeuralFeatureTable({key: agent.table.features[keys[i]].copy() for key, i in zip(keys, permutation, strict=True)})
    rows = []
    for seed in seeds:
        world = ResourceWorld(int(seed), goal, obstacles=obstacles)
        evaluator.rng = np.random.default_rng(int(seed) + 1_000_000)
        if navigation_only:
            original_observe = world.observe
            def observe():
                observation = original_observe()
                observation["allowed_actions"] = list(agent.policy.actions[:4])
                return observation
            world.observe = observe
        rows.append(evaluator.run_episode(world, goal, train=False))
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--episodes", type=int, default=600)
    parser.add_argument("--seed", type=int, default=29)
    parser.add_argument("--checkpoint", type=Path, required=True, help="New output, never overwritten")
    parser.add_argument("--output", type=Path, required=True, help="New episode JSONL")
    parser.add_argument("--resume", type=Path)
    parser.add_argument("--initial-phase65", type=Path)
    parser.add_argument("--goal", choices=GOALS, help="Optional focused training instead of current curriculum level")
    parser.add_argument("--max-steps", type=int, default=120)
    parser.add_argument("--learning-rate", type=float, default=0.025)
    parser.add_argument("--evaluate-every", type=int, default=100)
    parser.add_argument("--eval-episodes", type=int, default=40)
    parser.add_argument("--success-threshold", type=float, default=0.70)
    parser.add_argument("--wall-seconds", type=float, default=180)
    args = parser.parse_args()
    if min(args.episodes, args.max_steps, args.evaluate_every, args.eval_episodes, args.wall_seconds) <= 0:
        parser.error("episode, step, evaluation, and wall limits must be positive")
    if args.resume and args.initial_phase65:
        parser.error("resume and initial-phase65 are mutually exclusive")
    summary_path = args.output.with_suffix(".summary.json")
    for path in (args.checkpoint, args.output, summary_path):
        if path.exists():
            parser.error(f"refusing to overwrite {path}")
    table = feature_table()
    if args.resume:
        agent, pending_world = AutonomousAgent.load(args.resume, table)
    else:
        config = AutonomyConfig(max_steps=args.max_steps, learning_rate=args.learning_rate)
        if args.initial_phase65:
            policy, _ = LinearSoftmaxPolicy.load(args.initial_phase65)
            agent = AutonomousAgent.transfer_phase65(table, policy, seed=args.seed, config=config)
        else:
            agent = AutonomousAgent(table, seed=args.seed, config=config)
        pending_world = None
        agent.curriculum.threshold = args.success_threshold
        agent.curriculum.min_evaluations = args.eval_episodes
        agent.curriculum.max_mean_actions = args.max_steps
    if agent.session and not agent.session["done"] and pending_world is None:
        parser.error("mid-episode resume requires a saved simulator world")
    started = time.perf_counter()
    rows, evaluations = [], []
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as handle:
        if pending_world and agent.session and not agent.session["done"]:
            while not agent.session["done"]:
                if agent.pending is None:
                    action = agent.choose_action(pending_world.observe())
                else:
                    action = agent.policy.actions[agent.pending[1]]
                if not agent.session["done"]:
                    agent.observe(pending_world.step(action))
            row = agent.result()
            rows.append(row)
            handle.write(json.dumps(row) + "\n")
        for _ in range(args.episodes):
            if time.perf_counter() - started >= args.wall_seconds:
                break
            # Seed domains are disjoint by construction, including across resume.
            episode_number = agent.memory.attempts.get("_training", {}).get("episodes", 0)
            world_seed = agent.seed * 1_000_000 + episode_number
            goal = args.goal or agent.curriculum.objective
            row = agent.run_episode(ResourceWorld(world_seed, goal), goal, train=True)
            agent.memory.attempts.setdefault("_training", {})["episodes"] = episode_number + 1
            rows.append(row)
            handle.write(json.dumps(row, separators=(",", ":")) + "\n")
            if (episode_number + 1) % args.evaluate_every == 0 and not args.goal:
                offset = len(agent.curriculum.history) * args.eval_episodes
                seeds = [8_000_000_000 + agent.seed * 100_000 + offset + i for i in range(args.eval_episodes)]
                evaluation = evaluate(agent, goal, seeds)
                training_domain = set(range(agent.seed * 1_000_000, agent.seed * 1_000_000 + episode_number + 1))
                agent.curriculum.assess(evaluation, training_seeds=training_domain)
                report = {"after_episode": episode_number + 1, "goal": goal, "metrics": summarize(evaluation),
                          "curriculum": agent.curriculum.history[-1], "rows": evaluation}
                evaluations.append(report)
                print(json.dumps({key: value for key, value in report.items() if key != "rows"}), flush=True)
            if (episode_number + 1) % args.evaluate_every == 0:
                periodic = args.checkpoint.with_name(f"{args.checkpoint.stem}_episode{episode_number + 1}.npz")
                agent.save(periodic)
        handle.flush()
    agent.save(args.checkpoint)
    summary = {"seed": agent.seed, "requested_episodes": args.episodes, "completed_episodes": len(rows),
               "elapsed_seconds": time.perf_counter() - started, "wall_limit_seconds": args.wall_seconds,
               "metrics": summarize(rows) if rows else None, "curriculum": agent.curriculum.to_dict(),
               "evaluations": evaluations, "checkpoint": str(args.checkpoint.resolve()),
               "initial_phase65": str(args.initial_phase65) if args.initial_phase65 else None,
               "resume": str(args.resume) if args.resume else None}
    with summary_path.open("x", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)
    print(json.dumps({key: value for key, value in summary.items() if key != "evaluations"}, indent=2))


if __name__ == "__main__":
    main()
