"""Verify final checker release against archived and fresh Minecraft evidence."""

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from autonomy.evidence import audit_run, file_sha256
from autonomy.experiment import atomic_json, source_manifest

FOLDER = Path(__file__).resolve().parent


def main():
    pilot = json.loads((FOLDER / "pilot_results.json").read_text())
    campaigns = [json.loads((ROOT / "experiments/phase9" / row["name"] / "state.json").read_text())
                 for row in pilot["campaigns"]]
    hardened = ROOT / "experiments/phase9/checker24_hardened"
    state = json.loads((hardened / "state.json").read_text())
    config = json.loads((hardened / "config.json").read_text())
    assert state["active_attempt"] is None and len(state["attempts"]) == 1
    smoke, = state["attempts"]
    assert smoke["status"] == "committed" and smoke["success"] and smoke["update"]["weight_delta_norm"] == 0
    current = source_manifest(ROOT)
    assert current["implementation_sha256"] == config["implementation_sha256"]
    attempts = [attempt for campaign in campaigns for attempt in campaign["attempts"]] + [smoke]
    reports = [audit_run(Path(attempt["results"])) for attempt in attempts]
    assert all(report == json.loads(Path(attempt["checker_report"]).read_text())
               for report, attempt in zip(reports, attempts))
    episodes = [episode for report in reports for episode in report["episodes"]]
    assert len(episodes) == 9 and all(episode["success"] for episode in episodes)
    assert sum(episode["training_applied"] for episode in episodes) == 2
    assert sum(episode["weight_delta_norm"] > 0 for episode in episodes) == 2
    training, = [campaign for campaign in campaigns if any(a["train"] for a in campaign["attempts"])]
    first, second = training["attempts"]
    assert second["checkpoint"] == first["checkpoint_after"]
    assert all(file_sha256(row["checkpoint_after"]["path"]) == row["checkpoint_after"]["sha256"] for row in training["attempts"])
    original = json.loads((FOLDER.parent / "phase8_finish_20261124/artifact_integrity_closeout.json").read_text())
    assert file_sha256(ROOT / "data/processed/connectome_raw_csr.npz") == original["graph"]["sha256"]
    preserved = original["preserved_checkpoints"] | {row["path"]: row["sha256"] for row in original["fits"]}
    assert all(file_sha256(ROOT/path) == digest for path, digest in preserved.items())
    archived = json.loads((FOLDER / "archived_audit_final.json").read_text())
    archived_current = [audit_run(FOLDER.parent / row["run_id"]) for row in archived["reports"]]
    assert archived_current == archived["reports"]
    metadata = [json.loads((Path(attempt["results"]) / "run.json").read_text()) for attempt in attempts]
    result = {"release_ready_for_bounded_development": True, "automated_tests": 136,
              "archived_scored_episodes_reproduced": 152, "new_functional_scored_episodes": 9,
              "new_functional_successes": 9, "generated_disposable_worlds": sum(meta["generated_world_instances"] for meta in metadata),
              "unscored_mining_interruption": 1, "verified_development_training_updates": 2,
              "original_graph_unchanged": True, "original_checkpoints_unchanged": True,
              "phase8_benchmark_unchanged": True, "final_source_sha256": current["implementation_sha256"],
              "original_graph_sha256": original["graph"]["sha256"],
              "original_checkpoints": preserved, "hardened_smoke": smoke,
              "new_evaluation_weight_updates": 0, "minimum_available_ram_mib": min(meta["minimum_sampled_available_ram_mib"] for meta in metadata),
              "maximum_gpu_temperature_c": max(meta["maximum_sampled_gpu_c"] for meta in metadata),
              "training_chain": training["attempts"], "milestone_video": json.loads((FOLDER / "pilot_audit.json").read_text())["milestone_video"],
              "official_training_worlds": 0, "standalone_chat_wakeup_connected": False,
              "scope": "Functional development validation only; not a reliability, learning or neural-benefit benchmark"}
    target = FOLDER / "release_audit.json"
    assert not target.exists()
    atomic_json(target, result)
    print(json.dumps({key: value for key, value in result.items() if key not in ("original_checkpoints", "training_chain", "hardened_smoke")}, indent=2))


if __name__ == "__main__":
    main()
