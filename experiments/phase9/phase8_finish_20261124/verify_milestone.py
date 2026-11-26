"""Audit original selected-readout milestone footage and extract review frames."""

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from experiments.phase9.phase75_reliability_20261117.audit import audit
from tools.milestone_video import FFMPEG, file_digest, verify_mp4

FOLDER = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--frames-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    plan = json.loads((FOLDER / "milestone_plan.json").read_text())
    directory = FOLDER.parent / args.run_id
    meta = json.loads((directory / "run.json").read_text())
    media = json.loads((ROOT / "recordings/phase9/youtube" / (args.run_id + ".json")).read_text())
    frozen = json.loads((FOLDER / "heldout_plan.json").read_text())
    assert meta["implementation_sha256"] == frozen["implementation_sha256"]
    assert meta["conditions"] == ["trained"] and meta["interaction_assistance"] == "crosshair_only_no_automatic_aim"
    assert meta["available_ram_guard_mib"] == 768 and meta["free_disk_guard_mib"] == 2048
    assert meta["world_seed"] == plan["world_seed"] and meta["layout_seeds"] == [plan["layout_seed"]]
    assert meta["checkpoint_sha256"] == plan["checkpoint_sha256"]
    assert meta["policy_rng_seed"] == plan["policy_seed"]
    assert meta["goals"] == [plan["goal"]] and meta["requested"] == meta["completed"] == 1
    assert all(meta[key] == plan[key] for key in ("forward_ticks", "turn_degrees", "pitch_actions", "remember_mined_columns", "trial_tick_limit"))
    assert meta["stop_reason"] == "suite_complete" and meta["milestone_video_status"] == "verified"
    assert meta["spectator_view"] == "first_person" and meta["recording_mode"] == "OBS_isolated_spectator"
    assert meta["capture_content_proof"]["matched"] and meta["train"] is False
    assert media["replay"] is False and media["actions_altered_for_video"] is False
    assert any("Using graphics device: NVIDIA GeForce RTX 4050" in line for line in meta["actual_graphics"])
    report = audit(args.run_id)
    episode, = report["episodes"]
    assert episode["verified"] and episode["success"] and episode["inventory"]["wooden_pickaxe"] >= 1
    assert episode["confirmed_breaks"] >= 3 and episode["actions"] <= plan["policy_action_limit"]
    assert all(episode["confirmed_crafting_and_placement"].get(action) for action in
               ("CRAFT_PLANKS", "CRAFT_STICKS", "CRAFT_TABLE", "PLACE_TABLE", "CRAFT_PICKAXE"))
    controller, = map(json.loads, (directory / "controller.jsonl").read_text().splitlines())
    assert controller["train"] is False and controller["update"]["weight_delta_norm"] == 0
    video = Path(meta["milestone_video_export"])
    verified = verify_mp4(video, minimum_seconds=episode["game_seconds"])
    assert verified["sha256"] == meta["milestone_video"]["sha256"]
    assert meta["milestone_video"]["episode_coverage_complete"]
    proof_archive = {}
    for kind in ("game", "obs"):
        original = Path(meta["capture_content_proof"][kind + "_frame"])
        expected_hash = meta["capture_content_proof"][kind + "_frame_sha256"]
        assert file_digest(original) == expected_hash
        preserved = directory / ("capture_" + kind + ".png")
        if not preserved.exists():
            shutil.copy2(original, preserved)
        assert file_digest(preserved) == expected_hash
        proof_archive[kind] = {"path": str(preserved), "sha256": expected_hash}
    args.frames_dir.mkdir(parents=True, exist_ok=False)
    frames = []
    for index, fraction in enumerate((.03, .2, .4, .6, .8, .97)):
        seconds = fraction * verified["duration_seconds"]
        target = args.frames_dir / f"frame_{index}_{seconds:.3f}s.png"
        subprocess.run([str(FFMPEG), "-nostdin", "-n", "-v", "error", "-threads", "2", "-filter_threads", "1",
                        "-ss", str(seconds), "-i", str(video), "-frames:v", "1", "-update", "1", str(target)], check=True, timeout=20)
        frames.append({"seconds": seconds, "path": str(target)})
    from PIL import Image, ImageDraw
    sheet = Image.new("RGB", (1440, 584), "#111111")
    draw = ImageDraw.Draw(sheet)
    for index, frame in enumerate(frames):
        x, y = index % 3 * 480, index // 3 * 292
        with Image.open(frame["path"]) as original:
            sheet.paste(original.resize((480, 270)), (x, y))
        draw.text((x + 5, y + 273), f"Original video frame at {frame['seconds']:.3f}s", fill="white")
    sheet_path = args.frames_dir / "contact_sheet.png"
    sheet.save(sheet_path)
    result = {"run_id": args.run_id, "execution_kind": "Fresh development execution, not a replay or primary score",
              "video_path": str(video), "video": verified, "actual_graphics": meta["actual_graphics"],
              "capture_content_proof": meta["capture_content_proof"], "episode": episode,
              "preserved_capture_frames": proof_archive,
              "frames": frames, "contact_sheet": str(sheet_path),
              "manual_visual_review": "Pending explicit inspection; this script only verifies and extracts real footage"}
    with args.output.open("x", encoding="utf-8", newline="\n") as output:
        json.dump(result, output, indent=2, allow_nan=False)
        output.write("\n")
    print(json.dumps({"video": verified, "actions": episode["actions"], "inventory": episode["inventory"], "contact_sheet": str(sheet_path)}, indent=2))


if __name__ == "__main__":
    main()
