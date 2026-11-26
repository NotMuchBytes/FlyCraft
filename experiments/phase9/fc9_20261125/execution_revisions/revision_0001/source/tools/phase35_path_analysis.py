#!/usr/bin/env python3
"""Efficient structural path analysis for the Phase 3.5 evidence gate."""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
from scipy import sparse

from interface import SensoryEncoder, select_phase3_populations
from simulator import ConnectomeGraph


def multisource_distances(incoming: sparse.csr_matrix, sources: np.ndarray) -> np.ndarray:
    """Exact unweighted directed distances via sparse boolean frontiers."""
    n = incoming.shape[0]
    distances = np.full(n, -1, dtype=np.int16)
    distances[sources] = 0
    frontier = np.zeros(n, dtype=np.bool_)
    frontier[sources] = True
    hop = 0
    while np.any(frontier):
        hop += 1
        reached = np.asarray(incoming @ frontier).ravel().astype(np.bool_, copy=False)
        reached &= distances < 0
        if not np.any(reached):
            break
        distances[reached] = hop
        frontier = reached
    return distances


def distribution(values: np.ndarray) -> dict[str, int]:
    counts = Counter(int(v) for v in values if v >= 0)
    return {str(key): counts[key] for key in sorted(counts)}


def jaccard(a: np.ndarray, b: np.ndarray) -> float:
    intersection = np.count_nonzero(a & b)
    union = np.count_nonzero(a | b)
    return float(intersection / union) if union else 1.0


def main() -> None:
    data_dir = ROOT / "data"
    graph = ConnectomeGraph.load(data_dir / "processed")
    inputs, outputs = select_phase3_populations(data_dir)
    encoder = SensoryEncoder.from_population(inputs, graph.neuron_count, neurons_per_sector=50)
    incoming_structure = graph.adjacency_raw.astype(np.bool_)
    outgoing = graph.adjacency_raw.transpose().tocsr()
    output_indices = np.array([record.dense_index for record in outputs], dtype=np.int32)

    # Actual annotation-backed readouts, not name guesses.
    import csv, gzip
    with gzip.open(data_dir / "classification.csv.gz", "rt", encoding="utf-8-sig", newline="") as handle:
        classification = {int(row["root_id"]): row for row in csv.DictReader(handle)}
    root_to_dense = {int(root): index for index, root in enumerate(graph.root_ids)}
    readouts: dict[str, np.ndarray] = {}
    for name in ("optic", "visual_projection", "descending"):
        readouts[name] = np.array(
            [root_to_dense[root] for root, row in classification.items() if row["super_class"] == name],
            dtype=np.int32,
        )

    out_degree = np.diff(outgoing.indptr)
    out_synapses = np.asarray(outgoing.sum(axis=1)).ravel()
    all_input_indices = np.array([record.dense_index for record in inputs], dtype=np.int32)
    cohort_results: dict[str, object] = {}
    distances_by_sector: dict[str, np.ndarray] = {}
    reached_by_hop: dict[str, dict[int, np.ndarray]] = {}

    for sector, sources in encoder.sector_indices.items():
        distances = multisource_distances(incoming_structure, sources.astype(np.int32))
        distances_by_sector[sector] = distances
        output_distances = distances[output_indices]
        readout_stats = {}
        for name, indices in readouts.items():
            values = distances[indices]
            reachable = values >= 0
            readout_stats[name] = {
                "population": int(indices.size),
                "reachable": int(np.count_nonzero(reachable)),
                "minimum_hops": int(values[reachable].min()) if np.any(reachable) else None,
                "maximum_hops": int(values[reachable].max()) if np.any(reachable) else None,
                "shortest_path_distribution": distribution(values),
            }
        hop_counts = distribution(distances)
        reached_by_hop[sector] = {hop: (distances >= 0) & (distances <= hop) for hop in range(1, 7)}
        cohort_results[sector] = {
            "source_count": int(sources.size),
            "source_root_ids": [int(graph.root_ids[index]) for index in sources],
            "source_out_degree": {
                "minimum": int(out_degree[sources].min()),
                "median": float(np.median(out_degree[sources])),
                "maximum": int(out_degree[sources].max()),
                "mean": float(np.mean(out_degree[sources])),
            },
            "source_out_synapses": {
                "minimum": int(out_synapses[sources].min()),
                "median": float(np.median(out_synapses[sources])),
                "maximum": int(out_synapses[sources].max()),
                "mean": float(np.mean(out_synapses[sources])),
            },
            "reachable_all_neurons": int(np.count_nonzero(distances >= 0)),
            "all_neuron_hop_distribution": hop_counts,
            "readouts": readout_stats,
        }

    convergence = {}
    sectors = list(encoder.sector_indices)
    for i, first in enumerate(sectors):
        for second in sectors[i + 1 :]:
            key = f"{first}__{second}"
            convergence[key] = {
                f"reachable_jaccard_through_hop_{hop}": jaccard(reached_by_hop[first][hop], reached_by_hop[second][hop])
                for hop in range(1, 7)
            }
            first_outputs = distances_by_sector[first][output_indices] >= 0
            second_outputs = distances_by_sector[second][output_indices] >= 0
            convergence[key]["descending_reachable_jaccard"] = jaccard(first_outputs, second_outputs)

    population_degree = out_degree[all_input_indices]
    population_synapses = out_synapses[all_input_indices]
    payload = {
        "graph": {"neurons": graph.neuron_count, "directed_edges": graph.edge_count},
        "population_counts": {name: int(indices.size) for name, indices in readouts.items()},
        "all_photoreceptor_out_degree_percentiles": {
            str(p): float(np.percentile(population_degree, p)) for p in (0, 10, 25, 50, 75, 90, 100)
        },
        "all_photoreceptor_out_synapse_percentiles": {
            str(p): float(np.percentile(population_synapses, p)) for p in (0, 10, 25, 50, 75, 90, 100)
        },
        "cohorts": cohort_results,
        "structural_convergence": convergence,
    }
    output = ROOT / "experiments" / "phase35" / "results" / "path_analysis.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({
        "output": str(output),
        "photoreceptor_degree_median": payload["all_photoreceptor_out_degree_percentiles"]["50"],
        "cohorts": {
            name: {
                "reachable": value["reachable_all_neurons"],
                "descending": value["readouts"]["descending"],
                "visual_projection": value["readouts"]["visual_projection"],
            }
            for name, value in cohort_results.items()
        },
    }, indent=2))


if __name__ == "__main__":
    main()
