"""Matched simulator retention check. This is not live Minecraft evaluation."""

import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from autonomy import AutonomousAgent, GOALS
from autonomy.metrics import summarize
from tools.train_phase7 import feature_table, evaluate


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before",type=Path,required=True)
    parser.add_argument("--after",type=Path,required=True)
    parser.add_argument("--episodes",type=int,default=100)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    if not 1<=args.episodes<=100 or args.output.exists() or args.output.with_suffix(".jsonl").exists():
        parser.error("use 1-100 episodes and new output paths")
    checkpoints={"original_phase7":ROOT/"checkpoints/phase7/curriculum_v3_seed29.npz",
                 "before_campaign":args.before,"after_campaign":args.after}
    hashes={name:hashlib.sha256(path.read_bytes()).hexdigest() for name,path in checkpoints.items()}
    table=feature_table(); started=time.monotonic()
    report={"environment":"Phase7 World2D simulator, not Minecraft","episodes_per_goal":args.episodes,
            "evaluation_learning_disabled":True,"seed_start":9200000000,"checkpoints":hashes,"conditions":{},
            "completed":False,"purpose":"descriptive retention check; not a live generalization claim"}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.with_suffix(".jsonl").open("x",encoding="utf-8") as raw:
        for name,path in checkpoints.items():
            agent,_=AutonomousAgent.load(path,table)
            report["conditions"][name]={}
            for level,goal in enumerate(GOALS):
                if time.monotonic()-started>120:
                    raise RuntimeError("bounded retention-check wall limit reached")
                seeds=range(9200000000+level*100000,9200000000+level*100000+args.episodes)
                rows=evaluate(agent,goal,seeds)
                report["conditions"][name][goal]=summarize(rows)
                for row in rows:
                    raw.write(json.dumps({"condition":name,**row},separators=(",",":"))+"\n")
                print(json.dumps({"condition":name,"goal":goal,"successes":sum(r['success'] for r in rows),"episodes":len(rows)}),flush=True)
    report["checkpoint_hashes_unchanged"]=all(hashlib.sha256(p.read_bytes()).hexdigest()==hashes[n] for n,p in checkpoints.items())
    report["completed"]=True
    report["elapsed_seconds"]=time.monotonic()-started
    args.output.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8",newline="\n")


if __name__=="__main__":
    main()
