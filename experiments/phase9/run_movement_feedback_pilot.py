"""Bounded, paired Phase 7.5 development check; policy actions are never scripted."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import psutil

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from autonomy.experiment import atomic_json, source_manifest


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--init",action="store_true")
    parser.add_argument("--condition",choices=("input_only","displacement"))
    for name in ("work-dir","build-dir","obs-control-dir","video-export-dir"):
        parser.add_argument("--"+name,type=Path)
    args=parser.parse_args()
    folder=ROOT/"experiments/phase9/phase75_movement_20261029"
    if args.init:
        folder.mkdir(exist_ok=False)
        old=json.loads((ROOT/"experiments/phase9/dev_log30_milestones_20261029/state.json").read_text())
        cases=[a for a in old["attempts"] if a["episode_number"] in (9,16,17)]
        plan={"stage":"adaptive development, previously failed fixtures, not final benchmark",
              "created_unix":time.time(),"implementation_sha256":source_manifest(ROOT)["implementation_sha256"],
              "checkpoint":old["current_checkpoint"],"goal":"one_log","forward_ticks":2,"trial_ticks":400,
              "conditions":["input_only","displacement"],"recorded_case_numbers":[1],
              "cases":[{"case":i+1,"world_seed":a["world_seed"],"policy_seed":a["policy_seed"],
                        "historical_run_id":a["run_id"]} for i,a in enumerate(cases)],
              "learning":False,"full_world_entity_rng_matched":False,
              "stopping_rule":"All three cases per condition, no success-based early stopping; stop on infrastructure, recording, resource or usage failures. No retries or unattended queue."}
        atomic_json(folder/"plan.json",plan);print(folder);return
    if args.condition is None or any(getattr(args,n) is None for n in ("work_dir","build_dir","obs_control_dir","video_export_dir")):
        parser.error("condition and all four directories are required")
    plan=json.loads((folder/"plan.json").read_text())
    if source_manifest(ROOT)["implementation_sha256"]!=plan["implementation_sha256"]:
        raise ValueError("source changed after pilot plan")
    deadline=time.monotonic()+850
    for case in plan["cases"]:
        remaining=int(deadline-time.monotonic())-15
        if remaining<120: raise RuntimeError("bounded pilot wall budget exhausted")
        run_id=f"p75_move_{'i' if args.condition=='input_only' else 'd'}_{case['case']:02d}"
        command=[sys.executable,str(ROOT/"tools/run_phase8_live.py"),"--run-id",run_id,"--headless",
                 "--checkpoint",plan["checkpoint"]["path"],"--goals","one_log","--conditions","trained",
                 "--world-seed",str(case["world_seed"]),"--layout-start",str(case["world_seed"]),
                 "--policy-seed",str(case["policy_seed"]),"--seconds",str(min(240,remaining)),"--trial-ticks","400",
                 "--camera-mode","bounded","--forward-ticks","2","--movement-feedback",args.condition,
                 "--server-heap-mib","384","--client-heap-mib","512","--capture-width","854","--capture-height","480",
                 "--work-dir",str(args.work_dir),"--build-dir",str(args.build_dir),
                 "--obs-control-dir",str(args.obs_control_dir),"--video-export-dir",str(args.video_export_dir),
                 "--parent-pid",str(os.getpid()),"--parent-created",str(psutil.Process().create_time()),
                 "--stop-file",str(folder/"STOP")]
        if case["case"] in plan["recorded_case_numbers"]: command += ["--spectator","--milestone",str(case["case"])]
        with (folder/(run_id+".log")).open("x",encoding="utf-8") as log:
            result=subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=min(270,remaining+15))
        run=json.loads((ROOT/"experiments/phase9"/run_id/"run.json").read_text())
        print(json.dumps({"run_id":run_id,"stop_reason":run["stop_reason"],"completed":run["completed"]}),flush=True)
        if result.returncode or run["stop_reason"]!="suite_complete" or run["completed"]!=1:
            raise RuntimeError("pilot infrastructure failed; evidence preserved, no automatic retry")


if __name__=="__main__":main()
