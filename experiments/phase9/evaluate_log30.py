"""Audit a fixed 30-seed log or plank evaluation and export actual outcomes."""

import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.analyze_phase8 import wilson
from tools.analyze_live_navigation import analyze_run
from autonomy.experiment import verified_terminal_inventory
from experiments.phase9.compare_movement import fixture


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def only_row(path):
    rows = Path(path).read_text(encoding="utf-8").splitlines()
    if len(rows) != 1:
        raise ValueError(f"expected one episode: {path}")
    return json.loads(rows[0])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    plan, state = read(args.campaign / "evaluation_plan.json"), read(args.campaign / "state.json")
    goal = plan["goal"]
    item, count, target, title = {"one_log":("log",1,24,"one-log"),
                                "planks":("planks",4,21,"four-plank")}[goal]
    if plan["target_successes"] != target:
        raise ValueError("target differs from the stated Phase 8 criterion")
    rows = [a for a in state["attempts"] if a["status"] == "committed"]
    if len(rows) != 30 or state["active_attempt"] is not None or len(set(a["world_seed"] for a in rows)) != 30:
        raise ValueError("evaluation must have exactly 30 completed distinct seeds and no active attempt")
    if [a["world_seed"] for a in rows] != plan["seeds"]:
        raise ValueError("scored seeds differ from the predeclared plan")
    outcomes, relative_fixtures, resources, audits = [], set(), [], []
    accepted_sources = {plan["source_sha256"]}
    for revision in state.get("validation_revisions", []):
        if revision["changed_files"] != ["autonomy/experiment.py"] or revision["previous_source_sha256"] not in accepted_sources:
            raise ValueError("non-validation source changes during evaluation")
        accepted_sources.add(revision["source_sha256"])
    for a in rows:
        folder = ROOT / "experiments/phase9" / a["run_id"]
        run = read(folder / "run.json")
        score, controller = only_row(folder / "server.jsonl"), only_row(folder / "controller.jsonl")
        delivery = only_row(folder / "server.jsonl.delivery.jsonl")
        if a["train"] or controller["train"] or a["update"]["weight_delta_norm"] != 0:
            raise ValueError("evaluation learned")
        if a["checkpoint"]["sha256"] != plan["checkpoint_sha256"] or run["implementation_sha256"] not in accepted_sources:
            raise ValueError("checkpoint or implementation differs from plan")
        if run["forward_ticks"] != plan["forward_ticks"] or run["trial_tick_limit"] != plan["trial_tick_limit"] \
                or run["camera_mode"] != plan["camera_mode"] or run["turn_degrees"] != plan["turn_degrees"] \
                or run["policy_rng_seed"] != plan["policy_seeds"][a["episode_number"]-1] \
                or score["layout_seed"] != a["world_seed"]:
            raise ValueError("motor, deadline, RNG or layout differs from plan")
        if not delivery["acknowledged"] or not run["server_exited_cleanly"]:
            raise ValueError("delivery or clean server exit missing")
        success = score["inventory"][item] >= count
        if not (a["success"] == score["success"] == controller["success"] == success):
            raise ValueError("inventory scoring disagreement")
        terminal_inventory, terminal_source = verified_terminal_inventory(folder,score,controller)
        if any(terminal_inventory.get(key) != value for key,value in score["inventory"].items()):
            raise ValueError("terminal inventory disagreement")
        required = a["episode_number"] in plan["recorded_episode_numbers"]
        if required != a["video_required"]:
            raise ValueError("recording plan changed")
        if required:
            video = a["video"]
            if not video["full_decode_verified"] or not video["episode_coverage_complete"] or not run["client_exited_cleanly"]:
                raise ValueError("milestone coverage missing")
            if hashlib.sha256(Path(video["path"]).read_bytes()).hexdigest() != video["sha256"]:
                raise ValueError("milestone MP4 changed")
        elif run["spectator"] or run["recording"] is not None or a["video"] is not None:
            raise ValueError("routine episode was unexpectedly recorded")
        initial = fixture(folder)
        if any(initial["inventory"].values()):
            raise ValueError("evaluation did not start with an empty inventory")
        relative_fixtures.add(json.dumps(initial, sort_keys=True))
        audit = analyze_run(folder); audits.append(audit)
        pickup_observed = False
        for line in (folder / "bridge.jsonl").read_text(encoding="utf-8").splitlines():
            request = json.loads(line)["request"]
            if isinstance(request,str): request = json.loads(request)
            pickup_observed |= request.get("telemetry",{}).get("inventory",{}).get("log",0) >= 1
        broken = controller.get("confirmed_block_changes", 0)
        outcomes.append({"episode":a["episode_number"], "world_seed":a["world_seed"],
            "success":success, "ticks":score["ticks"], "actions":controller["actions"],
            "inventory_log":score["inventory"]["log"], "confirmed_block_changes":broken,
            "inventory_planks":score["inventory"]["planks"],
            "log_pickup_observed":pickup_observed,
            "craft_actions_acknowledged":sum(m["action"]=="CRAFT_PLANKS" for m in audit["motions"]),
            "craft_success_acks":sum(m["action"]=="CRAFT_PLANKS" and m["ack_status"]=="success" for m in audit["motions"]),
            "failed_actions":controller["failed_actions"], "recoveries":controller["recovery_attempts"],
            "failure_mode":None if success else "collected_without_crafting" if goal=="planks" and score["inventory"]["log"] else "mined_without_pickup" if broken else "no_confirmed_block_break",
            "recorded_milestone":required, "longest_unseen_decisions":audit["longest_unseen_decision_streak"],
            "near_zero_forward_samples":sum(m["action"] == "FORWARD" and m["ack_status"] == "success"
                                             and m["horizontal_displacement"] < .02 for m in audit["motions"]),
            "terminal_inventory_source":terminal_source,
            "wall_seconds":run["elapsed_seconds"], "run_id":a["run_id"]})
        resources.append(run)
    successes = sum(row["success"] for row in outcomes)
    result = {"environment":plan["environment"], "stage":"fixed development evaluation, not final Set B",
        "episodes":30, "distinct_world_seeds":30, "distinct_relative_fixture_snapshots":len(relative_fixtures),
        "generated_world_instances":sum(a.get("generated_world_instances") or 0 for a in state["attempts"]),
        "total_attempts":len(state["attempts"]),
        "successes":successes, "success_rate":successes/30, "wilson_95":wilson(successes,30),
        "point_target_met":successes >= target, "target_successes":target, "goal":goal, "forward_ticks":plan["forward_ticks"],
        "mean_actions_all":statistics.fmean(row["actions"] for row in outcomes),
        "mean_actions_success":statistics.fmean(row["actions"] for row in outcomes if row["success"]) if successes else None,
        "mean_game_seconds_all":statistics.fmean(row["ticks"]/20 for row in outcomes),
        "trials_with_log_pickup_observed":sum(row["log_pickup_observed"] for row in outcomes),
        "craft_actions_acknowledged":sum(row["craft_actions_acknowledged"] for row in outcomes),
        "craft_success_acknowledgments":sum(row["craft_success_acks"] for row in outcomes),
        "worker_wall_seconds":sum(row["wall_seconds"] for row in outcomes),
        "maximum_sampled_gpu_c":max(r["maximum_sampled_gpu_c"] for r in resources if r["maximum_sampled_gpu_c"] is not None),
        "minimum_available_ram_mib":min(r["minimum_sampled_available_ram_mib"] for r in resources),
        "recorded_milestones":[row["episode"] for row in outcomes if row["recorded_milestone"]],
        "event_only_episodes":sum(not row["recorded_milestone"] for row in outcomes),
        "checkpoint_sha256":plan["checkpoint_sha256"], "source_sha256":plan["source_sha256"],
        "validation_source_revisions":state.get("validation_revisions", []),
        "source_hash_episode_counts":dict(Counter(r["implementation_sha256"] for r in resources)),
        "policy_updated":False, "neural_learning_gain_established":False,
        "all_initial_inventories_empty":True,
        "interrupted_attempts":[a for a in state["attempts"] if a["status"] != "committed"],
        "outcomes":outcomes, "navigation_audits":audits,
        "limitations":"Prepared near-tree flat fixtures and semantic sensors; distinct seeds can share relative layout geometry. Motor setting selected on prior development seeds. Fixed policy evaluation only; no untouched final benchmark or natural-world autonomy claim."}
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "validation.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8",newline="\n")
    with (args.output / "episodes.csv").open("w",encoding="utf-8",newline="") as handle:
        writer = csv.DictWriter(handle,fieldnames=list(outcomes[0]),lineterminator="\n")
        writer.writeheader(); writer.writerows(outcomes)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1,2,figsize=(12,4),layout="constrained")
    x = [row["episode"] for row in outcomes]
    colors = ["#247b58" if row["success"] else "#b94e48" for row in outcomes]
    axes[0].bar(x,[row["actions"] for row in outcomes],color=colors)
    axes[0].set(xlabel="Predeclared evaluation episode",ylabel="Acknowledged actions",title=f"Green: {count} {item} confirmed; red: failure")
    axes[1].bar(x,[row["ticks"]/20 for row in outcomes],color=colors)
    axes[1].axhline(20,color="#666",linestyle="--",linewidth=.8)
    axes[1].set(xlabel="Predeclared evaluation episode",ylabel="Game seconds",title="Failures included; 20-second deadline")
    fig.suptitle(f"Real Minecraft strict {title} evaluation: {successes}/30 · fixed trained policy, 2-tick forward\nControlled prepared-tree fixtures; no learning-gain or natural-terrain claim",fontsize=11)
    fig.savefig(args.output / "outcomes.png",dpi=160); plt.close(fig)
    print(json.dumps({k:v for k,v in result.items() if k not in ("outcomes","navigation_audits","interrupted_attempts")},indent=2))


if __name__ == "__main__":
    main()
