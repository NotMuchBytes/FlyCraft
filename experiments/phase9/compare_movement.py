"""Compare frozen motor settings from real episode evidence, not simulated replay."""

import argparse
import json
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.analyze_live_navigation import analyze_run
from tools.analyze_phase8 import wilson


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def fixture(folder):
    snapshot = json.loads((folder / "server.jsonl.initial.jsonl").read_text().splitlines()[0])
    x, y, z, yaw, pitch = snapshot["position_xyz_yaw_pitch"]
    blocks = sorted((tuple(round(p-o, 6) for p, o in zip(b["position"], (x,y,z))), b["state"])
                    for b in snapshot["fixture_blocks"])
    return {"relative_blocks": blocks, "inventory": snapshot["inventory"],
            "yaw": yaw, "pitch": pitch, "mode": snapshot["game_mode"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaigns", nargs=2, type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    configs = [read(p / "config.json") for p in args.campaigns]
    if configs[0]["initial_checkpoint"] != configs[1]["initial_checkpoint"]:
        raise ValueError("policies differ")
    if configs[0]["implementation_sha256"] != configs[1]["implementation_sha256"]:
        raise ValueError("source differs")
    profiles = [{k:v for k,v in c["runtime_profile"].items() if k != "forward_ticks"} for c in configs]
    if profiles[0] != profiles[1]:
        raise ValueError("other runtime settings differ")
    groups, indexed, audits = {}, [], []
    for campaign, config in zip(args.campaigns, configs):
        state = read(campaign / "state.json")
        rows = [a for a in state["attempts"] if a["status"] == "committed" and a["split"] == "eval_a" and a["condition"] == "trained"]
        if not rows or state["active_attempt"] is not None:
            raise ValueError("campaign is empty or active")
        indices = {a["world_seed"]: a for a in rows}
        if len(indices) != len(rows):
            raise ValueError("multiple checkpoint evaluations require explicit selection")
        indexed.append(indices)
        success = sum(a["success"] for a in rows)
        summaries = []
        for a in rows:
            folder = ROOT / "experiments/phase9" / a["run_id"]
            run = read(folder / "run.json")
            if a["train"] or a["update"]["weight_delta_norm"] or run.get("forward_ticks") != config["runtime_profile"]["forward_ticks"]:
                raise ValueError("learning or movement configuration mismatch")
            audit = analyze_run(folder)
            audits.append(audit)
            summaries.append({"run_id":a["run_id"], "seed":a["world_seed"], "success":a["success"],
                "ticks":a["ticks"], "actions":a["actions"],
                "terminal_inventory":json.loads((folder / "server.jsonl").read_text().splitlines()[0])["inventory"],
                "median_forward_displacement":audit["median_forward_displacement"],
                "target_losses":audit["forward_target_losses"],
                "longest_unseen_decisions":audit["longest_unseen_decision_streak"],
                "video_sha256":a["video"]["sha256"], "video_path":a["video"]["path"]})
        groups[campaign.name] = {"forward_ticks": config["runtime_profile"]["forward_ticks"],
            "successes":success, "episodes":len(rows), "wilson_95":wilson(success,len(rows)),
            "mean_actions":statistics.fmean(a["actions"] for a in rows),
            "mean_game_seconds":statistics.fmean(a["ticks"]/20 for a in rows), "episodes_data":summaries}
    if indexed[0].keys() != indexed[1].keys():
        raise ValueError("seeds differ")
    pairs = []
    for seed, a in indexed[0].items():
        b = indexed[1][seed]
        if a["policy_seed"] != b["policy_seed"] or a["checkpoint"] != b["checkpoint"]:
            raise ValueError("RNG or checkpoint differs")
        folders = [ROOT / "experiments/phase9" / row["run_id"] for row in (a,b)]
        runs = [read(p / "run.json") for p in folders]
        for key in ("trial_tick_limit", "camera_mode", "turn_degrees", "interaction_assistance"):
            if runs[0][key] != runs[1][key]:
                raise ValueError(f"{key} differs")
        if fixture(folders[0]) != fixture(folders[1]):
            raise ValueError("initial relative fixture or inventory differs")
        pairs.append({"seed":seed,"baseline_success":a["success"],"candidate_success":b["success"],
                      "same_relative_fixture_inventory_orientation":True})
    result = {"stage":"adaptive development, real Minecraft controlled fixtures",
        "policy_sha256":configs[0]["initial_checkpoint"]["sha256"], "source_sha256":configs[0]["implementation_sha256"],
        "conditions":groups,"paired_worlds":pairs,"navigation_audits":audits,
        "full_rng_matched":False,"final_b_used":False,"neural_learning_improvement_established":False,
        "limitation":"Reused development layouts, small sample, unrecorded complete world/entity RNG; motor change only, no policy updates."}
    with args.output.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(result,handle,indent=2,allow_nan=False); handle.write("\n")
    print(args.output)


if __name__ == "__main__":
    main()
