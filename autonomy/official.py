"""Bind official workers to durable plans and reclaim verified disposable worlds."""

from pathlib import Path
import shutil
import time

from .experiment import Campaign, source_manifest


def validate_worker(args, root, *, campaign=None):
    if campaign is None:
        import json
        config = json.loads(args.campaign_manifest.read_text(encoding="utf-8"))
        if config.get("curriculum_schema") == "staged-terrain-v1":
            from .staged import StagedCampaign
            campaign = StagedCampaign(args.campaign_manifest.parent, project_root=root)
        else:
            campaign = Campaign(args.campaign_manifest.parent, project_root=root)
    if not campaign.official or campaign.config["world_limit"] != 10000:
        raise ValueError("worker requires an authorized official 10000-world plan")
    index = campaign.state["active_attempt"]
    if index is None:
        raise ValueError("official worker has no durable active attempt")
    attempt = campaign.state["attempts"][index]
    profile = campaign.runtime_profile(attempt["goal"])
    cache = profile.get("launch_cache")
    if cache:
        if getattr(args, "launch_cache", None) is None or Path(args.launch_cache).resolve() != Path(cache["path"]).resolve() \
                or args.launch_cache_sha256 != cache["sha256"]:
            raise ValueError("official launch cache differs from frozen profile")
    elif getattr(args, "launch_cache", None) is not None:
        raise ValueError("unplanned official launch cache")
    expected = {"run_id": attempt["run_id"], "official_world_number": attempt["official_world_number"],
        "world_seed": attempt["world_seed"], "layout_start": attempt["layout_seed"],
        "policy_seed": attempt["policy_seed"], "goals": attempt["goal"], "conditions": attempt["condition"],
        "train": attempt["train"], "headless": True, "trials": 1, "camera_mode": "bounded", "pitch_actions": True,
        "turn_degrees": profile["turn_degrees"], "forward_ticks": profile["forward_ticks"],
        "trial_ticks": profile["trial_ticks"], "three_tree_fixture": profile["three_tree_fixture"],
        "remember_mined_columns": profile["remember_mined_columns"], "spectator": attempt["video_required"],
        "milestone": attempt["episode_number"] if attempt["video_required"] else None,
        "operator_fault": "none", "natural_world": False, "blocked_forward_fixture": False,
        "explore_forward": False, "jump_on_blocked_forward": False, "camera_probe": False,
        "movement_feedback": "displacement", "layout_seeds": None, "natural_start": None,
        "unplaced_table_fixture": False, "graphics_backend": "opengl", "launcher": "direct",
        "server_heap_mib": profile["server_heap_mib"], "client_heap_mib": profile["client_heap_mib"],
        "capture_width": profile["width"], "capture_height": profile["height"]}
    if campaign.config.get("curriculum_schema") == "staged-terrain-v1":
        expected.update(terrain_actions=True, terrain_step_fixture=profile["terrain_step_fixture"],
                        natural_world=profile["natural_world"], natural_start=profile.get("natural_start"))
    elif getattr(args, "terrain_actions", False) or getattr(args, "terrain_step_fixture", False):
        raise ValueError("terrain interface is absent from the original frozen plan")
    if (attempt["split"] != "training" and campaign.config.get("curriculum_schema") != "staged-terrain-v1") or attempt["status"] != "running":
        raise ValueError("official worker must own a running training attempt")
    for key, value in expected.items():
        if getattr(args, key) != value:
            raise ValueError(f"official worker differs from frozen plan: {key}")
    if args.minimum_available_ram_mib < 768 or args.minimum_free_disk_mib < 2048:
        raise ValueError("official resource guards cannot be reduced")
    for path, expected_path in ((args.checkpoint, attempt["checkpoint"]["path"]),
            (args.frozen_checkpoint, campaign.config["frozen_checkpoint"]["path"]),
            (args.stop_file, campaign.folder / "STOP"),
            (args.work_dir / args.run_id, attempt["runtime"])):
        if path is None or Path(path).resolve() != Path(expected_path).resolve():
            raise ValueError("official worker path differs from durable attempt")
    if source_manifest(root)["implementation_sha256"] != campaign.config["implementation_sha256"]:
        raise ValueError("official worker source changed")
    return {"experiment_stage": attempt.get("experiment_stage", "official_training"), "campaign_name": campaign.config["name"],
            "official_world_number": attempt["official_world_number"]}


def cleanup_world(campaign, attempt, work_dir):
    """Delete only the verified routine world's directory; preserve all evidence."""
    if attempt["status"] != "committed" or attempt.get("checker_status") != "verified" \
            or attempt.get("video_required", True) or attempt.get("world_cleanup"):
        return False
    root = Path(work_dir).resolve()
    runtime = root / attempt["run_id"]
    target = runtime / "server/world"
    if Path(attempt["runtime"]).absolute() != runtime or target.resolve() != target \
            or not target.is_relative_to(root) or target == root:
        raise ValueError("refusing cleanup outside the exact disposable world path")
    for path in (root, runtime, runtime / "server", target):
        if path.is_symlink() or path.is_junction():
            raise ValueError("refusing linked disposable world path")
    if target.exists():
        for path in target.rglob("*"):
            if path.is_symlink() or path.is_junction():
                raise ValueError("refusing links inside disposable world")
        shutil.rmtree(target)
    attempt["world_cleanup"] = {"path": str(target), "completed_unix": time.time(),
                                "basis": "independently verified routine episode; logs/checkpoint retained"}
    campaign.save()
    return True
