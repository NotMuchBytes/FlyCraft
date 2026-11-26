"""Re-audit the declared checker pilot; never changes its gameplay evidence."""

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from autonomy.evidence import audit_run, file_sha256
from autonomy.experiment import source_manifest, atomic_json
from tools.milestone_video import FFMPEG

FOLDER = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-dir", type=Path, required=True)
    args = parser.parse_args()
    pilot = json.loads((FOLDER / "pilot_results.json").read_text())
    plan = json.loads((FOLDER / "pilot_plan.json").read_text())
    assert pilot["complete"] and pilot["official_training_worlds"] == 0
    reports, groups, milestone_run = [], {}, None
    for campaign in pilot["campaigns"]:
        for attempt in campaign["attempts"]:
            report = audit_run(Path(attempt["results"]))
            original = json.loads(Path(attempt["checker_report"]).read_text())
            assert report == original
            assert report["implementation_sha256"] == plan["source"]["implementation_sha256"]
            reports.append(report)
            for episode in report["episodes"]:
                group = campaign["name"]
                groups.setdefault(group, []).append(episode)
            if report["video"]:
                milestone_run = attempt["run_id"]
    assert sum(len(rows) for rows in groups.values()) == plan["expected_scored_episodes"]
    original = json.loads((FOLDER.parent / "phase8_finish_20261124/artifact_integrity_closeout.json").read_text())
    assert file_sha256(ROOT / "data/processed/connectome_raw_csr.npz") == original["graph"]["sha256"]
    preserved = original["preserved_checkpoints"] | {row["path"]: row["sha256"] for row in original["fits"]}
    assert all(file_sha256(ROOT/path) == digest for path, digest in preserved.items())
    old_source = json.loads((FOLDER.parent / "p8_mining_20261124_pickaxe_milestone/source_manifest.json").read_text())["files"]
    current = source_manifest(ROOT)
    changed = sorted(path for path in old_source.keys() | current["files"].keys()
                     if old_source.get(path) != current["files"].get(path))
    assert set(changed) <= {"autonomy/experiment.py", "autonomy/evidence.py", "tools/run_phase9.py",
                            "tools/obs_session.py", "tools/supervise_phase9.py"}
    stop_campaign, = [row for row in pilot["campaigns"] if row["name"] == "checker24_stop"]
    interrupted = stop_campaign["attempts"][0]
    stop_path = Path(interrupted["results"])
    events = [json.loads(line) for line in (stop_path / "headless.jsonl").read_text().splitlines()]
    command = next(row["data"]["command_id"] for row in events if row["event"] == "action_start"
                   and row["data"]["action"] == "COLLECT_LOG")
    credited = any(row["event"] == "action_end" and row["data"]["ack"]["command_id"] == command
                   and row["data"]["ack"]["status"] == "success" for row in events)
    stop = {"first_attempt_status": interrupted["status"], "run_id": interrupted["run_id"],
            "mining_command_id": command, "mining_acknowledged_success": credited,
            "committed_episodes": stop_campaign["summary"]["committed_episodes"],
            "generated_world_instances": stop_campaign["summary"]["generated_world_instances"],
            "scored_before_stop": interrupted["status"] == "committed"}
    if not stop["scored_before_stop"]:
        assert not credited and len(stop_campaign["attempts"]) == 2
        first, second = stop_campaign["attempts"]
        assert first["world_seed"] == second["world_seed"] and first["run_id"] != second["run_id"]
    assert milestone_run
    directory = FOLDER.parent / milestone_run
    meta = json.loads((directory / "run.json").read_text())
    frames = []
    args.review_dir.mkdir(parents=True, exist_ok=False)
    video = Path(meta["milestone_video_export"])
    for index, fraction in enumerate((.05, .22, .40, .58, .76, .94)):
        seconds = fraction * meta["milestone_video"]["duration_seconds"]
        target = args.review_dir / f"frame_{index}_{seconds:.3f}s.png"
        subprocess.run([str(FFMPEG), "-nostdin", "-n", "-v", "error", "-threads", "2", "-filter_threads", "1",
                        "-ss", str(seconds), "-i", str(video), "-frames:v", "1", "-update", "1", str(target)], check=True)
        frames.append({"seconds": seconds, "path": str(target)})
    from PIL import Image, ImageDraw
    sheet = Image.new("RGB", (1440, 584), "#111111")
    draw = ImageDraw.Draw(sheet)
    for index, frame in enumerate(frames):
        x, y = index % 3 * 480, index // 3 * 292
        with Image.open(frame["path"]) as image:
            sheet.paste(image.resize((480, 270)), (x, y))
        draw.text((x+5, y+273), f"Original video at {frame['seconds']:.3f}s", fill="white")
    sheet.save(args.review_dir / "contact_sheet.png")
    proof_dir = (ROOT / "experiments/phase9/checker24_pick/capture_proof")
    proof_dir.mkdir(exist_ok=False)
    for kind in ("game", "obs"):
        proof = meta["capture_content_proof"]
        source = Path(proof[kind + "_frame"])
        assert file_sha256(source) == proof[kind + "_frame_sha256"]
        shutil.copy2(source, proof_dir / (kind + ".png"))
    result = {"complete": True, "functional_validation_only": True, "episodes": groups,
              "scored_episodes": sum(len(rows) for rows in groups.values()),
              "generated_world_instances": sum(row["summary"]["generated_world_instances"] for row in pilot["campaigns"]),
              "training_updates": sum(row["summary"]["training_updates"] for row in pilot["campaigns"]),
              "stop_resume": stop, "milestone_run": milestone_run, "milestone_video": str(video),
              "milestone_goal_success": reports[[r["run_id"] for r in reports].index(milestone_run)]["episodes"][0]["success"],
              "milestone_frames": frames, "contact_sheet": str(args.review_dir / "contact_sheet.png"),
              "manual_visual_review": "pending", "graph_unchanged": True, "original_checkpoints_unchanged": True,
              "actor_source_unchanged": True, "changed_coordination_files": changed,
              "pilot_source_sha256": plan["source"]["implementation_sha256"],
              "review_source_sha256": current["implementation_sha256"], "official_training_worlds": 0}
    assert not (FOLDER / "pilot_audit.json").exists()
    atomic_json(FOLDER / "pilot_audit.json", result)
    print(json.dumps({key: value for key, value in result.items() if key not in ("episodes", "milestone_frames")}, indent=2))


if __name__ == "__main__":
    main()
