#!/usr/bin/env python3
"""Summarize measured live camera probes; these are motor tests, not AI trials."""

import argparse
import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIC_CASES = {"small_yaw", "small_negative_yaw", "medium_yaw", "medium_negative_yaw",
                "large_yaw", "wrap_180", "pitch_upper_clamp", "pitch_lower_clamp", "duplicate_and_stale"}


def read_run(name):
    folder = ROOT / "experiments/phase8" / name
    metadata = json.loads((folder / "run.json").read_text(encoding="utf-8-sig"))
    if metadata["experiment_kind"] != "scripted_camera_probe_not_policy":
        raise ValueError("Only separately labeled motor probes are accepted")
    trace = [json.loads(line) for line in (folder / "camera.jsonl").read_text().splitlines()]
    probe = [json.loads(line) for line in (folder / "camera_probe.jsonl").read_text().splitlines()]
    configuration = next(row["data"] for row in trace if row["event"] == "configuration")
    cases = []
    for row in probe:
        if row["event"] not in {"case_complete", "case_failed", "case_skipped"}:
            continue
        case = dict(row["data"], event=row["event"])
        camera = [r for r in trace if r["episode_id"] == "camera_probe:" + case["case"]]
        completed = [r["data"] for r in camera if r["event"] == "command_complete"]
        frames = [r["data"] for r in camera if r["event"] == "frame"]
        renders = [r for r in camera if r["event"] == "render_frame"]
        case["measured_render_frames"] = len(renders)
        case["accepted_requests"] = sum(r["data"]["acceptance"]["accepted"] for r in camera if r["event"] == "request")
        for field in ("peak_yaw_velocity", "peak_pitch_velocity", "peak_yaw_acceleration", "peak_pitch_acceleration"):
            case[field] = max((r[field] for r in completed), default=None)
        for axis in ("yaw", "pitch"):
            values = [r["frame"][axis+"Overshoot"] for r in frames if r["frame"][axis+"Overshoot"] is not None]
            case["maximum_recorded_"+axis+"_overshoot_deg"] = max(values, default=None)
        if completed:
            final = completed[-1]
            case["last_command_wall_seconds_to_body_settle"] = final["wall_seconds"]
            case["final_command"] = final["final_frame"]
            final_frame=final["final_frame"]
            if final_frame["targetYaw"] is None:
                case["maximum_final_angular_error_deg"] = None
            else:
                yaw_error=final_frame["yawError"]
                yaw_error=(yaw_error+180)%360-180
                case["maximum_final_angular_error_deg"] = max(abs(yaw_error), abs(final_frame["pitchError"]))
        cases.append(case)
    static = [case for case in cases if case["case"] in STATIC_CASES and case["event"] == "case_complete"]
    return {
        "run_id": name, "metadata": metadata, "configuration": configuration,
        "probe_result": json.loads((folder / "camera_probe.jsonl.complete.json").read_text()),
        "cases": cases,
        "static_case_mean_wall_settling_seconds": statistics.mean(c["last_command_wall_seconds_to_body_settle"] for c in static),
        "static_case_maximum_final_angular_error_deg": max(c["maximum_final_angular_error_deg"] for c in static),
        "static_case_maximum_observed_yaw_velocity_deg_s": max(c["peak_yaw_velocity"] for c in static),
        "static_case_maximum_observed_pitch_velocity_deg_s": max(c["peak_pitch_velocity"] for c in static),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", required=True)
    parser.add_argument("--after", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output must be new; preserve previous analyses")
    before, after = read_run(args.before), read_run(args.after)
    for key in ("world_seed", "layout_start", "trial_tick_limit", "checkpoint_sha256", "requested_graphics_backend"):
        if before["metadata"][key] != after["metadata"][key]:
            parser.error("Unmatched " + key)
    if before["configuration"]["limits"] != after["configuration"]["limits"]:
        parser.error("Controller limits differ")
    result = {
        "kind": "matched_scripted_live_minecraft_motor_tests_not_autonomous_goal_evidence",
        "before": before, "after": after,
        "limitations": [
            "One repeat per condition; no statistical generalization claim.",
            "Wall settling is the player-angle and velocity criterion, not a perceptual rating.",
            "Rendered camera samples are preserved, but a pre-command render sample is not always available.",
            "Rapid reversals use the same relative command timing; different actuator progress yields different endpoints.",
            "Instant reference omits its historical extra cooldown and target-aim macros to isolate the actuator.",
            "No mining accuracy, autonomous completion or learning result is inferred from a motor probe.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({key: {field: value for field, value in run.items() if field.startswith("static_case_")}
                      for key, run in (("before", before), ("after", after))}, indent=2))


if __name__ == "__main__":
    main()
