"""Re-audit the twelve completed training worlds and preserve their chain."""
import json
from pathlib import Path
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from autonomy.evidence import audit_run,file_sha256
from autonomy.experiment import atomic_json
from learning import LinearSoftmaxPolicy
from tools.milestone_video import verify_mp4
from audit_first4 import interval


def main():
    ops=Path(__file__).resolve().parent
    state=json.loads((ops/"through350_state_snapshot.json").read_text())
    config=json.loads((ops/"frozen_config.json").read_text())
    previous=config["initial_checkpoint"]
    rows=[]
    for a in state["attempts"]:
        assert a["status"]=="committed" and a["checkpoint"]==previous
        audit=audit_run(a["results"])
        assert audit["status"]=="verified" and len(audit["episodes"])==1
        result=audit["episodes"][0]
        assert result["success"]==a["success"]
        assert file_sha256(a["checkpoint_after"]["path"])==a["checkpoint_after"]["sha256"]
        before,_=LinearSoftmaxPolicy.load(previous["path"])
        after,_=LinearSoftmaxPolicy.load(a["checkpoint_after"]["path"])
        assert np.isclose(np.linalg.norm(after.weights-before.weights),result["weight_delta_norm"],rtol=1e-9,atol=1e-12)
        previous=a["checkpoint_after"]
        if a["video_required"]:
            assert verify_mp4(a["video"]["path"])["full_decode_verified"]
        atomic_json(ops/(a["run_id"]+"_audit.json"),audit)
        rows.append(dict(official_world_number=a["official_world_number"],retention=a["retention"],
            worker_wall_seconds=a["wall_seconds"],**result))
    groups={}
    for task,selected in (("terrain",[r for r in rows if not r["retention"]]),("retention",[r for r in rows if r["retention"]])):
        n=len(selected);k=sum(r["success"] for r in selected)
        groups[task]=dict(successes=k,trials=n,wilson95=interval(k,n),
            mean_actions=float(np.mean([r["actions"] for r in selected])),
            mean_game_seconds=float(np.mean([r["game_seconds"] for r in selected])),
            mean_worker_wall_seconds=float(np.mean([r["worker_wall_seconds"] for r in selected])))
    atomic_json(ops/"through350_audit.json",dict(training_not_heldout=True,foundation_worlds=338,
        combined_worlds=350,new_successes=sum(r["success"] for r in rows),new_scored=len(rows),
        updates=sum(r["training_applied"] for r in rows),groups=groups,episodes=rows,checkpoint=previous,
        graph_sha256=file_sha256(config["checker"]["graph"]["path"])))
    print(json.dumps(groups,indent=2))


if __name__=="__main__":main()
