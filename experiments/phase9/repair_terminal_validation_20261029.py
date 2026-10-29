"""One audited evaluation-record repair; never launch Minecraft or change actions."""

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from autonomy.experiment import Campaign, CampaignLock, atomic_json, source_manifest, verified_terminal_inventory


def main():
    folder = ROOT / "experiments/phase9/dev_log30_milestones_20261029"
    with CampaignLock(folder):
        campaign = Campaign(folder, project_root=ROOT)
        if campaign.state["active_attempt"] is not None or len(campaign.state["attempts"]) != 11:
            raise ValueError("expected idle evaluation immediately after trial 11")
        old = json.loads((folder / "source_manifest.json").read_text())
        new = source_manifest(ROOT)
        changed = sorted(k for k in old["files"].keys() | new["files"].keys()
                         if old["files"].get(k) != new["files"].get(k))
        if changed != ["autonomy/experiment.py"]:
            raise ValueError("unexpected source changes; no repair performed")
        attempt = campaign.state["attempts"][-1]
        if attempt["status"] != "interrupted" or attempt.get("error") != "'terminal_inventory'" or attempt["train"]:
            raise ValueError("this repair only addresses the audited missing evaluation terminal field")
        results = ROOT / "experiments/phase9" / attempt["run_id"]
        score = json.loads((results / "server.jsonl").read_text().splitlines()[0])
        outcome = json.loads((results / "controller.jsonl").read_text().splitlines()[0])
        inventory, source = verified_terminal_inventory(results, score, outcome)
        if not score["success"] or not outcome["success"] or inventory["log"] < 1 or source != "acknowledged_bridge_boundary":
            raise ValueError("audited inventory evidence does not establish the recorded success")
        backup = folder / "state.before_terminal_validation_repair.json"
        if backup.exists():
            raise ValueError("repair already attempted; preserve prior history")
        atomic_json(backup, campaign.state)
        attempt["prior_validation_error"] = attempt.pop("error")
        attempt["original_validation_finished_unix"] = attempt["finished_unix"]
        attempt["validation_recovered_without_gameplay"] = True
        attempt["status"] = "running"
        campaign.state["active_attempt"] = len(campaign.state["attempts"]) - 1
        campaign.save()
        repaired = campaign.recover()
        if repaired["status"] != "committed":
            raise ValueError("full evidence revalidation did not commit; stopped")
        revision = campaign.amend_validation_only(
            "Evaluation success was written before its terminal_inventory field. Validate the unchanged raw acknowledged boundary instead; no actor, controller, runner, seeds, policy, affordances or limits changed. Preserve original files and rejection, and continue the same 30-seed plan without replay or replacement.")
        atomic_json(folder / "validation_amendment.json", revision)
        print(json.dumps({"episode":11,"success":repaired["success"],"terminal_inventory_source":repaired["terminal_inventory_source"],
                          "new_game_executions":0,"revision":revision},indent=2))


if __name__ == "__main__":
    main()
