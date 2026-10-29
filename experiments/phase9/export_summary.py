"""Export actual development observations and provenance, without replaying actions."""

import argparse
import csv
import json
import hashlib
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from tools.run_phase9 import brain_sample


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    state=json.loads((args.campaign/"state.json").read_text())
    attempts=state["attempts"]
    training=[a for a in attempts if a["status"]=="committed" and a["train"]]
    evaluations=[a for a in attempts if a["status"]=="committed" and not a["train"]]
    clips=[]
    discarded_updates=0
    for attempt in attempts:
        result=Path(attempt.get("results",ROOT/"experiments/phase9"/attempt["run_id"]))
        run=json.loads((result/"run.json").read_text()) if (result/"run.json").is_file() else {}
        candidate=None
        if attempt["status"]!="committed" and (result/"controller.jsonl").is_file():
            outcomes=[json.loads(line) for line in (result/"controller.jsonl").read_text().splitlines()]
            discarded_updates+=sum(row.get("update",{}).get("weight_delta_norm",0)>0 for row in outcomes)
            path=ROOT/"checkpoints/phase9"/attempt["run_id"]/"trial_0000.npz"
            if path.is_file():
                candidate={"path":str(path),"sha256":hashlib.sha256(path.read_bytes()).hexdigest(),"promoted":False}
        clips.append({"run_id":attempt["run_id"],"status":attempt["status"],"success":attempt.get("success"),
                      "video":attempt.get("video",run.get("milestone_video")),"video_status":run.get("milestone_video_status"),
                      "video_error":run.get("milestone_video_error"),"original_results":str(result),
                      "checkpoint_before":attempt["checkpoint"],"checkpoint_after":attempt.get("checkpoint_after"),
                      "uncommitted_candidate_checkpoint":candidate,"actions_altered":False})
    args.output.mkdir(parents=True,exist_ok=True)
    fields=("run_id","split","condition","episode_number","world_seed","status","success","ticks","actions","total_reward","wall_seconds","training_applied")
    with (args.output/"development_episodes.csv").open("w",encoding="utf-8",newline="") as handle:
        writer=csv.DictWriter(handle,fieldnames=fields,extrasaction="ignore")
        writer.writeheader(); writer.writerows(attempts)
    plt.rcParams.update({"font.size":10,"axes.spines.top":False,"axes.spines.right":False})
    if training:
        fig,axes=plt.subplots(1,3,figsize=(12,3.6),layout="constrained")
        x=[a["episode_number"] for a in training]
        for axis,key,label in zip(axes,("total_reward","actions","weight_delta_norm"),("Environment return","Acknowledged actions","Readout weight-change norm")):
            y=[a["update"][key] if key=="weight_delta_norm" else a[key] for a in training]
            axis.plot(x,y,"o-",color="#246bb7")
            axis.set(xlabel="Committed training episode",ylabel=label,xticks=x)
            axis.grid(alpha=.2)
        fig.suptitle(f"Development pilot observations (n={len(training)}); no matched improvement claim")
        fig.savefig(args.output/"development_progress.png",dpi=160)
        fig.savefig(args.output/"development_progress.svg")
        plt.close(fig)
    if evaluations:
        fig,axis=plt.subplots(figsize=(9,4),layout="constrained")
        labels=[a["condition"] for a in evaluations]
        axis.bar(range(len(evaluations)),[a["actions"] for a in evaluations],
                 color=["#267c58" if a["success"] else "#b85353" for a in evaluations])
        axis.set(xticks=range(len(evaluations)),xticklabels=labels,ylabel="Acknowledged actions",
                 title="Matched development checks · green success / red failure\nSmall samples do not establish neural contribution")
        fig.savefig(args.output/"development_controls.png",dpi=160)
        plt.close(fig)
    committed=[a for a in attempts if a["status"]=="committed"]
    sample=brain_sample(committed[-1]["results"]) if committed else None
    # For an informative static illustration select a real active window,
    # rather than inventing activity after the visible resource disappeared.
    if sample:
        for line in (Path(committed[-1]["results"])/"bridge.jsonl").read_text().splitlines():
            row=json.loads(line); response=row.get("response",{})
            if response.get("neural_features") is not None and response.get("peak_global_active",0)>sample["peak_active_neurons"]:
                sample={"command_id":response["command_id"],"requested_action":response["action"],"mode":response["feature_mode"],
                        "features":response["neural_features"],"probabilities":response["action_probabilities"],
                        "peak_active_neurons":response["peak_global_active"]}
    if sample:
        fig,axes=plt.subplots(1,2,figsize=(12,4),layout="constrained")
        features={k:v for k,v in sample["features"].items() if k!="bias"}
        axes[0].bar(list(features),list(features.values()),color="#5689bc")
        axes[0].set(ylabel="Integrated readout activity / 50",title="Actual fixed-network readout; bias excluded")
        names=list(sample["probabilities"])
        axes[1].barh(names,list(sample["probabilities"].values()),color="#598961")
        axes[1].set(xlim=(0,1),xlabel="Probability",title="Actual action distribution")
        fig.suptitle(f"Selected actual window (maximum active-count in last episode): request {sample['command_id']} {sample['requested_action']} · {sample['mode']}\n18-step window; peak active neurons {sample['peak_active_neurons']} / 139,255. A request is not an execution acknowledgment.",fontsize=10)
        fig.savefig(args.output/"actual_brain_readout.png",dpi=160)
        plt.close(fig)
    media={"stage":"development","official_training_worlds":0,"training_episodes":len(training),
           "committed_training_updates":sum(a["training_applied"] for a in training),
           "uncommitted_candidate_updates":discarded_updates,"evaluation_episodes":len(evaluations),
           "generated_world_instances":sum(a["generated_world_instances"] or 0 for a in attempts),
           "distinct_generated_seeds":len({a["world_seed"] for a in attempts if a["generated_world_instances"]}),
           "learning_improvement_established":False,"final_untouched_evaluation_performed":False,
           "brain_figure_selection":"recorded window with maximum active count within last committed episode",
           "clips":clips}
    (args.output/"video_production_metadata.json").write_text(json.dumps(media,indent=2)+"\n",encoding="utf-8",newline="\n")
    print(json.dumps({k:v for k,v in media.items() if k!="clips"},indent=2))


if __name__=="__main__":
    main()
