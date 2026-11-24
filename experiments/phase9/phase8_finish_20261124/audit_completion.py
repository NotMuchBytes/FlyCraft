"""Re-audit the complete frozen primary sample and preserve evidence hashes."""

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from autonomy.experiment import source_manifest
from experiments.phase9.phase8_pitch_followup_20261117.score import score

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
    plan = json.loads((FOLDER / "heldout_plan.json").read_text())
    final = json.loads((FOLDER / "final_results.json").read_text())
    fresh = score([run["run"] for run in final["runs"]], plan_folder=FOLDER)
    assert fresh == final, "Final scores must reproduce exactly from preserved live logs"
    assert all(row["complete"] and row["verified_trials"] == 30 for row in fresh["goals"].values())
    assert source_manifest(ROOT)["implementation_sha256"] == plan["implementation_sha256"]
    checkpoint = ROOT / plan["policy"]["checkpoint"]
    assert digest(checkpoint) == plan["policy"]["sha256"]
    hashes, episodes, nonzero_updates = {}, 0, 0
    for run in fresh["runs"]:
        directory = FOLDER.parent / run["run"]
        meta = json.loads((directory / "run.json").read_text())
        assert meta["stop_reason"] == "suite_complete"
        assert meta["available_ram_guard_mib"] == 768 and meta["free_disk_guard_mib"] == 2048
        assert meta["minimum_sampled_available_ram_mib"] >= 768
        assert meta["maximum_sampled_gpu_c"] < 75
        rows = [json.loads(line) for line in (directory / "controller.jsonl").read_text().splitlines()]
        assert len(rows) == meta["completed"] == meta["requested"]
        for row in rows:
            assert row["train"] is False and row["condition"] == "trained"
            nonzero_updates += row["update"]["weight_delta_norm"] != 0
            assert row["update"]["weight_delta_norm"] == row["update"]["gradient_norm"] == 0
        episodes += len(rows)
        for path in sorted(directory.iterdir()):
            if path.is_file() and path.suffix in (".json", ".jsonl", ".log"):
                hashes[path.relative_to(ROOT).as_posix()] = digest(path)
    assert episodes == 120 and nonzero_updates == 0
    result = {
        "phase": 8, "primary_episodes": episodes, "complete_runs": len(fresh["runs"]),
        "exact_score_reproduction": True, "evaluation_weight_updates": nonzero_updates,
        "checkpoint_sha256": digest(checkpoint), "implementation_sha256": plan["implementation_sha256"],
        "all_point_targets_met": all(row["target_met"] for row in fresh["goals"].values()),
        "minimum_sampled_available_ram_mib": min(run["minimum_sampled_available_ram_mib"] for run in fresh["runs"]),
        "maximum_sampled_gpu_c": max(run["maximum_sampled_gpu_c"] for run in fresh["runs"]),
        "summed_run_elapsed_seconds": sum(run["elapsed_seconds"] for run in fresh["runs"]),
        "evidence_sha256": hashes,
        "limits": "Controlled fixtures; seed-disjointness does not imply novel geometry. No natural-terrain or neural-benefit conclusion.",
        "phase9_campaign_started": False,
    }
    with args.output.open("x", encoding="utf-8", newline="\n") as output:
        json.dump(result, output, indent=2, allow_nan=False)
        output.write("\n")
    print(json.dumps({key: value for key, value in result.items() if key != "evidence_sha256"}, indent=2))


if __name__ == "__main__":
    main()
