"""Conservative post-crash recovery: no invented score or model update."""
import argparse
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from autonomy.experiment import CampaignLock,atomic_json
from autonomy.staged import StagedCampaign
import psutil


def unscored_technical(attempt,results):
    """Any scored/partial score, missing video or contradictory evidence parks."""
    if attempt.get("video_required") or attempt.get("verified_game_episodes"):return False
    score=Path(results)/"server.jsonl"
    if score.exists() and score.read_text(encoding="utf-8").strip():return False
    meta=Path(results)/"run.json"
    if not meta.exists():return True
    run=json.loads(meta.read_text())
    return run.get("completed")==0 and run.get("stop_reason") in {
        "available_ram_guard","free_disk_guard","gpu_temperature_guard","coordinator_lost","wall_budget"}


def recover(plan):
    folder=Path(plan["campaign"])
    with CampaignLock(folder):
        campaign=StagedCampaign(folder,project_root=ROOT)
        index=campaign.state["active_attempt"]
        if index is None:
            if not campaign.state["attempts"] or campaign.state["attempts"][-1]["status"]!="interrupted":return 2
            index=len(campaign.state["attempts"])-1
            outcome=campaign.state["attempts"][index]
        else:
            # Campaign.recover also rejects a still-live worker with the same birth time.
            outcome=campaign.recover()
        if outcome["status"]=="committed":return 0
        if not unscored_technical(outcome,outcome["results"]):
            if not (folder/"fix_request.json").exists():
                atomic_json(folder/"fix_request.json",dict(code="startup_recovery_review",run_id=outcome["run_id"],
                    reason="scored, recorded, partial or contradictory episode needs review; no retry authorized"))
            return 2
        prior=[a for a in campaign.state["attempts"] if a.get("unscored_technical_retry")]
        if len([a for a in prior if time.time()-a.get("finished_unix",0)<3600])>=3:
            atomic_json(folder/"fix_request.json",dict(code="startup_retry_limit",reason="three technical retries in one hour"))
            return 2
        campaign.state["attempts"][index]["unscored_technical_retry"]=True
        campaign.state["attempts"][index]["recovery_basis"]="owned worker lost; no scored native episode; previous committed checkpoint retained"
        campaign.save()
        fix=folder/"fix_request.json"
        if fix.exists():
            archive=folder/"recovery_archive";archive.mkdir(exist_ok=True)
            fix.rename(archive/f"{outcome['run_id']}_{time.time_ns()}_fix_request.json")
        print(json.dumps(dict(run_id=outcome["run_id"],generated_world_instances=outcome["generated_world_instances"],
            checkpoint=campaign.state["current_checkpoint"],no_score_invented=True,no_action_replayed=True)))
        return 0


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--plan",type=Path,required=True);args=parser.parse_args()
    try:raise SystemExit(recover(json.loads(args.plan.read_text())))
    except (OSError,ValueError,RuntimeError,psutil.Error) as error:print(str(error),file=sys.stderr);raise SystemExit(2)
