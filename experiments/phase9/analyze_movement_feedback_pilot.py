"""Audit the six real Phase 7.5 motor-feedback trials, preserving negatives."""

from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from autonomy.experiment import verified_terminal_inventory
from experiments.phase9.compare_movement import fixture
from tools.analyze_phase8 import wilson


def read(path):return json.loads(path.read_text())
def single(path):
    rows=path.read_text().splitlines()
    if len(rows)!=1:raise ValueError("expected exactly one episode")
    return json.loads(rows[0])


def main():
    folder=ROOT/"experiments/phase9/phase75_movement_20261029"
    plan=read(folder/"plan.json");results=[];fixtures={}
    for condition,letter in (("input_only","i"),("displacement","d")):
        for case in plan["cases"]:
            run_id=f"p75_move_{letter}_{case['case']:02d}"
            p=ROOT/"experiments/phase9"/run_id
            run=read(p/"run.json");score=single(p/"server.jsonl");outcome=single(p/"controller.jsonl")
            if run["stop_reason"]!="suite_complete" or not run["server_exited_cleanly"] or not single(p/"server.jsonl.delivery.jsonl")["acknowledged"]:
                raise ValueError("incomplete live evidence")
            if run["implementation_sha256"]!=plan["implementation_sha256"] or run["checkpoint_sha256"]!=plan["checkpoint"]["sha256"]:
                raise ValueError("source or checkpoint mismatch")
            if run["movement_feedback"]!=condition or run["policy_rng_seed"]!=case["policy_seed"] or run["world_seed"]!=case["world_seed"] or run["forward_ticks"]!=2 or run["trial_tick_limit"]!=400:
                raise ValueError("planned parameters differ")
            if outcome["train"] or outcome["update"]["weight_delta_norm"] or score["success"]!=outcome["success"]:
                raise ValueError("learning or outcome disagreement")
            inventory,source=verified_terminal_inventory(p,score,outcome)
            if inventory["log"]!=score["inventory"]["log"] or score["success"]!=(inventory["log"]>=1):raise ValueError("inventory mismatch")
            initial=fixture(p)
            if any(initial["inventory"].values()):raise ValueError("nonempty initial inventory")
            fixtures[condition,case["case"]]=initial
            acks=[json.loads(line)["data"]["ack"] for line in (p/"headless.jsonl").read_text().splitlines() if json.loads(line)["event"]=="action_end"]
            forward=[a for a in acks if a["action"]=="FORWARD" and a["status"] in ("success","failed")]
            stalled=[a for a in forward if not a["movement_confirmed"]]
            required=case["case"] in plan["recorded_case_numbers"]
            if required:
                video=run["milestone_video"]
                if run["milestone_video_status"]!="verified" or not video["episode_coverage_complete"] or not run["client_exited_cleanly"] or hashlib.sha256(Path(video["path"]).read_bytes()).hexdigest()!=video["sha256"]:raise ValueError("milestone video missing")
            elif run["spectator"] or run["recording"] is not None:raise ValueError("routine trial recorded")
            results.append({"run_id":run_id,"condition":condition,"case":case["case"],"success":score["success"],"actions":outcome["actions"],"ticks":score["ticks"],"inventory":inventory,"terminal_inventory_source":source,"stalled_forward_actions":len(stalled),"stalled_reported_success":sum(a["status"]=="success" for a in stalled),"blocked_errors":sum(a["error"]=="movement_blocked" for a in forward),"recovery_events":outcome["recovery_events"],"failed_actions":outcome["failed_actions"],"milestone_recorded":required,"worker_wall_seconds":run["elapsed_seconds"],"gpu_max_c":run["maximum_sampled_gpu_c"],"minimum_available_ram_mib":run["minimum_sampled_available_ram_mib"]})
    for case in plan["cases"]:
        if fixtures["input_only",case["case"]]!=fixtures["displacement",case["case"]]:raise ValueError("paired relative fixtures differ")
    if hashlib.sha256(Path(plan["checkpoint"]["path"]).read_bytes()).hexdigest()!=plan["checkpoint"]["sha256"]:raise ValueError("checkpoint changed")
    summary={}
    for mode in plan["conditions"]:
        rows=[r for r in results if r["condition"]==mode];s=sum(r["success"] for r in rows)
        summary[mode]={"successes":s,"episodes":3,"wilson_95":wilson(s,3),"mean_actions":sum(r["actions"] for r in rows)/3,"mean_game_seconds":sum(r["ticks"]/20 for r in rows)/3,"stalled_reported_success":sum(r["stalled_reported_success"] for r in rows),"blocked_errors":sum(r["blocked_errors"] for r in rows)}
    data={"stage":"adaptive development, reused failure layouts","plan":plan,"summary":summary,"trials":results,"paired_relative_fixtures_match":True,"full_rng_matched":False,"policy_updated":False,"neural_learning_gain_established":False,"causal_generalization_gain_established":False,"required_milestone_mp4s":2,"missing_required_milestone_mp4s":0}
    with (folder/"analysis.json").open("x",encoding="utf-8",newline="\n") as f:json.dump(data,f,indent=2);f.write("\n")
    print(json.dumps(summary,indent=2))


if __name__=="__main__":main()
