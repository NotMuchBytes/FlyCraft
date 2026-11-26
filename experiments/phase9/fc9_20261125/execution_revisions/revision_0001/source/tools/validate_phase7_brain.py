#!/usr/bin/env python3
"""Recompute every cached observation with the preserved full connectome."""

import argparse
import concurrent.futures
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from interface import RateActionDecoder, SensoryEncoder, select_phase3_populations, select_superclass_population
from learning import NeuralFeatureTable
from simulator import BoundedRateSimulator, ConnectomeGraph, RateConfig, normalize_incoming


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()
    if args.output.exists() or not 1 <= args.workers <= 4:
        parser.error("output must be new and workers must be between 1 and 4")
    started = time.perf_counter()
    graph_path = ROOT / "data/processed/connectome_raw_csr.npz"
    original_digest = hashlib.sha256(graph_path.read_bytes()).hexdigest()
    graph = ConnectomeGraph.load(ROOT / "data/processed")
    inputs, _ = select_phase3_populations(ROOT / "data")
    encoder = SensoryEncoder.from_population(inputs, graph.neuron_count, 50, 1.05, 3)
    decoder = RateActionDecoder(select_superclass_population(ROOT / "data", "visual_projection"))
    adjacency = normalize_incoming(graph.adjacency_raw, minimum=5, gain=0.8)
    table = NeuralFeatureTable.from_phase35(ROOT / "experiments/phase35/results/rate_decoder_evaluation.json")

    def compute(sector):
        sim = BoundedRateSimulator(adjacency, RateConfig(decay=0, activity_floor=1e-7))
        integrated = np.zeros(graph.neuron_count, dtype=np.float32)
        peak = 0
        for step in range(18):
            activity = sim.step(encoder.encode(None if sector == "not_visible" else sector, 0 if step < 3 else 1))
            integrated += activity
            peak = max(peak, int(np.count_nonzero(activity >= 0.01)))
        response = decoder.observe(integrated)
        features = np.array([1, response.left_activity / 50, response.right_activity / 50, response.total_activity / 50])
        return {"sector": sector, "features": features.tolist(), "exact_cache_match": bool(np.array_equal(features, table.for_sector(sector))),
                "peak_active": peak, "integrated_digest": hashlib.sha256(integrated.tobytes()).hexdigest()}

    sectors = sorted(table.features)
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        rows = list(pool.map(compute, sectors * 2))
    report = {"neuron_count": graph.neuron_count, "raw_edges": graph.edge_count, "retained_edges": adjacency.nnz,
              "graph_sha256": original_digest, "graph_unchanged": hashlib.sha256(graph_path.read_bytes()).hexdigest() == original_digest,
              "all_cache_matches_exact": all(row["exact_cache_match"] for row in rows),
              "full_state_repeats_exact": all(rows[i] == rows[i + len(sectors)] for i in range(len(sectors))),
              "workers": args.workers, "elapsed_seconds": time.perf_counter() - started, "windows": rows}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    print(json.dumps({key: value for key, value in report.items() if key != "windows"}, indent=2))
    if not all(report[key] for key in ("graph_unchanged", "all_cache_matches_exact", "full_state_repeats_exact")):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
