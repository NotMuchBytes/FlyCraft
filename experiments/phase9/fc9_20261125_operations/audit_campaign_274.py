"""Read-only snapshot audit; never changes the live frozen campaign."""
import collections
import json
from pathlib import Path
import statistics
import sys
import time

ROOT = Path("C:/Users/anass/Documents/FlyCraft")
sys.path.insert(0, str(ROOT))
import numpy as np
from autonomy import AutonomousAgent
from autonomy.evidence import audit_run
from autonomy.experiment import Campaign, atomic_json, digest, source_manifest

folder = ROOT / "experiments/phase9/fc9_20261125"
campaign = Campaign(folder, project_root=ROOT)
attempts = [a for a in campaign.state["attempts"] if a["status"] == "committed" and a["official_world_number"] <= 274]
assert len(attempts) == 274
destination = ROOT / "experiments/phase9/fc9_20261125_operations/progress_00274.json"
if destination.exists():
    raise FileExistsError(destination)
reports, errors = [], []
checkpoint = campaign.config["initial_checkpoint"]
previous, _ = AutonomousAgent.load(checkpoint["path"], campaign.table)
metas = []
for attempt in attempts:
    try:
        profile = campaign.runtime_profile(attempt["goal"])
        expected = dict(experiment_stage="official_training", campaign_name=campaign.config["name"],
            official_world_number=attempt["official_world_number"], world_seed=attempt["world_seed"],
            implementation_sha256=campaign.config["implementation_sha256"], train=True,
            checkpoint_sha256=checkpoint["sha256"], frozen_checkpoint_sha256=campaign.config["frozen_checkpoint"]["sha256"],
            goals=[attempt["goal"]], conditions=["trained"], policy_rng_seed=attempt["policy_seed"],
            headless=True, spectator=attempt["video_required"], camera_mode="bounded", turn_degrees=15,
            pitch_actions=True, forward_ticks=2, trial_tick_limit=profile["trial_ticks"],
            remember_mined_columns=profile["remember_mined_columns"], jump_on_blocked_forward=False,
            explore_forward=False, movement_feedback="displacement")
        if attempt["checkpoint"] != checkpoint:
            raise ValueError("checkpoint input chain mismatch")
        report = audit_run(attempt["results"], expected=expected)
        original = json.loads(Path(attempt["checker_report"]).read_text())
        if report["status"] != "verified" or report["evidence_sha256"] != original["evidence_sha256"]:
            raise ValueError("episode proof changed since commit")
        next_checkpoint = attempt["checkpoint_after"]
        if digest(next_checkpoint["path"]) != next_checkpoint["sha256"]:
            raise ValueError("saved checkpoint hash mismatch")
        restored, _ = AutonomousAgent.load(next_checkpoint["path"], campaign.table)
        delta = float(np.linalg.norm(restored.policy.weights - previous.policy.weights))
        if not np.isfinite(restored.policy.weights).all() or not np.isclose(delta, attempt["update"]["weight_delta_norm"], rtol=1e-9, atol=1e-12):
            raise ValueError("saved readout delta mismatch")
        runtime = Path(attempt["runtime"])
        if attempt["video_required"]:
            if not (runtime / "server/world").is_dir():
                raise ValueError("milestone world was not preserved")
        elif not attempt.get("world_cleanup") or (runtime / "server/world").exists():
            raise ValueError("routine world cleanup not recorded/completed")
        metas.append(json.loads((Path(attempt["results"]) / "run.json").read_text()))
        checkpoint, previous = next_checkpoint, restored
        reports.append(report)
    except Exception as error:
        errors.append(dict(world=attempt["official_world_number"], error=str(error), type=type(error).__name__))
    if attempt["official_world_number"] % 50 == 0:
        print(json.dumps(dict(audited=attempt["official_world_number"], errors=len(errors))), flush=True)

wall = attempts[-1]["finished_unix"] - attempts[0]["started_unix"]
goals = {}
for goal in campaign.config["goal_schedule"]:
    chosen = [a for a in attempts if a["goal"] == goal]
    episodes = [r["episodes"][0] for r in reports if r["episodes"][0]["goal"] == goal]
    goals[goal] = dict(trials=len(chosen), successes=sum(a["success"] for a in chosen),
        mean_actions=statistics.mean(a["actions"] for a in chosen),
        mean_game_seconds=statistics.mean(a["ticks"] / 20 for a in chosen),
        mean_worker_wall_seconds=statistics.mean(a["wall_seconds"] for a in chosen),
        failures=dict(collections.Counter(e["failure_mode"] for e in episodes if not e["success"])))

videos = [dict(world=a["official_world_number"], goal=a["goal"], success=a["success"], video=a["video"],
    export=m.get("milestone_video_export")) for a, m in zip(attempts, metas) if a.get("video_required")] if not errors else []
output = dict(schema=1, stage="official_training", campaign="fc9_20261125", snapshot_unix=time.time(),
    read_only=True, snapshot_worlds=274, verified_episodes=len(reports), successes=sum(a["success"] for a in attempts),
    training_updates=sum(a["training_applied"] for a in attempts),
    training_suppression=dict(collections.Counter(str(a.get("training_suppressed")) for a in attempts if a.get("training_suppressed"))),
    evaluation_episodes=0, goal_counts=goals, milestone_videos=videos,
    routine_worlds_reclaimed=sum(not a["video_required"] for a in attempts),
    observed_elapsed_seconds_including_readiness=wall, observed_worlds_per_hour_including_readiness=274 * 3600 / wall,
    minimum_available_ram_mib=min(m["minimum_sampled_available_ram_mib"] for m in metas),
    maximum_gpu_temperature_c=max(m["maximum_sampled_gpu_c"] for m in metas if m["maximum_sampled_gpu_c"] is not None),
    cpu_temperature_available=False, source_matches=source_manifest(ROOT)["implementation_sha256"] == campaign.config["implementation_sha256"],
    implementation_sha256=campaign.config["implementation_sha256"], snapshot_checkpoint=checkpoint,
    final_evaluation_untouched=True, training_is_not_final_reliability=True, errors=errors, reports=reports)
atomic_json(destination, output)
print(json.dumps({key: value for key, value in output.items() if key not in ("reports", "milestone_videos")}, indent=2))
raise SystemExit(bool(errors))
