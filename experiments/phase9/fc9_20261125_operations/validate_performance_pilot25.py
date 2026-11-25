"""Audit fresh development runs and keep launcher timing apart from gameplay."""
import collections
import json
from pathlib import Path
import statistics
import sys

ROOT = Path("C:/Users/anass/Documents/FlyCraft")
sys.path.insert(0, str(ROOT))
from autonomy.evidence import audit_run
from autonomy.experiment import atomic_json, digest, source_manifest

BASE = Path(__file__).parent
finished = json.loads((BASE / "performance_pilot25_finished.json").read_text())
destination = ROOT / "experiments/phase9/fc9_20261125_operations/performance_validation_0002.json"
if destination.exists():
    raise FileExistsError(destination)
source = source_manifest(ROOT)["implementation_sha256"]
tests = BASE / "performance_revision_tests_all_20261125.txt"
assert "Ran 155 tests" in tests.read_text() and tests.read_text().rstrip().endswith("OK")
results, table, errors, snapshots = [], [], [], collections.defaultdict(list)
for plan in finished["plans"]:
    state = json.loads((Path(plan["folder"]) / "state.json").read_text())
    rows = state["attempts"]
    assert len(rows) == plan["trials"]
    group = []
    for row in rows:
        if row["status"] != "committed" or row["train"] or row["update"]["weight_delta_norm"] != 0:
            raise ValueError("pilot altered learning or has unverified evidence")
        meta = json.loads((Path(row["results"]) / "run.json").read_text())
        proof = audit_run(row["results"], expected=dict(implementation_sha256=source, train=False,
            goals=[plan["goal"]], conditions=["trained"], world_seed=row["world_seed"],
            policy_rng_seed=row["policy_seed"], checkpoint_sha256=row["checkpoint"]["sha256"],
            headless=True, camera_mode="bounded", pitch_actions=True, forward_ticks=2,
            movement_feedback="displacement", jump_on_blocked_forward=False, explore_forward=False))
        assert proof["status"] == "verified"
        episode = proof["episodes"][0]
        initial = json.loads((Path(row["results"]) / "server.jsonl.initial.jsonl").read_text())
        pose = initial["position_xyz_yaw_pitch"]
        relative = dict(y=pose[1], yaw=pose[3], pitch=pose[4], inventory=initial["inventory"], game_mode=initial["game_mode"],
            blocks=sorted([(tuple(block["position"][i] - pose[i] for i in range(3)), block["state"]) for block in initial["fixture_blocks"]]))
        snapshots[(plan["goal"], row["layout_seed"])].append(relative)
        value = dict(results=row["results"], run_id=row["run_id"], goal=plan["goal"], mode=plan["mode"],
            success=row["success"], actions=row["actions"], policy_seed=row["policy_seed"], seed=row["world_seed"],
            initial_absolute_pose=pose, relative_initial_geometry=relative,
            worker_seconds=row["wall_seconds"], episode_seconds=episode["elapsed_seconds"],
            worker_overhead_seconds=row["wall_seconds"]-episode["elapsed_seconds"],
            coordinator_cycle_seconds=row["coordinator_cycle_seconds"],
            outside_worker_seconds=row["coordinator_cycle_seconds"]-row["wall_seconds"],
            preparation_mode=meta["launch_preparation_mode"], video=row.get("video"),
            export=meta.get("milestone_video_export"), failure_mode=episode["failure_mode"], proof=proof)
        group.append(value)
        results.append(value)
    table.append(dict(goal=plan["goal"], mode=plan["mode"], trials=len(group), successes=sum(r["success"] for r in group),
        total_coordinator_seconds=plan["total_coordinator_seconds"],
        mean_worker_overhead_seconds=statistics.mean(r["worker_overhead_seconds"] for r in group),
        first_outside_worker_seconds=group[0]["outside_worker_seconds"],
        warmed_outside_worker_seconds=[r["outside_worker_seconds"] for r in group[1:]]))
for key, variants in snapshots.items():
    if any(value != variants[0] for value in variants[1:]):
        errors.append(dict(case=str(key), reason="relative initial geometry differs"))
output = dict(schema=1, passed=not errors, implementation_sha256=source, tests_passed=155,
    tests_log=dict(path=str(tests), sha256=digest(tests)), runs=[r["results"] for r in results],
    configuration_matched=True, exact_replay=False, absolute_poses_not_fixed=True,
    relative_initial_geometry_equal=not errors, learning_updates=0,
    initial_checkpoint_sha256=results[0]["proof"]["evidence_sha256"].get("source_manifest.json"),
    timing=table, episodes=results, errors=errors)
# Bind the actual checkpoint independently of per-episode evidence manifests.
output["initial_checkpoint_sha256"] = digest(finished["initial_checkpoint"])
atomic_json(destination, output)
print(json.dumps(dict(passed=output["passed"], tests=155, timing=table, errors=errors), indent=2))
raise SystemExit(bool(errors))
