"""Reviewed pose-matching revision; refuses actor, reward or seed changes."""
import json
from pathlib import Path
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from autonomy.experiment import atomic_json,digest,source_manifest
from autonomy.staged import StagedCampaign


def main():
    ops = Path(__file__).resolve().parent
    folder = ROOT/"experiments/phase9/fc9_stage25"
    config,state = [json.loads((folder/n).read_text()) for n in ("config.json","state.json")]
    assert (folder/"STOP").exists() and state["active_attempt"] is None
    assert len(state["attempts"]) == 12 and all(a["status"] == "committed" for a in state["attempts"])
    assert config.get("execution_revision",1) == 1
    pilot = json.loads((ops/"natural_interface_pilot.json").read_text())
    assert pilot["checkpoint"] == state["current_checkpoint"] and pilot["learning_updates"] == 0
    assert {r["condition"] for r in pilot["results"]} == {"trained","frozen","uniform","no_neural","shuffled"}
    assert all(r["actual_pose"] == pilot["matched_pose"] and r["weight_delta_norm"] == 0 for r in pilot["results"])
    tests = ops/"revision2_tests.txt"
    assert "Ran 166 tests" in tests.read_text() and tests.read_text().rstrip().endswith("OK")
    old = json.loads((folder/"source_manifest.json").read_text())
    new = source_manifest(ROOT)
    changed = sorted(k for k in set(old["files"])|set(new["files"]) if old["files"].get(k) != new["files"].get(k))
    assert changed == ["autonomy/evidence.py","autonomy/official.py","autonomy/staged.py","tools/run_phase9.py"]
    cache = ROOT/".runtime/terrain_cache_v4/manifest.json"
    assert json.loads(cache.read_text())["implementation_sha256"] == new["implementation_sha256"]
    archive = ops/"revision_0001_at350"
    archive.mkdir(exist_ok=False)
    for name in ("config.json","state.json","summary.json","source_manifest.json","seeds.json"):
        shutil.copy2(folder/name,archive/name)
    revision = dict(execution_revision=1,implementation_sha256=config["implementation_sha256"],
        config_sha256=digest(folder/"config.json"),archive=str(archive),retired_after_world=350,
        successor_reason="Match natural control poses to native trained reference; gate all four retained wood goals at their original thresholds",
        actor_or_reward_changed=False,training_seeds_changed=False)
    config["execution_revisions"] = [revision]
    config["execution_revision"] = 2
    config["implementation_sha256"] = new["implementation_sha256"]
    config["runtime_profile"]["launch_cache"] = dict(path=str(cache),sha256=digest(cache))
    for name in changed:
        p=ops/"revision2_source_snapshot"/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,p)
    atomic_json(ops/"revision2_source_manifest.json",new)
    atomic_json(ops/"revision2_review.json",dict(changed_files=changed,prior=revision,
        implementation_sha256=new["implementation_sha256"],pilot_sha256=digest(ops/"natural_interface_pilot.json"),
        tests_sha256=digest(tests),reviewed_unix=time.time(),policy_checkpoint_unchanged=state["current_checkpoint"]))
    atomic_json(folder/"source_manifest.json",new)
    atomic_json(folder/"config.json",config)
    state["config_sha256"] = digest(folder/"config.json")
    atomic_json(folder/"state.json",state)
    campaign=StagedCampaign(folder,project_root=ROOT);campaign.save()
    shutil.copy2(folder/"config.json",ops/"revision2_config.json")
    print("Reviewed revision 2 installed at world 350; STOP remains set.")


if __name__ == "__main__":
    main()
