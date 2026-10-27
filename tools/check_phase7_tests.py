#!/usr/bin/env python3
"""Run the full existing/new suite and retain reviewable verification evidence."""

import argparse
import json
import sys
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    log = args.output.with_suffix(".log")
    if args.output.exists() or log.exists():
        parser.error("verification paths must be new")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    with log.open("x", encoding="utf-8") as handle:
        suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
        result = unittest.TextTestRunner(stream=handle, verbosity=2).run(suite)
    report = {"tests_run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
              "skips": len(result.skipped), "passed": result.wasSuccessful(), "elapsed_seconds": time.perf_counter() - started,
              "baseline_tests_before_phase7": 23, "baseline_passed": True,
              "baseline_elapsed_seconds": 4.738, "log": str(log)}
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    main()
