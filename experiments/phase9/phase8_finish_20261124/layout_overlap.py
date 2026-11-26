"""Distinguish unseen seed identities from repeated prepared-fixture geometry."""

import argparse
import json
from pathlib import Path

FOLDER = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    old_path = FOLDER.parent / "phase8_pitch_followup_20261117/final_results.json"
    new_path = FOLDER / "final_results.json"
    if not new_path.exists():
        new_path = FOLDER / "progress.json"
    old = json.loads(old_path.read_text())
    new = json.loads(new_path.read_text())
    development = json.loads((FOLDER / "development_audit.json").read_text())
    source_seeds = {(row["world_seed"], row["layout_seed"])
                    for rows in old["episodes"].values() for row in rows}
    source_seeds.update((202611230801, seed) for seed in (728310449, 461992637, 890173251))
    source_geometry = {goal: {row["relative_fixture_sha256"] for row in rows}
                       for goal, rows in old["episodes"].items()}
    for variant in development["episodes"].values():
        for goal, rows in variant.items():
            source_geometry.setdefault(goal, set()).update(row["relative_fixture_sha256"] for row in rows)
    pooled_geometry = set().union(*source_geometry.values())
    report = {}
    for goal, rows in new["episodes"].items():
        seeds = {(row["world_seed"], row["layout_seed"]) for row in rows}
        assert not seeds & source_seeds, "Held-out seed identity overlaps development"
        geometry = {row["relative_fixture_sha256"] for row in rows}
        report[goal] = {
            "scored_trials": len(rows), "seed_identity_overlap_with_development": 0,
            "distinct_translation_normalized_fixtures": len(geometry),
            "distinct_fixtures_already_in_same_goal_development": len(geometry & source_geometry[goal]),
            "trials_with_same_goal_development_fixture": sum(
                row["relative_fixture_sha256"] in source_geometry[goal] for row in rows),
            "trials_with_any_development_fixture": sum(
                row["relative_fixture_sha256"] in pooled_geometry for row in rows),
            "distinct_fixtures_absent_from_all_development": len(geometry - pooled_geometry),
        }
    result = {
        "evaluation_file": new_path.name, "development_source": str(old_path.relative_to(FOLDER.parent)),
        "goals": report,
        "interpretation": "Fresh seed identities do not guarantee novel geometry: voxel rounding and bounded tree placement reuse templates. Report this as a held-out seed reliability test, not unseen-terrain or out-of-distribution layout generalization.",
    }
    with args.output.open("x", encoding="utf-8", newline="\n") as output:
        json.dump(result, output, indent=2)
        output.write("\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
