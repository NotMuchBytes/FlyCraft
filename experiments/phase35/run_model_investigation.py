#!/usr/bin/env python3
"""Bounded Phase 3.5 dynamics/readout investigation with explicit criteria."""

from __future__ import annotations

import csv
import gzip
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import numpy as np
import psutil

from interface import SensoryEncoder, select_phase3_populations
from simulator import (
    BoundedRateSimulator,
    ConnectomeGraph,
    LIFSimulator,
    NeuronConfig,
    RateConfig,
    WeightTransformConfig,
    filter_min_synapses,
    normalize_incoming,
    transform_weights,
)


CONDITIONS: tuple[str | None, ...] = ("far_left", "left", "center", "right", "far_right", None)
STEPS = 18
READOUT_CRITERIA = {
    "minimum_pairwise_cosine_distance_left_center_right": 0.10,
    "minimum_active_readout_cells_each": 5,
    "maximum_global_active_fraction": 0.10,
    "activity_threshold_rate_model": 0.01,
}
LIF_CONFIGS = [
    {"model": "lif", "minimum_synapses": minimum, "scale": scale, "decay": decay}
    for minimum in (2, 5)
    for scale in (0.08, 0.12, 0.16, 0.20)
    for decay in (0.5, 0.8)
]
RATE_CONFIGS = [
    {"model": "bounded_rate", "minimum_synapses": 5, "gain": gain, "decay": decay}
    for gain in (0.5, 0.8, 1.0)
    for decay in (0.0, 0.5)
]


def cosine_distance(a: np.ndarray, b: np.ndarray) -> float:
    denominator = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denominator == 0:
        return 0.0 if np.array_equal(a, b) else 1.0
    return 1.0 - float(np.dot(a, b) / denominator)


def make_readouts(graph: ConnectomeGraph, data_dir: Path, input_indices: set[int]) -> dict[str, np.ndarray]:
    root_to_dense = {int(root): index for index, root in enumerate(graph.root_ids)}
    with gzip.open(data_dir / "classification.csv.gz", "rt", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    result = {}
    for name in ("optic", "visual_projection", "descending"):
        indices = [root_to_dense[int(row["root_id"])] for row in rows if row["super_class"] == name]
        if name == "optic":
            indices = [index for index in indices if index not in input_indices]
        result[name] = np.array(indices, dtype=np.int32)
    return result


def run_lif(adjacency, config, encoder, readouts, condition):
    sim = LIFSimulator(adjacency, NeuronConfig(decay=config["decay"], threshold=1.0))
    temporal = {name: np.zeros((STEPS, indices.size), dtype=np.uint8) for name, indices in readouts.items()}
    global_counts = []
    started = time.perf_counter()
    for step in range(STEPS):
        current = encoder.encode(condition, 0 if step < 3 else 1)
        metrics = sim.step(current)
        global_counts.append(metrics.active_neurons)
        for name, indices in readouts.items():
            temporal[name][step] = sim.spikes[indices]
    return summarize_condition(condition, temporal, global_counts, time.perf_counter() - started, rate=False)


def run_rate(adjacency, config, encoder, readouts, condition):
    sim = BoundedRateSimulator(adjacency, RateConfig(decay=config["decay"], activity_floor=1e-7))
    temporal = {name: np.zeros((STEPS, indices.size), dtype=np.float32) for name, indices in readouts.items()}
    global_counts = []
    started = time.perf_counter()
    for step in range(STEPS):
        current = encoder.encode(condition, 0 if step < 3 else 1)
        activity = sim.step(current)
        global_counts.append(int(np.count_nonzero(activity >= READOUT_CRITERIA["activity_threshold_rate_model"])))
        for name, indices in readouts.items():
            temporal[name][step] = activity[indices]
    return summarize_condition(condition, temporal, global_counts, time.perf_counter() - started, rate=True)


def summarize_condition(condition, temporal, global_counts, elapsed, *, rate):
    readout_summary = {}
    threshold = READOUT_CRITERIA["activity_threshold_rate_model"] if rate else 0.5
    for name, values in temporal.items():
        response = values.sum(axis=0, dtype=np.float64).astype(np.float32)
        readout_summary[name] = {
            "total_activity": float(values.sum(dtype=np.float64)),
            "active_cells": int(np.count_nonzero(np.max(values, axis=0, initial=0) >= threshold)),
            "peak_timestep_activity": float(np.max(values.sum(axis=1, dtype=np.float64), initial=0)),
            "response_vector": response,
            "response_checksum": float(np.dot(response.astype(np.float64), np.arange(1, response.size + 1))),
        }
    return {
        "condition": condition or "not_visible",
        "peak_global_active": max(global_counts),
        "global_active_by_step": global_counts,
        "readouts": readout_summary,
        "elapsed_seconds": elapsed,
        "steps_per_second": STEPS / elapsed,
    }


def evaluate(config, conditions, neuron_count):
    stable = max(item["peak_global_active"] for item in conditions) < neuron_count * READOUT_CRITERIA["maximum_global_active_fraction"]
    propagated = max(item["peak_global_active"] for item in conditions[:-1]) > 50
    zero_silent = conditions[-1]["peak_global_active"] == 0
    readout_evaluation = {}
    # Gate explicitly targets left, center, right; far sectors remain reported.
    selected = [next(item for item in conditions if item["condition"] == name) for name in ("left", "center", "right")]
    for readout in ("optic", "visual_projection", "descending"):
        vectors = [item["readouts"][readout]["response_vector"] for item in selected]
        distances = [cosine_distance(a, b) for a, b in combinations(vectors, 2)]
        active_counts = [item["readouts"][readout]["active_cells"] for item in selected]
        passed = stable and propagated and zero_silent and min(active_counts) >= READOUT_CRITERIA["minimum_active_readout_cells_each"] and min(distances) >= READOUT_CRITERIA["minimum_pairwise_cosine_distance_left_center_right"]
        readout_evaluation[readout] = {
            "active_cells_left_center_right": active_counts,
            "pairwise_cosine_distances_left_center_right": distances,
            "minimum_pairwise_cosine_distance": min(distances),
            "passed": passed,
        }
    return {"config": config, "stable": stable, "propagated": propagated, "zero_input_silent": zero_silent, "readout_evaluation": readout_evaluation}


def serializable(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.integer, np.floating)):
        return value.item()
    raise TypeError(type(value).__name__)


def main() -> None:
    data_dir = ROOT / "data"
    graph = ConnectomeGraph.load(data_dir / "processed")
    inputs, _ = select_phase3_populations(data_dir)
    encoder = SensoryEncoder.from_population(inputs, graph.neuron_count, 50, 1.05, 3)
    input_indices = {record.dense_index for record in inputs}
    readouts = make_readouts(graph, data_dir, input_indices)
    process = psutil.Process(os.getpid())
    peak_rss = process.memory_info().rss
    results = []

    for config in LIF_CONFIGS + RATE_CONFIGS:
        if config["model"] == "lif":
            filtered = filter_min_synapses(graph.adjacency_raw, config["minimum_synapses"])
            adjacency = transform_weights(filtered, WeightTransformConfig("log1p", config["scale"], 32.0))
            runner = run_lif
        else:
            adjacency = normalize_incoming(graph.adjacency_raw, minimum=config["minimum_synapses"], gain=config["gain"])
            runner = run_rate
        with ThreadPoolExecutor(max_workers=4) as executor:
            conditions = list(executor.map(lambda condition: runner(adjacency, config, encoder, readouts, condition), CONDITIONS))
        evaluation = evaluate(config, conditions, graph.neuron_count)
        peak_rss = max(peak_rss, process.memory_info().rss)
        results.append({**evaluation, "conditions": conditions, "edge_count": int(adjacency.nnz)})
        print(json.dumps({**evaluation, "conditions": None}))

    passes = []
    priority = {"descending": 3, "visual_projection": 2, "optic": 1}
    for result in results:
        for readout, evaluation in result["readout_evaluation"].items():
            if evaluation["passed"]:
                passes.append((priority[readout], evaluation["minimum_pairwise_cosine_distance"], result, readout))
    selected = max(passes, key=lambda item: (item[0], item[1])) if passes else None
    repeat_match = None
    if selected:
        _, _, result, readout = selected
        config = result["config"]
        if config["model"] == "lif":
            adjacency = transform_weights(filter_min_synapses(graph.adjacency_raw, config["minimum_synapses"]), WeightTransformConfig("log1p", config["scale"], 32.0))
            repeat = run_lif(adjacency, config, encoder, readouts, "left")
        else:
            adjacency = normalize_incoming(graph.adjacency_raw, minimum=config["minimum_synapses"], gain=config["gain"])
            repeat = run_rate(adjacency, config, encoder, readouts, "left")
        original = next(item for item in result["conditions"] if item["condition"] == "left")
        repeat_match = all(
            np.array_equal(repeat["readouts"][name]["response_vector"], original["readouts"][name]["response_vector"])
            for name in readouts
        )

    for result in results:
        for condition in result["conditions"]:
            for summary in condition["readouts"].values():
                summary.pop("response_vector", None)

    payload = {
        "criteria": READOUT_CRITERIA,
        "readout_populations": {name: int(indices.size) for name, indices in readouts.items()},
        "configuration_count": len(results),
        "results": results,
        "selected_pass": None if selected is None else {"readout": selected[3], "config": selected[2]["config"], "evaluation": selected[2]["readout_evaluation"][selected[3]]},
        "selected_repeat_exact": repeat_match,
        "peak_rss_bytes": peak_rss,
        "workers": 4,
    }
    output = ROOT / "experiments" / "phase35" / "results" / "model_investigation.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, default=serializable), encoding="utf-8")
    print(json.dumps({"output": str(output), "selected_pass": payload["selected_pass"], "repeat_exact": repeat_match, "peak_rss_bytes": peak_rss}, indent=2))


if __name__ == "__main__":
    main()
