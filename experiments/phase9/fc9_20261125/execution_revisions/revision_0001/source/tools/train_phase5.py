#!/usr/bin/env python3
"""Train or resume the small FlyCraft action readout."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from learning import LinearSoftmaxPolicy, NeuralFeatureTable, TargetTask, TrainingConfig


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--episodes", type=int, default=100)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--checkpoint", type=Path, required=True, help="New output checkpoint, or existing input checkpoint with --resume")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--output", type=Path, help="Episode JSONL path")
    parser.add_argument("--max-steps", type=int, default=24)
    parser.add_argument("--save-every", type=int, default=50)
    args = parser.parse_args()
    if args.episodes <= 0 or args.max_steps <= 0 or args.save_every <= 0:
        parser.error("episodes, max-steps, and save-every must be positive")
    return args


def default_log(seed: int, initial_episode: int, final_episode: int) -> Path:
    return ROOT / "experiments" / "phase5" / "runs" / f"cli_seed_{seed}_episodes_{initial_episode + 1}_{final_episode}.jsonl"


def main() -> None:
    args = arguments()
    checkpoint = args.checkpoint.resolve()
    if args.resume:
        if not checkpoint.exists():
            raise SystemExit(f"resume checkpoint does not exist: {checkpoint}")
        policy, metadata = LinearSoftmaxPolicy.load(checkpoint)
        seed = metadata["training_seed"]
        if args.seed is not None and args.seed != seed:
            raise SystemExit(f"--seed {args.seed} does not match checkpoint seed {seed}")
        rng = np.random.default_rng()
        rng.bit_generator.state = metadata["rng_state"]
        initial_episode = policy.episodes_trained
        final_checkpoint = checkpoint.with_name(f"{checkpoint.stem}_resumed_to_{initial_episode + args.episodes}{checkpoint.suffix}")
    else:
        if checkpoint.exists():
            raise SystemExit(f"refusing to overwrite checkpoint: {checkpoint}; use --resume or a new path")
        seed = 42 if args.seed is None else args.seed
        rng = np.random.default_rng(seed)
        policy = LinearSoftmaxPolicy()
        initial_episode = 0
        final_checkpoint = checkpoint
    if final_checkpoint.exists():
        raise SystemExit(f"refusing to overwrite output checkpoint: {final_checkpoint}")

    table = NeuralFeatureTable.from_phase35(ROOT / "experiments" / "phase35" / "results" / "rate_decoder_evaluation.json")
    task = TargetTask(table)
    config = TrainingConfig(max_steps=args.max_steps)
    final_episode = initial_episode + args.episodes
    output = (args.output or default_log(seed, initial_episode, final_episode)).resolve()
    if output.exists():
        raise SystemExit(f"refusing to overwrite episode log: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    started = time.perf_counter()
    for episode in range(initial_episode + 1, final_episode + 1):
        result = task.run_episode(policy, rng, episode=episode, seed=seed, config=config, train=True)
        row = result.serializable()
        rows.append(row)
        if (episode - initial_episode) % args.save_every == 0 and episode != final_episode:
            periodic = final_checkpoint.with_name(f"{final_checkpoint.stem}_episode_{episode}{final_checkpoint.suffix}")
            if not periodic.exists():
                policy.save_atomic(periodic, training_seed=seed, rng_state=rng.bit_generator.state)
    with output.open("x", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, separators=(",", ":")) + "\n")
    policy.save_atomic(final_checkpoint, training_seed=seed, rng_state=rng.bit_generator.state)
    elapsed = time.perf_counter() - started
    summary = {
        "episodes": len(rows),
        "initial_episode": initial_episode,
        "final_episode": final_episode,
        "seed": seed,
        "successes": sum(bool(row["success"]) for row in rows),
        "success_rate": sum(bool(row["success"]) for row in rows) / len(rows),
        "mean_reward": statistics.fmean(float(row["total_reward"]) for row in rows),
        "median_reward": statistics.median(float(row["total_reward"]) for row in rows),
        "mean_episode_length": statistics.fmean(int(row["steps"]) for row in rows),
        "elapsed_training_seconds": elapsed,
        "checkpoint": str(final_checkpoint),
        "episode_log": str(output),
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
