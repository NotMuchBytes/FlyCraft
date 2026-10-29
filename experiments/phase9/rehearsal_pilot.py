"""Equal-episode simulation rehearsal experiment; never counted as Minecraft worlds."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import statistics
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from autonomy import AutonomousAgent, GOALS
from autonomy.world import ResourceWorld
from autonomy.metrics import summarize
from tools.train_phase7 import feature_table, evaluate


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--checkpoint-dir",type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists() or args.output.with_suffix(".jsonl").exists() or args.checkpoint_dir.exists():
        parser.error("output and candidate checkpoint directory must be new")
    before_sha=hashlib.sha256(args.checkpoint.read_bytes()).hexdigest()
    args.checkpoint_dir.mkdir(parents=True)
    table=feature_table(); started=time.monotonic()
    report={"environment":"Phase7 World2D simulator, not Minecraft","real_training_worlds":0,
            "initial_checkpoint_sha256":before_sha,"training_episodes_per_condition":48,
            "training_seed_start":34000000,"evaluation_seed_start":9201000000,"evaluation_episodes_per_goal":100,
            "conditions":{},"controls":"same initial checkpoint, existing hyperparameters and seed sequence; only training goal mixture differs",
            "training_compute":"episode budget matched; action counts and wall time reported, not compute-matched",
            "neural_dynamics":"fixed Phase7 neural feature cache; readout parameters only are learned",
            "candidate_promoted_to_live_policy":False}
    with args.output.with_suffix(".jsonl").open("x",encoding="utf-8") as raw:
        for condition in ("frozen","focused_find_collect","mixed_rehearsal"):
            agent,_=AutonomousAgent.load(args.checkpoint,table)
            training=[]; begin=time.monotonic()
            if condition!="frozen":
                for index in range(48):
                    if time.monotonic()-started>120:
                        raise RuntimeError("bounded rehearsal experiment wall limit reached")
                    goal="find_collect" if condition=="focused_find_collect" else GOALS[index%len(GOALS)]
                    row=agent.run_episode(ResourceWorld(34000000+index,goal),goal,train=True)
                    training.append(row)
                    raw.write(json.dumps({"condition":condition,"stage":"simulation_training",**row},separators=(",",":"))+"\n")
                candidate=args.checkpoint_dir/(condition+".npz")
                agent.save(candidate,extension={"phase9_simulation_only":True,"real_training_worlds":0})
            entry={"training_episodes":len(training),"training_actions":sum(row["actions"] for row in training),
                   "training_goals":dict(Counter(row["goal"] for row in training)),"training_wall_seconds":time.monotonic()-begin,
                   "mean_return_variance":statistics.fmean(row["update"].get("return_variance",0) for row in training) if training else None,
                   "evaluation":{}}
            if condition!="frozen":
                entry["candidate_checkpoint"]=str(candidate)
                entry["candidate_sha256"]=hashlib.sha256(candidate.read_bytes()).hexdigest()
            for level,goal in enumerate(GOALS):
                rows=evaluate(agent,goal,range(9201000000+level*100000,9201000000+level*100000+100))
                entry["evaluation"][goal]=summarize(rows)
                for row in rows:
                    raw.write(json.dumps({"condition":condition,"stage":"simulation_evaluation",**row},separators=(",",":"))+"\n")
            report["conditions"][condition]=entry
            print(json.dumps({"condition":condition,"training_episodes":len(training),"training_actions":entry["training_actions"],
                              "successes":{goal:metrics["successes"] for goal,metrics in entry["evaluation"].items()}}),flush=True)
    report["initial_checkpoint_unchanged"]=hashlib.sha256(args.checkpoint.read_bytes()).hexdigest()==before_sha
    report["elapsed_seconds"]=time.monotonic()-started
    args.output.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8",newline="\n")


if __name__=="__main__":
    main()
