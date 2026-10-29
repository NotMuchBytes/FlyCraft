"""Matched descriptive simulation rehearsal comparisons; no live promotion."""

import argparse
from collections import defaultdict
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from experiments.phase9.analyze_validation import paired_p
from tools.analyze_phase8 import wilson


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():
        parser.error("analysis output must be new")
    rows=defaultdict(dict)
    for row in map(json.loads,args.input.with_suffix(".jsonl").read_text().splitlines()):
        if row["stage"]=="simulation_evaluation":
            rows[row["condition"]][row["goal"],row["world_seed"]]=row
    result={"environment":"World2D simulator, not Minecraft","candidate_promoted":False,"conditions":{}}
    for condition in ("focused_find_collect","mixed_rehearsal"):
        result["conditions"][condition]={}
        for goal in sorted({key[0] for key in rows["frozen"]}):
            keys=[key for key in rows["frozen"] if key[0]==goal]
            base=sum(rows["frozen"][key]["success"] for key in keys)
            new=sum(rows[condition][key]["success"] for key in keys)
            left=sum(rows["frozen"][key]["success"] and not rows[condition][key]["success"] for key in keys)
            right=sum(rows[condition][key]["success"] and not rows["frozen"][key]["success"] for key in keys)
            result["conditions"][condition][goal]={"episodes":len(keys),"frozen_successes":base,"candidate_successes":new,
                "candidate_wilson_95":wilson(new,len(keys)),"frozen_only":left,"candidate_only":right,
                "exact_paired_p":paired_p(left,right)}
    args.output.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8",newline="\n")
    print(json.dumps({condition:{goal:values for goal,values in goals.items() if goal in {"wooden_pickaxe","collect_multiple"}}
                      for condition,goals in result["conditions"].items()},indent=2))


if __name__=="__main__":
    main()
