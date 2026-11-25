"""Separate, matched evaluation pilot. Never trains or touches official seeds."""
import argparse
import json
from pathlib import Path
import sys
import time

import psutil

ROOT = Path("C:/Users/anass/Documents/FlyCraft")
sys.path.insert(0, str(ROOT))
from autonomy.experiment import Campaign, CampaignLock, atomic_json
from tools.supervise_phase9 import supervise

BASE = Path(__file__).parent
CACHE = ROOT / ".runtime/launch_cache_perf25/manifest.json"
OFFICIAL = ROOT / "experiments/phase9/fc9_20261125"
initial = json.loads((OFFICIAL / "state.json").read_text())["current_checkpoint"]["path"]
reference = ROOT / "checkpoints/phase7/curriculum_v3_seed29.npz"
plans = []
for goal, trials, modes in (("one_log", 2, ("legacy", "cached", "fast")), ("wooden_pickaxe", 1, ("legacy", "fast"))):
    for mode in modes:
        name = f"perf25_{'log' if goal == 'one_log' else 'pick'}_{mode}"
        folder = ROOT / "experiments/phase9" / name
        campaign = Campaign.create(folder, project_root=ROOT, name=name, checkpoint=initial,
            frozen_checkpoint=reference, worlds=trials, master=202611251201 if goal == "one_log" else 202611251202,
            compact=True, forward_ticks=2, goal=goal, checked=True, recording_policy="milestones",
            recording_milestones=(1,) if goal == "wooden_pickaxe" else (100,),
            launch_cache=CACHE if mode != "legacy" else None, continuous_readiness=mode == "fast")
        plans.append(dict(goal=goal, trials=trials, mode=mode, folder=str(folder)))

catalog = json.loads((OFFICIAL / "seeds.json").read_text())
reserved = {seed for key in ("pilot", "training", "eval_a", "eval_b") for seed in catalog[key]}
for plan in plans:
    seeds = json.loads((Path(plan["folder"]) / "seeds.json").read_text())["eval_a"][:plan["trials"]]
    assert not set(seeds) & reserved
    plan["seeds"] = seeds
for goal in {p["goal"] for p in plans}:
    assert len({tuple(p["seeds"]) for p in plans if p["goal"] == goal}) == 1
atomic_json(BASE / "performance_pilot25_plan.json", dict(plans=plans, initial_checkpoint=initial, learning=False))

for plan in plans:
    # Do not let a recorded development pilot contend with an existing job.
    while psutil.virtual_memory().available / 1024**2 < (3300 if plan["goal"] == "wooden_pickaxe" else 2000):
        time.sleep(2)
    args = argparse.Namespace(split="eval_a", condition="trained", max_attempts=plan["trials"],
        seconds=900, worker_seconds=300, work_dir=BASE, build_dir=ROOT / ".runtime/build_reply_loss_20261107",
        obs_control_dir=Path("C:/Users/anass/Documents/Codex/2026-10-27/files-pasted-by-the-user-flycraft/work"),
        video_export_dir=BASE.parent / "outputs")
    with CampaignLock(Path(plan["folder"])):
        campaign = Campaign(plan["folder"], project_root=ROOT)
        started = time.monotonic()
        result = supervise(campaign, args)
        plan["total_coordinator_seconds"] = time.monotonic() - started
        plan["summary"] = campaign.summary()
        print(json.dumps(dict(goal=plan["goal"], mode=plan["mode"], result=result,
            completed=plan["summary"]["committed_episodes"], seconds=plan["total_coordinator_seconds"])), flush=True)
        if result or plan["summary"]["committed_episodes"] != plan["trials"]:
            raise RuntimeError("pilot needs attention: " + plan["folder"])
atomic_json(BASE / "performance_pilot25_finished.json", dict(plans=plans, initial_checkpoint=initial, learning=False))
