"""Produce a clearly labeled fix-request example from a corrupted log COPY."""

import argparse
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from autonomy.evidence import audit_run, EvidenceError
from autonomy.experiment import atomic_json
from tools.supervise_phase9 import request_fix


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--copy-dir", type=Path, required=True)
    args = parser.parse_args()
    args.copy_dir.mkdir(parents=True, exist_ok=False)
    source = ROOT / "experiments/phase9/p8_mining_20261124_pickaxe_milestone"
    for path in source.iterdir():
        if path.suffix in (".json", ".jsonl"):
            shutil.copy2(path, args.copy_dir / path.name)
    path = args.copy_dir / "controller.jsonl"
    row = json.loads(path.read_text())
    row["update"] = None
    path.write_text(json.dumps(row) + "\n", encoding="utf-8", newline="\n")
    atomic_json(args.copy_dir / "COPY_TEST_ONLY.json", {"not_a_live_trial": True,
        "original_unchanged": str(source), "deliberate_mutation": "controller update = null"})
    try:
        audit_run(args.copy_dir)
    except EvidenceError as error:
        assert error.code == "evidence_schema"
        request = request_fix(Path(__file__).resolve().parent / "handoff_example",
            "TEST ONLY — deliberately corrupted copy, not a live episode failure: " + str(error),
            code=error.code, attempt={"run_id": "OFFLINE_COPY_TEST_NOT_A_TRIAL", "results": str(args.copy_dir),
                                      "status": "test_example", "not_a_live_trial": True})
        assert request["automatic_code_changes"] is False
    else:
        raise AssertionError("Corrupted evidence passed the checker")


if __name__ == "__main__":
    main()
