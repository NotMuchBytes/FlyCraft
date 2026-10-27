#!/usr/bin/env python3
"""Evaluate a trained FlyCraft readout against an untrained baseline."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from learning import LinearSoftmaxPolicy, NeuralFeatureTable, TargetTask, TrainingConfig


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--episodes", type=int, default=200)
    parser.add_argument("--seed", type=int, default=10042)
    parser.add_argument("--output", type=Path, required=True, help="Summary JSON path")
    parser.add_argument("--max-steps", type=int, default=24)
    args = parser.parse_args()
    if args.episodes <= 0 or args.max_steps <= 0:
        parser.error("episodes and max-steps must be positive")
    return args


def run(task: TargetTask, policy: LinearSoftmaxPolicy, seed: int, episodes: int, config: TrainingConfig) -> list[dict[str, object]]:
    rng = np.random.default_rng(seed)
    return [task.run_episode(policy, rng, episode=index, seed=seed, config=config, train=False).serializable() for index in range(1, episodes + 1)]


def summarize(rows: list[dict[str, object]]) -> dict[str, float | int | None]:
    successes = [row for row in rows if row["success"]]
    return {
        "episodes": len(rows),
        "successes": len(successes),
        "success_rate": len(successes) / len(rows),
        "mean_reward": statistics.fmean(float(row["total_reward"]) for row in rows),
        "median_reward": statistics.median(float(row["total_reward"]) for row in rows),
        "mean_final_distance": statistics.fmean(float(row["final_distance"]) for row in rows),
        "mean_episode_length": statistics.fmean(int(row["steps"]) for row in rows),
        "mean_steps_to_success": statistics.fmean(int(row["steps"]) for row in successes) if successes else None,
    }


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("x", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, separators=(",", ":")) + "\n")


def main() -> None:
    args = arguments()
    checkpoint = args.checkpoint.resolve()
    if not checkpoint.exists():
        raise SystemExit(f"checkpoint does not exist: {checkpoint}")
    output = args.output.resolve()
    if output.exists():
        raise SystemExit(f"refusing to overwrite evaluation output: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    policy, metadata = LinearSoftmaxPolicy.load(checkpoint)
    table = NeuralFeatureTable.from_phase35(ROOT / "experiments" / "phase35" / "results" / "rate_decoder_evaluation.json")
    task = TargetTask(table)
    config = TrainingConfig(max_steps=args.max_steps)
    baseline_rows = run(task, LinearSoftmaxPolicy(), args.seed, args.episodes, config)
    trained_rows = run(task, policy, args.seed, args.episodes, config)
    baseline_log = output.with_name(output.stem + "_baseline.jsonl")
    trained_log = output.with_name(output.stem + "_trained.jsonl")
    if baseline_log.exists() or trained_log.exists():
        raise SystemExit("refusing to overwrite existing evaluation JSONL files")
    write_jsonl(baseline_log, baseline_rows)
    write_jsonl(trained_log, trained_rows)
    payload = {
        "checkpoint": str(checkpoint),
        "checkpoint_training_seed": metadata["training_seed"],
        "checkpoint_episodes": policy.episodes_trained,
        "evaluation_seed": args.seed,
        "max_steps": args.max_steps,
        "baseline": summarize(baseline_rows),
        "trained": summarize(trained_rows),
        "raw_logs": {"baseline": str(baseline_log), "trained": str(trained_log)},
    }
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
