"""Fit the existing readout to its own recorded actions that made observed progress."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

import sys
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from experiments.phase9.phase8_finish_20261123.reconstruct_logged import checkpoint, reconstruct, table
from autonomy import AutonomousAgent

def objective(flat, x, y, allowed, sample_weights, original, regularization):
    weights=flat.reshape(original.shape)
    logits=x@weights
    logits=np.where(allowed,logits,-np.inf)
    logits-=np.max(logits,axis=1,keepdims=True)
    exp=np.exp(logits)
    probabilities=exp/exp.sum(axis=1,keepdims=True)
    selected=probabilities[np.arange(len(y)),y]
    loss=-float(sample_weights@np.log(np.maximum(selected,1e-300)))
    errors=probabilities.copy()
    errors[np.arange(len(y)),y]-=1
    errors*=sample_weights[:,None]
    difference=weights-original
    loss+=regularization/2*float(np.sum(difference*difference))
    gradient=x.T@errors+regularization*difference
    return loss,gradient.ravel()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint-out", type=Path, required=True)
    parser.add_argument("--provenance-out", type=Path, required=True)
    parser.add_argument("--confirmed-break-labels", action="store_true",
                        help="Include successful acknowledged log breaks as mining examples")
    args = parser.parse_args()
    if args.checkpoint_out.exists() or args.provenance_out.exists():
        parser.error("Output files must be new")
    folder = ROOT / "experiments/phase9/phase8_pitch_followup_20261117"
    records = json.loads((folder / "final_results.json").read_text())
    scored = {(row["run_id"], row["episode_id"]): row
              for group in records["episodes"].values() for row in group}
    base, _ = AutonomousAgent.load(checkpoint, table)
    base.enable_live_pitch()
    features, actions, masks, rewards = [], [], [], []
    episode_provenance=[]
    for run_id in sorted({key[0] for key in scored}):
        originals = {row["episode_id"]: row for row in map(json.loads,
            (ROOT / "experiments/phase9" / run_id / "controller.jsonl").read_text().splitlines())}
        for episode_id, episode in reconstruct(run_id).items():
            score = scored.get((run_id, episode_id))
            if score is None:
                continue
            session=episode["session"]
            assert session["success"] == score["success"] and session["actions"] == score["actions"]
            np.testing.assert_allclose(session["total_reward"], originals[episode_id]["total_reward"], rtol=1e-10,atol=1e-10)
            retained=0
            confirmed_breaks = sum(ack["action"] == "COLLECT_LOG" and ack["status"] == "success"
                                   and ack["block_changed"] for ack in episode["acknowledgments"])
            assert confirmed_breaks == score["confirmed_breaks"]
            for (vector, action, probabilities, reward), acknowledgment in zip(
                    episode["trajectory"], episode["acknowledgments"], strict=True):
                example_weight = reward
                if (args.confirmed_break_labels and acknowledgment["action"] == "COLLECT_LOG"
                        and acknowledgment["status"] == "success" and acknowledgment["block_changed"]):
                    example_weight = max(example_weight, 0.1)
                if example_weight <= 0:
                    continue
                features.append(vector)
                actions.append(action)
                masks.append(probabilities>0)
                rewards.append(min(example_weight,1.0))
                retained+=1
            episode_provenance.append({"run_id":run_id,"episode_id":episode_id,
                                       "success":score["success"],"retained_progress_transitions":retained})
    assert len(episode_provenance)==120
    x=np.asarray(features)
    y=np.asarray(actions)
    allowed=np.asarray(masks)
    sample_weights=np.asarray(rewards)
    for action in np.unique(y):
        selected=y==action
        sample_weights[selected]/=sample_weights[selected].sum()
    sample_weights/=sample_weights.sum()
    original=base.policy.weights.copy()
    regularization=0.0001

    result=minimize(objective,original.ravel(),args=(x,y,allowed,sample_weights,original,regularization),jac=True,method="L-BFGS-B",
                    options={"maxiter":500,"ftol":1e-11,"gtol":1e-7})
    assert result.success, result.message
    base.policy.weights=result.x.reshape(original.shape)
    base.policy.episodes_trained+=120
    base.session=None
    base.manager=None
    base.pending=None
    base.trajectory=[]
    provenance={
        "method":"Weighted behavioral cloning of recorded actions with positive operational transition reward",
        "source_checkpoint":str(checkpoint),"source_episodes":episode_provenance,
        "source_probabilities_rewards_and_action_counts_verified":True,
        "prior_evaluation_reclassified_as_development":True,
        "sample_count":len(y),"action_counts":dict(zip(base.policy.actions,map(int,np.bincount(y,minlength=len(base.policy.actions))))),
        "regularization":regularization,"loss":float(result.fun),"iterations":int(result.nit),
        "weight_delta_norm":float(np.linalg.norm(base.policy.weights-original)),
        "teacher":"Original policy's recorded actions and observed progress, with no new action labels",
        "policy_inputs":"Preserved 66-feature live pitch interface",
        "confirmed_break_labels": args.confirmed_break_labels,
        "mining_supervision": "A successful block-change acknowledgment is a mining example. Collection credit still requires inventory.",
    }
    provenance["source_checkpoint_sha256"]=hashlib.sha256(checkpoint.read_bytes()).hexdigest()
    out=args.provenance_out
    out.parent.mkdir(parents=True,exist_ok=True)
    with out.open("x",newline="\n") as file:
        json.dump(provenance,file,indent=2)
        file.write("\n")
    path=args.checkpoint_out
    base.save(path,extension={"offline_progress_training":provenance})
    print(json.dumps({key:provenance[key] for key in ("sample_count","action_counts","loss","iterations","weight_delta_norm")},indent=2))
    print("Pitch error weights",dict(zip(base.policy.actions,map(float,base.policy.weights[-3]))))
    print("Saved",path)


if __name__ == "__main__":
    main()
