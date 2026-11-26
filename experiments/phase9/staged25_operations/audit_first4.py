"""Read-only milestone audit; never supplies actions or changes a checkpoint."""
import json
import math
from pathlib import Path
import shutil
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from autonomy.evidence import audit_run, file_sha256
from autonomy.experiment import atomic_json
from learning import LinearSoftmaxPolicy
from tools.milestone_video import verify_mp4


def interval(k, n):
    z = 1.959963984540054
    p, d = k/n, 1+z*z/n
    center = (p+z*z/(2*n))/d
    half = z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return [max(0, center-half), min(1, center+half)]


def main():
    folder = ROOT / "experiments/phase9/fc9_stage25"
    output = Path(__file__).resolve().parent
    config, state = [json.loads((folder / name).read_text()) for name in ("config.json", "state.json")]
    attempts = state["attempts"][:4]
    assert len(attempts) == 4 and all(a["status"] == "committed" for a in attempts)
    foundation = config["foundation"]["checkpoint"]
    assert file_sha256(foundation["path"]) == foundation["sha256"]
    old, _ = LinearSoftmaxPolicy.load(foundation["path"])
    migrated, _ = LinearSoftmaxPolicy.load(config["initial_checkpoint"]["path"])
    assert np.array_equal(old.weights, migrated.weights[:old.weights.shape[0], :old.weights.shape[1]])
    assert file_sha256(config["checker"]["graph"]["path"]) == config["checker"]["graph"]["sha256"]
    previous = config["initial_checkpoint"]
    rows, files, videos = [], {}, []
    for a in attempts:
        assert a["checkpoint"] == previous
        report = audit_run(a["results"])
        assert report["status"] == "verified" and len(report["episodes"]) == 1
        episode = report["episodes"][0]
        assert episode["success"] == a["success"]
        before, _ = LinearSoftmaxPolicy.load(a["checkpoint"]["path"])
        after, _ = LinearSoftmaxPolicy.load(a["checkpoint_after"]["path"])
        assert file_sha256(a["checkpoint_after"]["path"]) == a["checkpoint_after"]["sha256"]
        assert np.isclose(np.linalg.norm(after.weights-before.weights), a["update"]["weight_delta_norm"], rtol=1e-9, atol=1e-12)
        previous = a["checkpoint_after"]
        rows.append(dict(official_world_number=a["official_world_number"], run_id=a["run_id"],
            task="wood_retention" if a["retention"] else "terrain_teaching", **episode,
            worker_wall_seconds=a["wall_seconds"], checkpoint_after=a["checkpoint_after"]))
        atomic_json(output / (a["run_id"] + "_audit.json"), report)
        for name, sha in report["evidence_sha256"].items():
            files[str(Path(a["results"]) / name)] = sha
        if a["video_required"]:
            video = a["video"]
            assert file_sha256(video["path"]) == video["sha256"]
            videos.append(dict(path=video["path"], sha256=video["sha256"], recheck=verify_mp4(video["path"])))
    groups = {}
    for task in ("terrain_teaching", "wood_retention"):
        selected = [r for r in rows if r["task"] == task]
        successes = sum(r["success"] for r in selected)
        groups[task] = dict(successes=successes, trials=len(selected), wilson95=interval(successes,len(selected)),
            mean_actions=float(np.mean([r["actions"] for r in selected])),
            mean_game_seconds=float(np.mean([r["game_seconds"] for r in selected])),
            mean_worker_wall_seconds=float(np.mean([r["worker_wall_seconds"] for r in selected])))
    for name in ("config.json", "source_manifest.json", "seeds.json"):
        shutil.copy2(folder / name, output / ("frozen_" + name))
    atomic_json(output / "first4_state_snapshot.json", dict(attempts=attempts, checkpoint=previous,
        basis="immutable first four completed attempts; later live state excluded"))
    atomic_json(output / "first4_audit.json", dict(schema=1, training_evidence_not_heldout=True,
        foundation_worlds=338, official_worlds_through_snapshot=342, training_successes=2,
        readout_updates=4, groups=groups, episodes=rows, videos=videos, evidence_sha256=files,
        original_weight_prefix_preserved=True, graph_sha256=config["checker"]["graph"]["sha256"],
        later_skills_unimplemented=config["pending_skills"]))
    print(json.dumps(groups,indent=2))


if __name__ == "__main__":
    main()
