#!/usr/bin/env python3
"""Re-evaluate the three preserved Phase 7 policies against their exact baseline seeds."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from autonomy import AutonomousAgent, GOALS
from autonomy.metrics import summarize
from tools.train_phase7 import evaluate, feature_table


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output must be new")
    table = feature_table()
    results = {"environment": "Phase 7 World2D simulator, not Minecraft", "matches_baseline": True, "policies": {}}
    fields = ("episodes", "successes", "goal_completion_rate", "mean_actions", "failed_actions", "recovery_attempts")
    for seed in (11, 29, 47):
        baseline = json.loads((ROOT / f"experiments/phase7/evaluation_v3_seed{seed}.json").read_text())
        agent, _ = AutonomousAgent.load(ROOT / f"checkpoints/phase7/curriculum_v3_seed{seed}.npz", table)
        goals = {}
        for level, goal in enumerate(GOALS):
            start = baseline["seed"] + level * 100_000
            metrics = summarize(evaluate(agent, goal, range(start, start + baseline["episodes_per_goal"])))
            previous = baseline["conditions"]["phase7_trained"][goal]
            differences = {key: {"baseline": previous[key], "current": metrics[key]}
                           for key in fields if previous[key] != metrics[key]}
            goals[goal] = {"episodes": metrics["episodes"], "successes": metrics["successes"], "differences": differences}
            results["matches_baseline"] &= not differences
        results["policies"][str(seed)] = goals
        print(json.dumps({"policy_seed": seed, "goals": goals}), flush=True)
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(results, handle, indent=2)
    if not results["matches_baseline"]:
        raise SystemExit("Phase 7 regression differs; inspect preserved metrics")


if __name__ == "__main__":
    main()
