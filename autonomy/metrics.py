"""Aggregate actual rollouts; undefined ratios remain null."""

import statistics


def summarize(rows: list[dict]) -> dict:
    if not rows:
        raise ValueError("cannot evaluate an empty rollout set")
    successes = [row for row in rows if row["success"]]
    attempts = sum(row["recovery_attempts"] for row in rows)
    subgoals = sum(row["subgoals"] for row in rows)
    return {"episodes": len(rows), "successes": len(successes), "goal_completion_rate": len(successes) / len(rows),
            "average_actions_per_success": statistics.fmean(row["actions"] for row in successes) if successes else None,
            "mean_time_to_success_seconds": statistics.fmean(row["elapsed_seconds"] for row in successes) if successes else None,
            "mean_actions": statistics.fmean(row["actions"] for row in rows),
            "failed_attempts": len(rows) - len(successes), "failed_actions": sum(row["failed_actions"] for row in rows),
            "recovery_attempts": attempts, "recovery_successes": sum(row["recovery_successes"] for row in rows),
            "recovery_success_rate": sum(row["recovery_successes"] for row in rows) / attempts if attempts else None,
            "subgoal_completion_rate": sum(row["subgoals_complete"] for row in rows) / subgoals if subgoals else None,
            "mean_reward": statistics.fmean(row["total_reward"] for row in rows),
            "mean_weight_delta_norm": statistics.fmean(row["update"]["weight_delta_norm"] for row in rows)}
