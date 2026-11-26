"""Reproduce the completed benchmark before repairing it; never change scores."""
import collections
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from autonomy.evidence import audit_run
from autonomy.experiment import atomic_json


def main():
    ops=Path(__file__).resolve().parent
    state=json.loads((ops/"before_repair_402/state.json").read_text())
    scores=collections.defaultdict(lambda:[0,0]);hashes={}
    for a in state["attempts"]:
        result=audit_run(a["results"])
        assert result["status"]=="verified" and len(result["episodes"])==1
        episode=result["episodes"][0]
        assert episode["success"]==a["success"] and episode["actions"]==a["actions"]
        key=("training_retention" if a["retention"] else "training_terrain") if a["train"] else a["evaluation_task"]+":"+a["condition"]
        scores[key][0]+=int(a["success"]);scores[key][1]+=1
        hashes[a["run_id"]]=result["evidence_sha256"]
    atomic_json(ops/"completed402_audit.json",dict(verified_episodes=len(state["attempts"]),scores=dict(scores),evidence_sha256=hashes,
        gate=state["gates"]["terrain"],no_scores_changed=True,checkpoint=state["current_checkpoint"]))
    print(json.dumps(dict(scores),indent=2))


if __name__=="__main__":main()
