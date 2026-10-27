#!/usr/bin/env python3
"""Deterministic Phase 3 open-loop discrimination and parameter search."""

from __future__ import annotations

import json
import math
import os
import platform
import sys
import time
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import numpy as np
import psutil

from interface import ActionDecoder, SensoryEncoder, select_phase3_populations
from simulator import ConnectomeGraph, LIFSimulator, NeuronConfig, WeightTransformConfig, build_source_gain, transform_weights


CONDITIONS: tuple[str | None, ...] = ("far_left", "left", "center", "right", "far_right", None)
CONFIGS = tuple(
    {"scale": scale, "decay": decay, "stimulus_duration": 1}
    for scale in (0.08, 0.10, 0.11, 0.12)
    for decay in (0.0, 0.3, 0.6)
) + tuple(
    {"scale": scale, "decay": decay, "stimulus_duration": 1}
    for scale in (0.12, 0.13, 0.14, 0.16)
    for decay in (0.7, 0.8, 0.85)
) + tuple(
    {"scale": scale, "decay": decay, "stimulus_duration": duration}
    for scale in (0.08, 0.10, 0.12)
    for decay in (0.3, 0.6, 0.8)
    for duration in (2, 3)
)
STEPS = 18
STIMULATED_NEURONS = 50
STIMULUS_AMPLITUDE = 1.05


def cosine_distance(a: np.ndarray, b: np.ndarray) -> float:
    denominator = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denominator == 0.0:
        return 0.0 if np.array_equal(a, b) else 1.0
    return 1.0 - float(np.dot(a, b) / denominator)


def run_condition(adjacency, config: dict[str, float], encoder: SensoryEncoder, decoder: ActionDecoder, condition: str | None) -> dict[str, object]:
    sim = LIFSimulator(adjacency, NeuronConfig(decay=config["decay"], threshold=1.0, reset_value=0.0))
    rows: list[dict[str, object]] = []
    vector = np.zeros((STEPS, decoder.all_indices.size), dtype=np.uint8)
    started = time.perf_counter()
    for step in range(STEPS):
        encoder_step = 0 if step < int(config["stimulus_duration"]) else 1
        current = encoder.encode(condition, step_in_observation=encoder_step, intensity=1.0)
        metrics = sim.step(current)
        response = decoder.observe(sim.spikes)
        vector[step] = sim.spikes[decoder.all_indices]
        rows.append(
            {
                "step": step,
                "active_neurons": metrics.active_neurons,
                "newly_active_neurons": metrics.newly_active_neurons,
                "output_total": response.total_activity,
                "output_left": response.left_activity,
                "output_right": response.right_activity,
                "output_other": response.center_activity,
                "peak_membrane_potential": metrics.peak_membrane_potential,
            }
        )
    elapsed = time.perf_counter() - started
    packed = np.packbits(vector, axis=None)
    return {
        "condition": condition or "not_visible",
        "timesteps": rows,
        "peak_global_active": max(row["active_neurons"] for row in rows),
        "cumulative_output_spikes": int(vector.sum()),
        "unique_active_outputs": int(np.count_nonzero(vector.any(axis=0))),
        "steps_per_second": STEPS / elapsed,
        "elapsed_seconds": elapsed,
        "response_vector": vector.sum(axis=0).astype(np.float32),
        "packed_temporal_response_hex": packed.tobytes().hex(),
    }


def create_svg(path: Path, best: dict[str, object]) -> None:
    width, height = 1000, 540
    margin_left, margin_top, plot_w, plot_h = 75, 60, 850, 380
    colors = {"far_left": "#6a3d9a", "left": "#1f78b4", "center": "#33a02c", "right": "#ff7f00", "far_right": "#e31a1c", "not_visible": "#666666"}
    maximum = max(1, max(max(row["output_total"] for row in run["timesteps"]) for run in best["conditions"]))
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">', '<rect width="100%" height="100%" fill="white"/>', '<text x="500" y="30" text-anchor="middle" font-family="sans-serif" font-size="20">Descending-population spikes by visual condition</text>', f'<line x1="{margin_left}" y1="{margin_top+plot_h}" x2="{margin_left+plot_w}" y2="{margin_top+plot_h}" stroke="black"/>', f'<line x1="{margin_left}" y1="{margin_top}" x2="{margin_left}" y2="{margin_top+plot_h}" stroke="black"/>']
    for run in best["conditions"]:
        points = []
        for row in run["timesteps"]:
            x = margin_left + plot_w * row["step"] / (STEPS - 1)
            y = margin_top + plot_h * (1 - row["output_total"] / maximum)
            points.append(f"{x:.1f},{y:.1f}")
        condition = run["condition"]
        parts.append(f'<polyline fill="none" stroke="{colors[condition]}" stroke-width="2" points="{" ".join(points)}"/>')
    for index, condition in enumerate(colors):
        x = 95 + index * 145
        parts.extend([f'<line x1="{x}" y1="495" x2="{x+25}" y2="495" stroke="{colors[condition]}" stroke-width="3"/>', f'<text x="{x+30}" y="500" font-family="sans-serif" font-size="13">{condition}</text>'])
    parts.extend([f'<text x="500" y="465" text-anchor="middle" font-family="sans-serif" font-size="14">Neural timestep</text>', f'<text x="18" y="250" transform="rotate(-90 18 250)" text-anchor="middle" font-family="sans-serif" font-size="14">Active descending neurons</text>', '</svg>'])
    path.write_text("\n".join(parts), encoding="utf-8")


def main() -> None:
    data_dir = ROOT / "data"
    result_dir = ROOT / "experiments" / "phase3" / "results"
    figure_dir = ROOT / "experiments" / "phase3" / "figures"
    result_dir.mkdir(parents=True, exist_ok=True)
    figure_dir.mkdir(parents=True, exist_ok=True)

    graph = ConnectomeGraph.load(data_dir / "processed")
    inputs, outputs = select_phase3_populations(data_dir)
    encoder = SensoryEncoder.from_population(inputs, graph.neuron_count, STIMULATED_NEURONS, STIMULUS_AMPLITUDE, 1)
    decoder = ActionDecoder(outputs)
    source_gain = build_source_gain(graph.nt_codes, mode="unsigned", unknown_policy="positive")
    process = psutil.Process(os.getpid())
    peak_rss = process.memory_info().rss
    all_results: list[dict[str, object]] = []

    for config in CONFIGS:
        adjacency = transform_weights(graph.adjacency_raw, WeightTransformConfig("log1p", config["scale"], 32.0))
        adjacency.data *= source_gain[adjacency.indices]
        condition_results = [run_condition(adjacency, config, encoder, decoder, condition) for condition in CONDITIONS]
        peak_rss = max(peak_rss, process.memory_info().rss)
        visible = condition_results[:-1]
        distances = [cosine_distance(a["response_vector"], b["response_vector"]) for a, b in combinations(visible, 2)]
        max_global = max(run["peak_global_active"] for run in condition_results)
        result = {
            "config": config,
            "conditions": condition_results,
            "max_global_active": max_global,
            "runaway": max_global > graph.neuron_count * 0.10,
            "mean_pairwise_cosine_distance_visible": float(np.mean(distances)),
            "min_pairwise_cosine_distance_visible": float(np.min(distances)),
            "conditions_with_output": sum(run["cumulative_output_spikes"] > 0 for run in visible),
            "unique_temporal_responses": len({run["packed_temporal_response_hex"] for run in condition_results}),
        }
        all_results.append(result)
        print(json.dumps({key: value for key, value in result.items() if key != "conditions"}))

    eligible = [r for r in all_results if not r["runaway"] and r["conditions_with_output"] > 0]
    best = max(eligible, key=lambda r: (r["unique_temporal_responses"], r["mean_pairwise_cosine_distance_visible"], r["conditions_with_output"])) if eligible else max(all_results, key=lambda r: (not r["runaway"], r["conditions_with_output"], r["max_global_active"], r["unique_temporal_responses"]))

    repeat_adjacency = transform_weights(graph.adjacency_raw, WeightTransformConfig("log1p", best["config"]["scale"], 32.0))
    repeated = run_condition(repeat_adjacency, best["config"], encoder, decoder, "left")
    original_left = next(run for run in best["conditions"] if run["condition"] == "left")
    deterministic_repeat = repeated["packed_temporal_response_hex"] == original_left["packed_temporal_response_hex"] and repeated["timesteps"] == original_left["timesteps"]

    for result in all_results:
        for run in result["conditions"]:
            run.pop("response_vector", None)
    repeated.pop("response_vector", None)
    payload = {
        "objective": "open-loop visual-condition discrimination at metadata-selected descending neurons",
        "constants": {"steps": STEPS, "stimulated_neurons_per_visible_condition": STIMULATED_NEURONS, "stimulus_amplitude": STIMULUS_AMPLITUDE, "weight_transform": "log1p", "threshold": 1.0, "reset": 0.0, "transmitter_model": "unsigned", "seed": 0},
        "population_counts": {"inputs": len(inputs), "outputs": len(outputs)},
        "sector_root_ids": {sector: [int(graph.root_ids[i]) for i in indices] for sector, indices in encoder.sector_indices.items()},
        "configurations": all_results,
        "best_config": best["config"],
        "best_config_summary": {key: value for key, value in best.items() if key not in {"conditions", "config"}},
        "deterministic_repeat_left": deterministic_repeat,
        "repeat_left": repeated,
        "peak_rss_bytes": peak_rss,
        "python": platform.python_version(),
        "platform": platform.platform(),
    }
    output = result_dir / "open_loop_results.json"
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    create_svg(figure_dir / "open_loop_output_activity.svg", best)
    print(f"wrote {output}")
    print(f"best={best['config']} deterministic_repeat={deterministic_repeat} peak_rss={peak_rss}")


if __name__ == "__main__":
    main()
