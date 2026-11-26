"""Audited transport/launcher revision, preserving the original official ledger."""
import argparse
import copy
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from autonomy.evidence import audit_run
from autonomy.experiment import Campaign, CampaignLock, atomic_json, digest, source_manifest

ALLOWED = {"autonomy/experiment.py", "autonomy/official.py", "tools/run_phase9.py", "tools/run_official_phase9.py",
    "tools/run_phase8_live.py", "tools/supervise_phase9.py", "tools/java_launch.py", "tools/launch_cache.py",
    "tools/prepare_launch_cache.py", "tools/resource_readiness.py", "tools/continue_phase9.py",
    "minecraft_mod/src/main/java/org/flycraft/bridge/AtomicFiles.java",
    "minecraft_mod/src/main/java/org/flycraft/bridge/Phase8Harness.java"}
HARNESS = "minecraft_mod/src/main/java/org/flycraft/bridge/Phase8Harness.java"


def check_transport_changes(previous, current, archive, root):
    changed = sorted(key for key in previous["files"].keys() | current["files"].keys()
                     if previous["files"].get(key) != current["files"].get(key))
    if not changed or set(changed) - ALLOWED:
        raise ValueError("revision may change only reviewed transport/launcher files")
    for name in previous["files"]:
        if digest(archive / "source" / name) != previous["files"][name]:
            raise ValueError("original source archive integrity mismatch")
    if HARNESS in changed:
        before = (archive / "source" / HARNESS).read_text(encoding="utf-8")
        after = (root / HARNESS).read_text(encoding="utf-8").replace(
            "AtomicFiles.replace(temporary, controlFile);",
            "Files.move(temporary, controlFile, StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE);")
        if before != after:
            raise ValueError("harness revision must only replace the atomic publication call")
    return changed


def continue_execution(campaign, cache_path, validation_path, reason):
    if not reason or not campaign.official or campaign.state["active_attempt"] is not None \
            or campaign.state["final_policy"] is not None or not (campaign.folder / "STOP").exists():
        raise ValueError("revision requires an explicitly stopped, idle official campaign")
    number = campaign.config.get("execution_revision", 1)
    archive = campaign.folder / "execution_revisions" / f"revision_{number:04d}"
    archived = json.loads((archive / "config.json").read_text())
    if archived != campaign.config or digest(archive / "state.json") != digest(campaign.folder / "state.json"):
        raise ValueError("revision archive differs from stopped campaign")
    previous = json.loads((archive / "source_manifest.json").read_text())
    current = source_manifest(campaign.root)
    changed = check_transport_changes(previous, current, archive, campaign.root)
    validation = json.loads(Path(validation_path).read_text())
    if validation.get("passed") is not True or validation.get("tests_passed", 0) < 149 \
            or validation.get("implementation_sha256") != current["implementation_sha256"] or len(validation.get("runs", [])) < 8:
        raise ValueError("new implementation requires passing tests and a fresh paired live pilot")
    if len({str(Path(run).resolve()) for run in validation["runs"]}) != len(validation["runs"]):
        raise ValueError("pilot runs must be distinct executions")
    for run in validation["runs"]:
        proof = audit_run(run, expected={"implementation_sha256": current["implementation_sha256"], "train": False})
        if proof["status"] != "verified" or len(proof["episodes"]) != 1:
            raise ValueError("pilot evidence is incomplete")
    cache_path = Path(cache_path).resolve()
    cache = json.loads(cache_path.read_text())
    if cache["implementation_sha256"] != current["implementation_sha256"]:
        raise ValueError("validated launch cache has stale source")
    profile = campaign.config["runtime_profile"]
    expected_profile = dict(server_heap_mib=profile["server_heap_mib"], client_heap_mib=profile["client_heap_mib"],
        capture_width=profile["width"], capture_height=profile["height"], graphics_backend="opengl")
    if cache["profile"] != expected_profile:
        raise ValueError("launch cache changes the frozen runtime profile")
    for path, expected in cache["files"].items():
        if digest(path) != expected:
            raise ValueError("launch cache artifact changed")
    revision = {"number": number + 1, "created_unix": time.time(), "reason": reason,
        "implementation_sha256": current["implementation_sha256"], "first_world": campaign.training_worlds() + 1,
        "previous_source_sha256": campaign.config["implementation_sha256"], "previous_archive": str(archive),
        "changed_files": changed, "validation": {"path": str(Path(validation_path).resolve()), "sha256": digest(validation_path)}}
    config = copy.deepcopy(campaign.config)
    config.setdefault("execution_revisions", []).append(dict(number=number,
        implementation_sha256=campaign.config["implementation_sha256"], archive=str(archive), last_world=campaign.training_worlds()))
    config["execution_revision"] = number + 1
    config["implementation_sha256"] = current["implementation_sha256"]
    cache_ref = {"path": str(cache_path), "sha256": digest(cache_path)}
    config["runtime_profile"]["launch_cache"] = cache_ref
    for value in config["runtime_profiles"].values():
        value["launch_cache"] = cache_ref
    config["checker"]["readiness_mode"] = "continuous"
    config["current_execution_revision"] = revision
    atomic_json(archive / "continuation.json", revision)
    atomic_json(campaign.folder / "source_manifest.json", current)
    atomic_json(campaign.folder / "config.json", config)
    campaign.config = config
    campaign.state["config_sha256"] = digest(campaign.folder / "config.json")
    campaign.state.setdefault("execution_revisions", []).append(revision)
    campaign.save()
    request = campaign.folder / "fix_request.json"
    if request.exists():
        resolution = dict(resolved_unix=time.time(), reason=reason, revision=revision,
                          previous_request_sha256=digest(request), original_failure_retained=True)
        atomic_json(campaign.folder / "attention" / f"resolution_revision_{number + 1:04d}.json", resolution)
        request.rename(campaign.folder / "attention" / f"fix_request_resolved_revision_{number + 1:04d}.json")
    return revision


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("campaign", "launch-cache", "validation"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--reason", required=True)
    args = parser.parse_args()
    with CampaignLock(args.campaign):
        campaign = Campaign(args.campaign, project_root=ROOT)
        print(json.dumps(continue_execution(campaign, args.launch_cache, args.validation, args.reason), indent=2))


if __name__ == "__main__":
    main()
