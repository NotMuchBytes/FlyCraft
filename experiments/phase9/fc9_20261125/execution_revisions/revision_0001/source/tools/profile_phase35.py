#!/usr/bin/env python3
"""Profile Phase 3 sparse propagation and safe experiment-level concurrency."""

from __future__ import annotations

import importlib.util
import json
import os
import platform
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
import psutil

from interface import SensoryEncoder, select_phase3_populations
from simulator import BatchedLIFSimulator, ConnectomeGraph, LIFSimulator, NeuronConfig, WeightTransformConfig, transform_weights


STEPS = 24
CONDITIONS = ("far_left", "left", "center", "right")


def profile_components(adjacency, current: np.ndarray) -> dict[str, float]:
    n = adjacency.shape[0]
    voltage = np.zeros(n, dtype=np.float32)
    spikes = np.zeros(n, dtype=np.bool_)
    gain = np.ones(n, dtype=np.float32)
    timings = {name: 0.0 for name in ("copy", "decay", "prepare_presynaptic", "sparse_matvec", "external_add", "threshold_reset", "metrics")}
    for step in range(STEPS + 5):
        record = step >= 5
        started = time.perf_counter(); previous = spikes.copy(); elapsed = time.perf_counter() - started
        if record: timings["copy"] += elapsed
        started = time.perf_counter(); voltage *= np.float32(0.8); elapsed = time.perf_counter() - started
        if record: timings["decay"] += elapsed
        started = time.perf_counter(); presynaptic = spikes.astype(np.float32); presynaptic *= gain; elapsed = time.perf_counter() - started
        if record: timings["prepare_presynaptic"] += elapsed
        started = time.perf_counter(); voltage += adjacency @ presynaptic; elapsed = time.perf_counter() - started
        if record: timings["sparse_matvec"] += elapsed
        started = time.perf_counter(); voltage += current if step < 3 else 0.0; elapsed = time.perf_counter() - started
        if record: timings["external_add"] += elapsed
        started = time.perf_counter(); spikes = voltage >= np.float32(1.0); voltage[spikes] = 0.0; elapsed = time.perf_counter() - started
        if record: timings["threshold_reset"] += elapsed
        started = time.perf_counter(); _ = (np.count_nonzero(spikes), np.count_nonzero(spikes & ~previous), float(np.max(voltage))); elapsed = time.perf_counter() - started
        if record: timings["metrics"] += elapsed
    total = sum(timings.values())
    return {**{key + "_seconds": value for key, value in timings.items()}, "total_seconds": total, "sparse_fraction": timings["sparse_matvec"] / total}


def run_single(adjacency, currents: list[np.ndarray], condition_index: int) -> tuple[list[int], float]:
    sim = LIFSimulator(adjacency, NeuronConfig(decay=0.8, threshold=1.0))
    counts = []
    started = time.perf_counter()
    for step in range(STEPS):
        counts.append(sim.step(currents[condition_index] if step < 3 else None).active_neurons)
    return counts, time.perf_counter() - started


def benchmark(adjacency, currents: list[np.ndarray]) -> dict[str, object]:
    process = psutil.Process(os.getpid())
    cpu_before = process.cpu_times()
    started = time.perf_counter()
    sequential = [run_single(adjacency, currents, i) for i in range(len(currents))]
    sequential_wall = time.perf_counter() - started
    cpu_after = process.cpu_times()
    sequential_cpu = (cpu_after.user + cpu_after.system) - (cpu_before.user + cpu_before.system)

    thread_results = {}
    for workers in (2, 4):
        cpu_before = process.cpu_times(); started = time.perf_counter()
        with ThreadPoolExecutor(max_workers=workers) as executor:
            results = list(executor.map(lambda i: run_single(adjacency, currents, i), range(len(currents))))
        wall = time.perf_counter() - started; cpu_after = process.cpu_times()
        thread_results[str(workers)] = {
            "wall_seconds": wall,
            "process_cpu_seconds": (cpu_after.user + cpu_after.system) - (cpu_before.user + cpu_before.system),
            "speedup_vs_sequential": sequential_wall / wall,
            "equivalent": [item[0] for item in results] == [item[0] for item in sequential],
        }

    batched = BatchedLIFSimulator(adjacency, NeuronConfig(decay=0.8, threshold=1.0), len(currents))
    current_matrix = np.column_stack(currents)
    batched_counts = []
    cpu_before = process.cpu_times(); started = time.perf_counter()
    for step in range(STEPS):
        batched_counts.append(batched.step(current_matrix if step < 3 else None).tolist())
    batched_wall = time.perf_counter() - started; cpu_after = process.cpu_times()
    batched_by_condition = [list(values) for values in zip(*batched_counts)]
    return {
        "sequential": {
            "wall_seconds": sequential_wall,
            "process_cpu_seconds": sequential_cpu,
            "steps_per_second": STEPS * len(currents) / sequential_wall,
            "cpu_one_core_basis_percent": 100 * sequential_cpu / sequential_wall,
        },
        "threads": thread_results,
        "batched": {
            "wall_seconds": batched_wall,
            "process_cpu_seconds": (cpu_after.user + cpu_after.system) - (cpu_before.user + cpu_before.system),
            "steps_per_second": STEPS * len(currents) / batched_wall,
            "speedup_vs_sequential": sequential_wall / batched_wall,
            "equivalent": batched_by_condition == [item[0] for item in sequential],
            "state_memory_bytes": batched.state_memory_bytes,
        },
    }


def main() -> None:
    graph = ConnectomeGraph.load(ROOT / "data" / "processed")
    inputs, _ = select_phase3_populations(ROOT / "data")
    encoder = SensoryEncoder.from_population(inputs, graph.neuron_count, 50, 1.05, 3)
    adjacency = transform_weights(graph.adjacency_raw, WeightTransformConfig("log1p", 0.08, 32.0))
    currents = [encoder.encode(condition, 0) for condition in CONDITIONS]
    process = psutil.Process(os.getpid())
    hardware = {
        "cpu_name": platform.processor(),
        "physical_cores": psutil.cpu_count(logical=False),
        "logical_cores": psutil.cpu_count(logical=True),
        "total_ram_bytes": psutil.virtual_memory().total,
        "available_ram_bytes_at_start": psutil.virtual_memory().available,
        "openblas_max_threads_from_numpy_build": 24,
        "thread_environment": {name: os.environ.get(name) for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")},
        "gpu_compute_packages": {name: importlib.util.find_spec(name) is not None for name in ("cupy", "torch", "pyopencl", "onnxruntime")},
        "nvidia_smi_available": False,
        "integrated_gpu_reported_in_cpu_name": "Radeon 740M Graphics",
    }
    payload = {
        "hardware": hardware,
        "component_profile": profile_components(adjacency, currents[0]),
        "execution_benchmark": benchmark(adjacency, currents),
        "peak_rss_bytes": process.memory_info().rss,
        "matrix_bytes": adjacency.data.nbytes + adjacency.indices.nbytes + adjacency.indptr.nbytes,
        "steps_per_condition": STEPS,
        "conditions": list(CONDITIONS),
    }
    output = ROOT / "experiments" / "phase35" / "results" / "performance_profile.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
