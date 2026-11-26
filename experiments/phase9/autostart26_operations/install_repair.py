"""Freeze one user-authorized repair round; keep the failed benchmark immutable."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from autonomy.experiment import CampaignLock,atomic_json,digest,seed_catalog,source_manifest
from autonomy.staged import StagedCampaign,gate_report
from tools.launch_cache import freeze_cache


def main():
    folder=ROOT/"experiments/phase9/fc9_stage25";ops=Path(__file__).resolve().parent
    with CampaignLock(folder):
        config,state,catalog,old_source=[json.loads((folder/n).read_text()) for n in ("config.json","state.json","seeds.json","source_manifest.json")]
        assert state["active_attempt"] is None and state["status"]=="stage_gate_failed"
        assert config.get("execution_revision")==2 and len(state["attempts"])==334
        assert all(a["status"]=="committed" for a in state["attempts"])
        gate=gate_report(state["attempts"],"terrain")
        assert gate==state["gates"]["terrain"] and gate["complete"] and not gate["passed"]
        assert gate["retention_successes"]==dict(one_log=20,three_logs=30,planks=25,wooden_pickaxe=29)
        tests=ops/"release_tests.txt"
        assert "Ran 177 tests" in tests.read_text() and tests.read_text().rstrip().endswith("OK")
        new_source=source_manifest(ROOT)
        changed=sorted(k for k in set(new_source["files"])|set(old_source["files"]) if new_source["files"].get(k)!=old_source["files"].get(k))
        assert changed==["autonomy/staged.py","tools/power_guard.py","tools/run_phase9.py","tools/run_staged_curriculum.py"]
        archive=ops/"before_repair_402";archive.mkdir(exist_ok=False)
        for n in ("config.json","state.json","summary.json","source_manifest.json","seeds.json"):
            shutil.copy2(folder/n,archive/n)
        excluded=set()
        for values in catalog.values():
            if isinstance(values,list):excluded.update(v for v in values if type(v)is int)
        for phase in ("phase8","phase9"):
            for meta in (ROOT/"experiments"/phase).glob("*/run.json"):
                run=json.loads(meta.read_text())
                if type(run.get("world_seed"))is int:excluded.add(run["world_seed"])
                excluded.update(run.get("layout_seeds") or [])
                if type(run.get("layout_start"))is int:excluded.add(run["layout_start"])
        fresh=seed_catalog(2026112601,training=1,pilot=1,evaluation=150,exclude=excluded)["eval_a"]
        assert not(set(fresh)&excluded) and len(set(fresh))==150
        catalog["repair_terrain_1"]=fresh
        cache=ROOT/".runtime/terrain_cache_v5";cache.mkdir(exist_ok=False)
        old_cache=Path(config["runtime_profile"]["launch_cache"]["path"]).parent
        for name in ("runServer.json","runClient.json"):shutil.copy2(old_cache/name,cache/name)
        cache_info=freeze_cache(cache,ROOT,json.loads((old_cache/"manifest.json").read_text())["profile"])
        previous=dict(execution_revision=2,implementation_sha256=config["implementation_sha256"],config_sha256=digest(folder/"config.json"),
            archive=str(archive),retired_after_world=402,reason="user requested resume and automatic restart; preserve failed gate and train bounded retention repair")
        config["execution_revisions"].append(previous)
        config.update(execution_revision=3,implementation_sha256=new_source["implementation_sha256"])
        config["runtime_profile"]["launch_cache"]=cache_info
        config["repair_rounds"]={"terrain":{"1":dict(training_worlds=32,
            training_schedule=["retention_one_log","retention_one_log","retention_one_log","primary"],
            evaluation_catalog="repair_terrain_1",authorization="User: run and make a fail safe that as soon as the pc is on it carries on",authorized_date="2026-11-26")}}
        state.setdefault("round_history",[]).append(dict(stage="terrain",round=0,gate=gate,checkpoint=state["current_checkpoint"],archive=str(archive)))
        state["curriculum_rounds"]={"terrain":1};state["status"]="repair_ready"
        atomic_json(folder/"seeds.json",catalog);config["catalog_sha256"]=digest(folder/"seeds.json")
        atomic_json(folder/"source_manifest.json",new_source);atomic_json(folder/"config.json",config)
        state["config_sha256"]=digest(folder/"config.json");atomic_json(folder/"state.json",state)
        campaign=StagedCampaign(folder,project_root=ROOT);campaign.save()
        for name in changed:
            destination=ops/"source_revision3"/name;destination.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,destination)
        for name in ("config.json","source_manifest.json"):
            shutil.copy2(folder/name,ops/("revision3_"+name))
        atomic_json(ops/"repair_authorization.json",dict(previous=previous,changed_modules=changed,actor_reward_changed=False,
            original_training_seeds_unchanged=True,fresh_evaluation_seed_count=150,prior_gate_preserved=True,
            checkpoint_before_repair=state["current_checkpoint"],created_unix=time.time()))
        print("Repair round frozen: 32 training worlds, fresh 270-episode evaluation, gates unchanged.")


if __name__=="__main__":main()
