"""Verify preserved graph/checkpoints and the new fit's embedded provenance."""

import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from autonomy.experiment import source_manifest
from learning.policy import LinearSoftmaxPolicy
from experiments.phase9.phase8_finish_20261123.analyze_development import CANDIDATES, OLD_CHECKPOINT

FOLDER = Path(__file__).resolve().parent


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    checks = {}
    graph = ROOT / "data/processed/connectome_raw_csr.npz"
    previous = json.loads((ROOT / "experiments/phase7/brain_validation.json").read_text())
    assert digest(graph) == previous["graph_sha256"]
    with np.load(graph, allow_pickle=False) as stored:
        shape = stored["shape"].tolist()
    assert shape == [139255, 139255]
    checks["graph"] = {"sha256": previous["graph_sha256"], "shape": shape, "unchanged": True}
    original = ROOT / "checkpoints/phase9/dev_pilot_20261029_b_pilot_trained_00002_a0003/trial_0000.npz"
    frozen = ROOT / "checkpoints/phase7/curriculum_v3_seed29.npz"
    assert digest(original) == OLD_CHECKPOINT
    frozen_sha = "a2b86d257882ebbd0faf7011588a30e91039e255ce3e3eb624985db82cc81ba6"
    assert digest(frozen) == frozen_sha
    checks["preserved_checkpoints"] = {original.relative_to(ROOT).as_posix(): OLD_CHECKPOINT,
                                       frozen.relative_to(ROOT).as_posix(): frozen_sha}
    baseline, _ = LinearSoftmaxPolicy.load(original)
    fits = []
    for name, record_name in (("progress_readout", "progress_readout_training"),
                              ("progress_readout_mining", "mining_readout_training")):
        path = ROOT / "checkpoints/phase8/finish_20261123" / (name + ".npz")
        sha = digest(path)
        assert sha in CANDIDATES
        policy, metadata = LinearSoftmaxPolicy.load(path)
        provenance = json.loads((FOLDER / (record_name + ".json")).read_text())
        assert metadata["extra"]["extension"]["offline_progress_training"] == provenance
        assert digest(Path(provenance["source_checkpoint"])) == OLD_CHECKPOINT
        if "source_checkpoint_sha256" in provenance:
            assert provenance["source_checkpoint_sha256"] == OLD_CHECKPOINT
        assert len(provenance["source_episodes"]) == 120
        assert policy.weights.shape == (66, 12)
        anchor = baseline.expanded(66, policy.actions)
        delta = float(np.linalg.norm(policy.weights - anchor.weights))
        np.testing.assert_allclose(delta, provenance["weight_delta_norm"], rtol=1e-12)
        assert sum(provenance["action_counts"].values()) == provenance["sample_count"]
        fits.append({"path": path.relative_to(ROOT).as_posix(), "sha256": sha,
                     "weight_shape": list(policy.weights.shape), "weight_delta_norm": delta,
                     "training_examples": provenance["sample_count"],
                     "mining_examples": provenance["action_counts"]["COLLECT_LOG"],
                     "embedded_provenance_matches": True})
    manifest = source_manifest(ROOT)
    assert manifest["implementation_sha256"] == "797c90920bd4dd348804c49ff578da65b4615b8fcbd46b1daf6ce82e4c3873ce"
    checks.update(fits=fits, live_implementation_sha256=manifest["implementation_sha256"])
    checks["source_log_sha256"] = {
        f"{run}/{name}": digest(ROOT / "experiments/phase9" / run / name)
        for run in sorted({item["run_id"] for item in provenance["source_episodes"]})
        for name in ("run.json", "bridge.jsonl", "controller.jsonl", "headless.jsonl",
                     "server.jsonl", "server.jsonl.initial.jsonl", "server.jsonl.delivery.jsonl")}
    with args.output.open("x", encoding="utf-8", newline="\n") as output:
        json.dump(checks, output, indent=2, allow_nan=False)
        output.write("\n")
    print(json.dumps({"graph_shape": shape, "preserved_checkpoints": 2,
                      "verified_fits": len(fits), "source_logs": len(checks["source_log_sha256"])}))


if __name__ == "__main__":
    main()
