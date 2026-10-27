#!/usr/bin/env python3
"""Run the Phase 3 interface closed-loop without learning."""

from __future__ import annotations

import json
import os
import platform
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import numpy as np
import psutil

from environment import AngularSensor, World2D
from interface import ActionDecoder, SensoryEncoder, select_phase3_populations
from simulator import ConnectomeGraph, LIFSimulator, NeuronConfig, WeightTransformConfig, transform_weights


EPISODES = {
    "target_left": (2.0, 8.0),
    "target_center": (5.0, 8.0),
    "target_right": (8.0, 8.0),
    "target_not_visible": (5.0, 0.0),
}
WORLD_STEPS = 20
NEURAL_STEPS_PER_WORLD_STEP = 6


def run_episode(name: str, target: tuple[float, float], adjacency, graph, encoder, decoder) -> dict[str, object]:
    world = World2D(target_x=target[0], target_y=target[1])
    sensor = AngularSensor()
    sim = LIFSimulator(adjacency, NeuronConfig(decay=0.8, threshold=1.0, reset_value=0.0))
    trajectory = [[world.x, world.y, world.heading]]
    rows: list[dict[str, object]] = []
    encoding_seconds = decoding_seconds = neural_seconds = 0.0
    process = psutil.Process(os.getpid())
    peak_rss = process.memory_info().rss
    started = time.perf_counter()
    for world_step in range(WORLD_STEPS):
        observation = sensor.observe(world)
        accumulated_left = accumulated_right = accumulated_other = accumulated_total = 0
        active_global_peak = 0
        for neural_step in range(NEURAL_STEPS_PER_WORLD_STEP):
            before = time.perf_counter()
            current = encoder.encode(observation.sector, neural_step, intensity=1.0)
            encoding_seconds += time.perf_counter() - before
            before = time.perf_counter()
            metrics = sim.step(current)
            neural_seconds += time.perf_counter() - before
            before = time.perf_counter()
            response = decoder.observe(sim.spikes)
            decoding_seconds += time.perf_counter() - before
            accumulated_left += response.left_activity
            accumulated_right += response.right_activity
            accumulated_other += response.center_activity
            accumulated_total += response.total_activity
            active_global_peak = max(active_global_peak, metrics.active_neurons)
        action = decoder.decode(type(response)(accumulated_left, accumulated_right, accumulated_other, accumulated_total, ()))
        world.step(action)
        trajectory.append([world.x, world.y, world.heading])
        rows.append({
            "world_step": world_step,
            "sensor_visible": observation.visible,
            "sensor_sector": observation.sector,
            "relative_angle": observation.relative_angle,
            "distance": observation.distance,
            "stimulated_neurons": 50 if observation.visible else 0,
            "descending_spikes_left": accumulated_left,
            "descending_spikes_right": accumulated_right,
            "descending_spikes_other": accumulated_other,
            "descending_spikes_total": accumulated_total,
            "global_active_peak": active_global_peak,
            "action": action,
            "state": [world.x, world.y, world.heading],
        })
        peak_rss = max(peak_rss, process.memory_info().rss)
    elapsed = time.perf_counter() - started
    return {
        "name": name,
        "target": list(target),
        "trajectory": trajectory,
        "steps": rows,
        "actions": {action: sum(row["action"] == action for row in rows) for action in ("TURN_LEFT", "TURN_RIGHT", "FORWARD", "NO_OP")},
        "elapsed_seconds": elapsed,
        "closed_loop_steps_per_second": WORLD_STEPS / elapsed,
        "neural_steps_per_second": WORLD_STEPS * NEURAL_STEPS_PER_WORLD_STEP / neural_seconds,
        "sensory_encoding_seconds": encoding_seconds,
        "output_decoding_seconds": decoding_seconds,
        "neural_simulation_seconds": neural_seconds,
        "peak_rss_bytes": peak_rss,
    }


def create_svg(path: Path, episodes: list[dict[str, object]]) -> None:
    colors = ["#1f78b4", "#33a02c", "#e31a1c", "#666666"]
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="900" height="650" viewBox="0 0 900 650">', '<rect width="100%" height="100%" fill="white"/>', '<text x="450" y="30" text-anchor="middle" font-family="sans-serif" font-size="20">Phase 3 deterministic closed-loop trajectories</text>', '<rect x="100" y="60" width="500" height="500" fill="#fafafa" stroke="black"/>']
    for episode, color in zip(episodes, colors):
        points = [f"{100 + p[0]*50:.1f},{560 - p[1]*50:.1f}" for p in episode["trajectory"]]
        tx, ty = episode["target"]
        parts.append(f'<polyline points="{" ".join(points)}" fill="none" stroke="{color}" stroke-width="3"/>')
        parts.append(f'<circle cx="{100+tx*50:.1f}" cy="{560-ty*50:.1f}" r="6" fill="{color}"/>')
    for i, (episode, color) in enumerate(zip(episodes, colors)):
        y = 110 + i * 40
        parts.extend([f'<line x1="650" y1="{y}" x2="680" y2="{y}" stroke="{color}" stroke-width="3"/>', f'<text x="690" y="{y+5}" font-family="sans-serif" font-size="14">{episode["name"]}</text>'])
    parts.extend(['<text x="350" y="595" text-anchor="middle" font-family="sans-serif" font-size="14">Arena x</text>', '<text x="55" y="310" transform="rotate(-90 55 310)" text-anchor="middle" font-family="sans-serif" font-size="14">Arena y</text>', '</svg>'])
    path.write_text("\n".join(parts), encoding="utf-8")


def main() -> None:
    data_dir = ROOT / "data"
    graph = ConnectomeGraph.load(data_dir / "processed")
    inputs, outputs = select_phase3_populations(data_dir)
    encoder = SensoryEncoder.from_population(inputs, graph.neuron_count, neurons_per_sector=50, amplitude=1.05, duration_steps=3)
    decoder = ActionDecoder(outputs)
    adjacency = transform_weights(graph.adjacency_raw, WeightTransformConfig("log1p", 0.08, 32.0))
    episodes = [run_episode(name, target, adjacency, graph, encoder, decoder) for name, target in EPISODES.items()]
    repeated = run_episode("target_left_repeat", EPISODES["target_left"], adjacency, graph, encoder, decoder)
    reproducible = repeated["trajectory"] == episodes[0]["trajectory"] and [r["action"] for r in repeated["steps"]] == [r["action"] for r in episodes[0]["steps"]]
    payload = {
        "architecture": "world -> five-sector sensor -> 50-neuron deterministic encoder -> full connectome -> 1,305-neuron descending decoder -> action -> world",
        "engineering_decoder": "left/right spike-count difference; balanced=FORWARD; no spikes=NO_OP",
        "neural_config": {"weight_transform": "log1p", "scale": 0.08, "decay": 0.8, "threshold": 1.0, "reset": 0.0, "stimulus_duration": 3, "transmitter_model": "unsigned"},
        "world_steps": WORLD_STEPS,
        "neural_steps_per_world_step": NEURAL_STEPS_PER_WORLD_STEP,
        "episodes": episodes,
        "repeated_left_episode_reproducible": reproducible,
        "repeat_left": repeated,
        "python": platform.python_version(),
        "platform": platform.platform(),
    }
    result_dir = ROOT / "experiments" / "phase3" / "results"
    figure_dir = ROOT / "experiments" / "phase3" / "figures"
    result_dir.mkdir(parents=True, exist_ok=True)
    figure_dir.mkdir(parents=True, exist_ok=True)
    output = result_dir / "closed_loop_results.json"
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    create_svg(figure_dir / "closed_loop_trajectories.svg", episodes)
    print(json.dumps({"reproducible": reproducible, "episodes": [{"name": e["name"], "actions": e["actions"], "closed_loop_steps_per_second": e["closed_loop_steps_per_second"], "neural_steps_per_second": e["neural_steps_per_second"], "peak_rss_bytes": e["peak_rss_bytes"]} for e in episodes]}, indent=2))


if __name__ == "__main__":
    main()
