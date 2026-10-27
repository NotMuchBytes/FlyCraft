#!/usr/bin/env python3
"""Prespecified Phase 5 learning validation over fixed connectome features."""

from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from learning import LinearSoftmaxPolicy, NeuralFeatureTable, TargetTask, TrainingConfig


TRAINING_SEEDS = (11, 29, 47)
TRAINING_EPISODES = 2_000
EVALUATION_EPISODES = 200
CONFIG = TrainingConfig()
RESULTS = ROOT / "experiments" / "phase5" / "results"
RUNS = ROOT / "experiments" / "phase5" / "runs"
CHECKPOINTS = ROOT / "checkpoints" / "phase5" / "followup_2000ep"


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, separators=(",", ":")) + "\n")


def train(task: TargetTask, seed: int, *, save: bool) -> tuple[LinearSoftmaxPolicy, list[dict[str, object]], float]:
    rng = np.random.default_rng(seed)
    policy = LinearSoftmaxPolicy()
    if save:
        policy.save_atomic(CHECKPOINTS / f"seed_{seed}_untrained.npz", training_seed=seed, rng_state=rng.bit_generator.state)
    rows = []
    started = time.perf_counter()
    for episode in range(1, TRAINING_EPISODES + 1):
        result = task.run_episode(policy, rng, episode=episode, seed=seed, config=CONFIG, train=True)
        rows.append(result.serializable())
        if save and episode % 50 == 0:
            policy.save_atomic(CHECKPOINTS / f"seed_{seed}_episode_{episode:04d}.npz", training_seed=seed, rng_state=rng.bit_generator.state)
    elapsed = time.perf_counter() - started
    if save:
        write_jsonl(RUNS / f"seed_{seed}_training.jsonl", rows)
        policy.save_atomic(CHECKPOINTS / f"seed_{seed}_trained_final.npz", training_seed=seed, rng_state=rng.bit_generator.state)
    return policy, rows, elapsed


def evaluate(task: TargetTask, policy: LinearSoftmaxPolicy, seed: int, label: str) -> tuple[dict[str, float], list[dict[str, object]]]:
    rng = np.random.default_rng(seed)
    rows = [
        task.run_episode(policy, rng, episode=episode, seed=seed, config=CONFIG, train=False).serializable()
        for episode in range(1, EVALUATION_EPISODES + 1)
    ]
    successes = [row for row in rows if row["success"]]
    summary = {
        "episodes": len(rows),
        "successes": len(successes),
        "success_rate": len(successes) / len(rows),
        "mean_reward": statistics.fmean(float(row["total_reward"]) for row in rows),
        "median_reward": statistics.median(float(row["total_reward"]) for row in rows),
        "mean_final_distance": statistics.fmean(float(row["final_distance"]) for row in rows),
        "mean_steps": statistics.fmean(int(row["steps"]) for row in rows),
        "mean_steps_to_success": statistics.fmean(int(row["steps"]) for row in successes) if successes else float("nan"),
    }
    write_jsonl(RUNS / f"{label}_seed_{seed}_evaluation.jsonl", rows)
    return summary, rows


def shuffled_task(table: NeuralFeatureTable, seed: int) -> TargetTask:
    rng = np.random.default_rng(seed)
    visible = ["far_left", "left", "center", "right", "far_right"]
    values = [table.features[name].copy() for name in visible]
    rng.shuffle(values)
    mapping = {name: value for name, value in zip(visible, values, strict=True)}
    mapping["not_visible"] = table.features["not_visible"].copy()
    return TargetTask(NeuralFeatureTable(mapping, table.scale))


def hidden_control(policy: LinearSoftmaxPolicy, table: NeuralFeatureTable, seed: int) -> dict[str, object]:
    rng = np.random.default_rng(seed)
    feature = table.for_sector(None)
    counts = {name: 0 for name in ("NO_OP", "TURN_LEFT", "TURN_RIGHT", "FORWARD")}
    for _ in range(50 * CONFIG.max_steps):
        _, action, _ = policy.sample(feature, rng)
        counts[action] += 1
    return {"steps": sum(counts.values()), "action_counts": counts, "no_op_fraction": counts["NO_OP"] / sum(counts.values())}


def aggregate(items: list[dict[str, float]]) -> dict[str, float]:
    return {key: statistics.fmean(item[key] for item in items) for key in items[0]}


def plot(training_rows: dict[int, list[dict[str, object]]], comparison: dict[str, dict[str, float]]) -> None:
    figure, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    for seed, rows in training_rows.items():
        rewards = np.array([float(row["total_reward"]) for row in rows])
        moving = np.convolve(rewards, np.ones(25) / 25, mode="valid")
        axes[0].plot(np.arange(25, len(rewards) + 1), moving, label=f"seed {seed}")
    axes[0].set(title="Training reward (25-episode mean)", xlabel="Episode", ylabel="Reward")
    axes[0].legend(frameon=False)
    axes[0].grid(alpha=0.2)
    names = ["baseline", "trained", "shuffled"]
    axes[1].bar(names, [comparison[name]["success_rate"] for name in names], color=("#6c757d", "#2a9d8f", "#e9c46a"))
    axes[1].set(title="Held-out success rate", ylabel="Success fraction", ylim=(0, 1))
    axes[1].grid(axis="y", alpha=0.2)
    figure.tight_layout()
    figure_dir = ROOT / "docs" / "figures"
    figure_dir.mkdir(parents=True, exist_ok=True)
    figure.savefig(figure_dir / "phase5_learning_validation.png", dpi=180)
    figure.savefig(figure_dir / "phase5_learning_validation.svg")
    plt.close(figure)


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    RUNS.mkdir(parents=True, exist_ok=True)
    CHECKPOINTS.mkdir(parents=True, exist_ok=True)
    table = NeuralFeatureTable.from_phase35(ROOT / "experiments" / "phase35" / "results" / "rate_decoder_evaluation.json")
    task = TargetTask(table)
    training_rows: dict[int, list[dict[str, object]]] = {}
    per_seed = []
    total_started = time.perf_counter()
    for seed in TRAINING_SEEDS:
        policy, rows, elapsed = train(task, seed, save=True)
        repeat, _, _ = train(task, seed, save=False)
        reproducible = np.array_equal(policy.weights, repeat.weights) and policy.baseline == repeat.baseline
        restored, metadata = LinearSoftmaxPolicy.load(CHECKPOINTS / f"seed_{seed}_trained_final.npz")
        checkpoint_exact = np.array_equal(policy.weights, restored.weights) and policy.baseline == restored.baseline
        baseline_summary, _ = evaluate(task, LinearSoftmaxPolicy(), 10_000 + seed, "baseline")
        trained_summary, _ = evaluate(task, restored, 10_000 + seed, "trained")
        shuffled_summary, _ = evaluate(shuffled_task(table, 20_000 + seed), restored, 10_000 + seed, "shuffled")
        per_seed.append(
            {
                "seed": seed,
                "training_elapsed_seconds": elapsed,
                "training_success_last_50": sum(bool(row["success"]) for row in rows[-50:]) / 50.0,
                "nonzero_update_episodes": sum(float(row["weight_delta_norm"]) > 0 for row in rows),
                "same_seed_reproducible": reproducible,
                "checkpoint_exact": checkpoint_exact,
                "checkpoint_episodes": restored.episodes_trained,
                "checkpoint_seed": metadata["training_seed"],
                "baseline": baseline_summary,
                "trained": trained_summary,
                "shuffled": shuffled_summary,
                "hidden_control": hidden_control(restored, table, 30_000 + seed),
            }
        )
        training_rows[seed] = rows
    comparison = {name: aggregate([item[name] for item in per_seed]) for name in ("baseline", "trained", "shuffled")}
    distance_reduction = (comparison["baseline"]["mean_final_distance"] - comparison["trained"]["mean_final_distance"]) / comparison["baseline"]["mean_final_distance"]
    success_gain = comparison["trained"]["success_rate"] - comparison["baseline"]["success_rate"]
    passed = (
        distance_reduction >= 0.20
        and success_gain >= 0.25
        and all(item["same_seed_reproducible"] and item["checkpoint_exact"] for item in per_seed)
        and all(item["nonzero_update_episodes"] == TRAINING_EPISODES for item in per_seed)
    )
    payload = {
        "prespecified": {
            "training_seeds": TRAINING_SEEDS,
            "training_episodes_per_seed": TRAINING_EPISODES,
            "evaluation_episodes_per_seed": EVALUATION_EPISODES,
            "training_config": CONFIG.__dict__,
            "success_criteria": {"minimum_mean_final_distance_reduction": 0.20, "minimum_success_rate_gain": 0.25},
        },
        "learning_boundary": "only the 4x4 linear action readout changes; connectome topology, normalized graph weights, dynamics, sensory encoder, and visual_projection population stay fixed",
        "per_seed": per_seed,
        "aggregate": comparison,
        "observed_mean_final_distance_reduction": distance_reduction,
        "observed_success_rate_gain": success_gain,
        "phase5_passed": passed,
        "elapsed_seconds": time.perf_counter() - total_started,
    }
    (RESULTS / "learning_validation.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    plot(training_rows, comparison)
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
