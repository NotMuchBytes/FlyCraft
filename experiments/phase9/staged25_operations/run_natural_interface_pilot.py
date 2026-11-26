"""Fresh five-condition interface pilot; not a held-out skill evaluation."""
import json
from pathlib import Path
import subprocess
import sys
import time
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from autonomy.evidence import audit_run
from autonomy.experiment import CONDITIONS, atomic_json, digest
from tools.resource_readiness import ResourceReadiness
from tools.supervise_phase9 import gpu_temperature, wait_resources


def main():
    work = Path("C:/Users/anass/Documents/Codex/2026-11-17/continue-developing-the-actual-flycraft-minecraft/work")
    folder = ROOT / "experiments/phase9/fc9_stage25"
    config,state = [json.loads((folder/n).read_text()) for n in ("config.json","state.json")]
    assert state["active_attempt"] is None and (folder/"STOP").exists()
    cache = ROOT / ".runtime/terrain_cache_v3/manifest.json"
    checkpoint = state["current_checkpoint"]
    stop = work / "natural_interface_pilot_STOP"
    pilot = SimpleNamespace(root=ROOT, folder=work, config=dict(checker=dict(launch_ram_mib=1800)),training_worlds=lambda:0)
    results,pose = [],None
    with ResourceReadiness(ROOT,gpu_temperature) as readiness:
        for condition in CONDITIONS:
            if stop.exists():raise RuntimeError("development pilot stopped")
            assert wait_resources(pilot,time.monotonic()+180,readiness=readiness)
            run_id = "terrain25_natural_interface_" + condition
            command = [sys.executable,str(ROOT/"tools/run_phase8_live.py"),"--run-id",run_id,
                "--headless","--pitch-actions","--terrain-actions","--natural-world",
                "--checkpoint",checkpoint["path"],"--frozen-checkpoint",config["frozen_checkpoint"]["path"],
                "--policy-label","terrain_candidate_after_slot350","--frozen-label","foundation338_terrain_transfer",
                "--goals","one_log","--conditions",condition,"--trials","1",
                "--world-seed","202611252601","--layout-start","202611252601","--policy-seed","26001",
                "--seconds","240","--trial-ticks","600","--turn-degrees","15","--forward-ticks","8",
                "--server-heap-mib","384","--client-heap-mib","512","--capture-width","854","--capture-height","480",
                "--launch-cache",str(cache),"--launch-cache-sha256",digest(cache),
                "--work-dir",str(work),"--build-dir",str(ROOT/".runtime/terrain-build1"),"--stop-file",str(stop)]
            if pose is not None:command += ["--natural-start",*map(str,pose)]
            path = ROOT/"experiments/phase9"/run_id
            if not path.exists():
                with (work/(run_id+".log")).open("x",encoding="utf-8") as log:
                    subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=300)
            report = audit_run(path,expected=dict(world_seed=202611252601,policy_rng_seed=26001,
                trial_tick_limit=600,train=False,conditions=[condition],terrain_actions=True,
                checkpoint_sha256=checkpoint["sha256"],frozen_checkpoint_sha256=config["frozen_checkpoint"]["sha256"],
                natural_start_requested=None if condition=="trained" else pose))
            assert report["status"] == "verified" and len(report["episodes"]) == 1
            initial = json.loads((path/"server.jsonl.initial.jsonl").read_text())
            actual = initial["position_xyz_yaw_pitch"]
            if pose is None:pose=actual
            else:assert all(abs(a-b)<1e-4 for a,b in zip(actual,pose))
            assert report["episodes"][0]["weight_delta_norm"] == 0
            atomic_json(path/"independent_audit.json",report)
            results.append(dict(actual_pose=actual,**report["episodes"][0]))
            print(json.dumps(results[-1]),flush=True)
    atomic_json(Path(__file__).with_name("natural_interface_pilot.json"),dict(
        development_interface_test_only=True,seed=202611252601,policy_seed=26001,trial_ticks=600,
        checkpoint=checkpoint,frozen_checkpoint=config["frozen_checkpoint"],matched_pose=pose,
        learning_updates=0,results=results,exact_entity_rng_replay_claimed=False))


if __name__ == "__main__":
    main()
