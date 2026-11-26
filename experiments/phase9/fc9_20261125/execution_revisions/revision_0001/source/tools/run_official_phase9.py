"""Explicitly authorized 10,000-world training, with checked bounded batches."""

import argparse
import json
import os
from pathlib import Path
import sys
import time

import psutil

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from autonomy.experiment import Campaign, CampaignLock, atomic_json
from autonomy.official import cleanup_world
from tools.run_phase9 import dashboard
from tools.supervise_phase9 import supervise, request_fix

OFFICIAL_MILESTONES = (1, 2, 3, 4, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 7500, 10000)


def run(campaign, args, *, batch=supervise):
    if not campaign.official or campaign.config["world_limit"] != 10000:
        raise ValueError("an authorized frozen 10000-world plan is required")
    atomic_json(campaign.folder / "executor.json", {"pid": os.getpid(),
        "process_created": psutil.Process().create_time(), "started_unix": time.time(),
        "status": "running", "automatic_final_evaluation": False})
    # Batch limits remain bounded. This explicit executor is the only long-run
    # entry point; it never clears STOP or attention requests between batches.
    args.split, args.condition = "training", "trained"
    args.max_attempts, args.seconds, args.worker_seconds = 100, 3600, 300
    while not (campaign.folder / "STOP").exists():
        if (campaign.folder / "fix_request.json").exists():
            return 2
        for attempt in campaign.state["attempts"]:
            cleanup_world(campaign, attempt, args.work_dir)
        if campaign.training_worlds() >= campaign.config["world_limit"]:
            if campaign.state["final_policy"] is None:
                campaign.freeze_final()
            atomic_json(campaign.folder / "executor.json", {"status": "training_budget_complete",
                "official_training_worlds": campaign.training_worlds(), "automatic_final_evaluation": False,
                "final_checkpoint": campaign.state["final_policy"], "updated_unix": time.time()})
            dashboard(campaign, "training budget complete; final evaluation pending")
            return 0
        outcome = batch(campaign, args, official=True)
        if outcome:
            return outcome
    atomic_json(campaign.folder / "executor.json", {"status": "paused", "updated_unix": time.time(),
                                                  "official_training_worlds": campaign.training_worlds()})
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init")
    init.add_argument("--name", required=True)
    init.add_argument("--checkpoint", type=Path, required=True)
    init.add_argument("--frozen-checkpoint", type=Path, required=True)
    init.add_argument("--authorization", required=True, help="Actual explicit user instruction; not inferred")
    init.add_argument("--authorized-date", required=True)
    init.add_argument("--master-seed", type=int, required=True)
    init.add_argument("--compact", action="store_true")
    start = commands.add_parser("run")
    for name in ("campaign", "work-dir", "build-dir", "obs-control-dir", "video-export-dir"):
        start.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    if args.command == "init":
        campaign = Campaign.create(ROOT / "experiments/phase9" / args.name, project_root=ROOT,
            name=args.name, checkpoint=args.checkpoint, frozen_checkpoint=args.frozen_checkpoint,
            master=args.master_seed, worlds=10000, compact=args.compact, forward_ticks=2,
            checked=True, official=True, authorization={"statement": args.authorization, "authorized_date": args.authorized_date},
            recording_policy="milestones", recording_milestones=OFFICIAL_MILESTONES)
        campaign.save()
        dashboard(campaign, "authorized plan frozen; not launched")
        print(campaign.folder)
        return 0
    acquired = False
    try:
        with CampaignLock(args.campaign):
            acquired = True
            campaign = Campaign(args.campaign, project_root=ROOT)
            return run(campaign, args)
    except Exception as error:
        if acquired:
            request_fix(args.campaign, error, code="official_executor")
        else:
            print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
