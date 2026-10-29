"""Descriptive matched controls and retention statistics from actual stored rows."""

import argparse
from collections import defaultdict
import json
import math
from pathlib import Path
import statistics
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from tools.analyze_phase8 import wilson


def paired_p(left_only,right_only):
    n=left_only+right_only
    return min(1.,2*sum(math.comb(n,i) for i in range(min(left_only,right_only)+1))/2**n) if n else 1.


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign",type=Path,required=True)
    parser.add_argument("--retention",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():
        parser.error("preserve previous analyses; output must be new")
    state=json.loads((args.campaign/"state.json").read_text())
    grouped=defaultdict(list)
    for row in state["attempts"]:
        if row["status"]=="committed" and row["split"]=="eval_a":
            grouped[row["condition"]].append(row)
    result={"environment":"real Minecraft, controlled flat survival fixtures, crosshair-only",
            "stage":"development","conditions":{},"comparisons_to_trained":{},
            "interval":"95% Wilson, descriptive conditional on these fixtures; small samples",
            "final_b_used":False,"learning_improvement_established":False,"neural_benefit_established":False}
    indexed={condition:{row["world_seed"]:row for row in rows} for condition,rows in grouped.items()}
    for condition,rows in grouped.items():
        successes=sum(row["success"] for row in rows)
        result["conditions"][condition]={"episodes":len(rows),"successes":successes,"success_rate":successes/len(rows),
            "wilson_95":wilson(successes,len(rows)),"world_seeds":[row["world_seed"] for row in rows],
            "actions":[row["actions"] for row in rows],"ticks":[row["ticks"] for row in rows],
            "mean_actions":statistics.fmean(row["actions"] for row in rows),
            "mean_game_seconds":statistics.fmean(row["ticks"]/20 for row in rows),
            "failures":[row["termination"] for row in rows if not row["success"]],
            "updates_zero":all(row["update"]["weight_delta_norm"]==0 for row in rows)}
        if condition!="trained" and "trained" in indexed:
            shared=indexed["trained"].keys()&indexed[condition].keys()
            left=sum(indexed["trained"][seed]["success"] and not indexed[condition][seed]["success"] for seed in shared)
            right=sum(indexed[condition][seed]["success"] and not indexed["trained"][seed]["success"] for seed in shared)
            result["comparisons_to_trained"][condition]={"matched_worlds":len(shared),"trained_only":left,"control_only":right,
                                                           "exact_paired_p":paired_p(left,right)}
    retention=defaultdict(dict)
    for row in map(json.loads,args.retention.with_suffix(".jsonl").read_text().splitlines()):
        retention[row["condition"]][row["goal"],row["world_seed"]]=row
    result["simulation_retention"]={"environment":"Phase7 World2D simulator, not Minecraft","goals":{}}
    for goal in sorted({key[0] for key in retention["before_campaign"]}):
        keys=[key for key in retention["before_campaign"] if key[0]==goal]
        before=sum(retention["before_campaign"][key]["success"] for key in keys)
        after=sum(retention["after_campaign"][key]["success"] for key in keys)
        left=sum(retention["before_campaign"][key]["success"] and not retention["after_campaign"][key]["success"] for key in keys)
        right=sum(retention["after_campaign"][key]["success"] and not retention["before_campaign"][key]["success"] for key in keys)
        result["simulation_retention"]["goals"][goal]={"episodes":len(keys),"before_successes":before,"after_successes":after,
            "before_only":left,"after_only":right,"exact_paired_p":paired_p(left,right)}
    args.output.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8",newline="\n")
    print(json.dumps(result,indent=2))


if __name__=="__main__":
    main()
