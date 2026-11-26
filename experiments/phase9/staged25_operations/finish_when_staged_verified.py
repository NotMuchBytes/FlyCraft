"""Authorized shutdown companion; a partial curriculum never means done."""
import importlib.util
from pathlib import Path
import subprocess

legacy_path = Path(__file__).resolve().parents[1] / "fc9_20261125_operations/finish_when_verified.py"
spec = importlib.util.spec_from_file_location("flycraft_shutdown_companion", legacy_path)
legacy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(legacy)
original_verify = legacy.verify_artifacts


def completion_ready(folder):
    folder = Path(folder)
    if any((folder / name).exists() for name in ("STOP", "fix_request.json")):
        return False
    config, state, executor = (legacy.read(folder / name) for name in ("config.json", "state.json", "executor.json"))
    if config.get("curriculum_schema") != "staged-terrain-v1" or config.get("world_limit") != 10000 \
            or not config.get("official_experiment_authorized") or config.get("pending_skills") \
            or executor.get("status") != "training_budget_complete" \
            or state.get("status") != "curriculum_complete" or state.get("active_attempt") is not None \
            or not state.get("final_policy"):
        return False
    if legacy.digest(folder / "config.json") != state["config_sha256"]:
        raise ValueError("curriculum configuration changed")
    if state["final_policy"] != state["current_checkpoint"] or executor["final_checkpoint"] != state["final_policy"]:
        raise ValueError("final curriculum checkpoint mismatch")
    if state["curriculum_index"] != len(config["supported_stages"]) or any(
            not state["gates"].get(stage["id"], {}).get("passed") for stage in config["supported_stages"]):
        return False
    rows = [a for a in state["attempts"] if a["split"] == "training"]
    if any(type(a.get("generated_world_instances")) is not int or a["generated_world_instances"] not in (0, 1) for a in rows):
        raise ValueError("unfinished or invalid training-world count")
    created = [a for a in rows if a["generated_world_instances"] == 1]
    start = config["foundation"]["foundation_world_instances"]
    if len(created) + start != 10000 or sorted(a["official_world_number"] for a in created) != list(range(start+1, 10001)):
        return False
    catalog = legacy.read(folder / "seeds.json")
    if legacy.digest(folder / "seeds.json") != config["catalog_sha256"]:
        raise ValueError("curriculum seed catalog changed")
    for a in created:
        if a["world_seed"] != catalog["training"][a["official_world_number"]-start-1]:
            raise ValueError("curriculum seed differs from frozen catalog")
    for number in config["recording_milestones"]:
        matches = [a for a in created if a["official_world_number"] == number]
        if len(matches) != 1 or matches[0]["status"] != "committed" or not matches[0].get("video_required"):
            raise ValueError("missing curriculum milestone")
    return True


def verify_artifacts(folder, ffmpeg):
    proof = original_verify(folder, ffmpeg)
    config = legacy.read(Path(folder) / "config.json")
    handoff = config["foundation_handoff"]
    if legacy.digest(handoff["path"]) != handoff["sha256"]:
        raise ValueError("foundation handoff changed")
    archive = Path(handoff["path"]).parent
    foundation = legacy.read(handoff["path"])
    for name, sha in foundation["files"].items():
        if legacy.digest(archive / name) != sha:
            raise ValueError("preserved foundation snapshot changed")
    if legacy.digest(foundation["checkpoint"]["path"]) != foundation["checkpoint"]["sha256"]:
        raise ValueError("foundation checkpoint changed")
    # Recheck the original raw episode hashes and decode its old milestones.
    verified = 0
    for a in legacy.read(archive / "state.json")["attempts"]:
        if a["status"] != "committed":
            continue
        audit = legacy.read(a["checker_report"])
        if audit["status"] != "verified" or audit["run_id"] != a["run_id"]:
            raise ValueError("foundation episode audit mismatch")
        for name, sha in audit["evidence_sha256"].items():
            if Path(name).name != name or legacy.digest(Path(a["results"]) / name) != sha:
                raise ValueError("foundation raw evidence changed")
        if a.get("video_required"):
            video = a["video"]
            if legacy.digest(video["path"]) != video["sha256"] or not video.get("full_decode_verified"):
                raise ValueError("foundation milestone changed")
            subprocess.run([str(ffmpeg), "-nostdin", "-v", "error", "-xerror", "-threads", "2",
                "-i", video["path"], "-map", "0:v:0", "-f", "null", "-"], check=True, capture_output=True, timeout=300)
        verified += 1
    proof["foundation_verified_episodes"] = verified
    proof["foundation_handoff"] = handoff
    return proof


if __name__ == "__main__":
    legacy.completion_ready = completion_ready
    legacy.verify_artifacts = verify_artifacts
    legacy.main()
