#!/usr/bin/env python3
"""Controlled full-connectome propagation and stability experiments."""

from __future__ import annotations

import csv
import gzip
import json
import math
import os
import platform
import sys
import threading
import time
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import matplotlib
import numpy as np
import psutil
import scipy

from simulator import (
    ConnectomeGraph,
    LIFSimulator,
    NeuronConfig,
    WeightTransformConfig,
    build_source_gain,
    transform_weights,
)
from simulator.graph import sparse_nbytes


PROCESSED = ROOT / "data" / "processed"
FIGURES = ROOT / "docs" / "figures"
EXPERIMENT_DIR = ROOT / "experiments" / "phase2"
VISUAL_FILE = ROOT / "data" / "visual_neuron_types.csv.gz"
SEED = 783
STEPS = 30
STIMULATED_COUNT = 50
STIMULUS_STRENGTH = 1.05


class PeakRSS:
    def __init__(self) -> None:
        self.process = psutil.Process()
        self.peak = self.process.memory_info().rss
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self.sample, daemon=True)

    def sample(self) -> None:
        while not self.stop.wait(0.02):
            self.peak = max(self.peak, self.process.memory_info().rss)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *_args):
        self.stop.set()
        self.thread.join()
        self.peak = max(self.peak, self.process.memory_info().rss)


def select_stimulation(graph: ConnectomeGraph) -> tuple[np.ndarray, list[int]]:
    candidates: list[int] = []
    with gzip.open(VISUAL_FILE, "rt", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["family"] == "Photo Receptors":
                candidates.append(int(row["root_id"]))
    candidates.sort()
    incoming = np.diff(graph.adjacency_raw.indptr)
    outgoing = np.bincount(graph.adjacency_raw.indices, minlength=graph.neuron_count)
    chosen_indices: list[int] = []
    chosen_root_ids: list[int] = []
    for root_id in candidates:
        index = graph.dense_index(root_id)
        if incoming[index] + outgoing[index] > 0:
            chosen_indices.append(index)
            chosen_root_ids.append(root_id)
        if len(chosen_indices) == STIMULATED_COUNT:
            break
    if len(chosen_indices) != STIMULATED_COUNT:
        raise RuntimeError("not enough connected Photo Receptor candidates")
    return np.asarray(chosen_indices, dtype=np.int32), chosen_root_ids


def run_config(
    graph: ConnectomeGraph,
    stimulated: np.ndarray,
    weight: WeightTransformConfig,
    neuron: NeuronConfig,
) -> dict[str, object]:
    with PeakRSS() as memory:
        init_started = time.perf_counter()
        adjacency = transform_weights(graph.adjacency_raw, weight)
        gains = build_source_gain(graph.nt_codes, mode="unsigned", unknown_policy="positive")
        sim = LIFSimulator(adjacency, neuron, gains)
        initialization_seconds = time.perf_counter() - init_started

        sim.reset()
        baseline = [asdict(sim.step()) for _ in range(5)]
        if any(row["active_neurons"] for row in baseline):
            raise RuntimeError("zero-input baseline was not silent")
        sim.reset()
        current = np.zeros(graph.neuron_count, dtype=np.float32)
        current[stimulated] = np.float32(STIMULUS_STRENGTH)
        metrics: list[dict[str, object]] = []
        cumulative = np.zeros(graph.neuron_count, dtype=np.bool_)
        wall_started = time.perf_counter()
        cpu_started = time.process_time()
        for step in range(STEPS):
            result = sim.step(current if step == 0 else None)
            cumulative |= sim.spikes
            row = asdict(result)
            row["cumulative_unique_active"] = int(np.count_nonzero(cumulative))
            metrics.append(row)
        wall_seconds = time.perf_counter() - wall_started
        cpu_seconds = time.process_time() - cpu_started
    active = [int(row["active_neurons"]) for row in metrics]
    nonzero_after_stimulus = [i for i, count in enumerate(active[1:], start=1) if count]
    peak_active = max(active)
    runaway = peak_active >= int(0.25 * graph.neuron_count)
    saturated_tail = all(count >= int(0.10 * graph.neuron_count) for count in active[-5:])
    return {
        "weight": weight.to_dict(),
        "neuron": neuron.to_dict(),
        "transmitter_mode": "unsigned",
        "unknown_transmitter_policy": "positive",
        "initialization_seconds": initialization_seconds,
        "adjacency_memory_bytes": sparse_nbytes(adjacency),
        "state_memory_bytes": sim.state_memory_bytes,
        "baseline": baseline,
        "timesteps": metrics,
        "wall_seconds": wall_seconds,
        "cpu_seconds": cpu_seconds,
        "steps_per_second": STEPS / wall_seconds,
        "mean_step_milliseconds": wall_seconds * 1000 / STEPS,
        "process_cpu_percent_one_core_basis": 100 * cpu_seconds / wall_seconds,
        "process_cpu_percent_total_machine_basis": 100 * cpu_seconds / wall_seconds / (os.cpu_count() or 1),
        "peak_process_rss_bytes": memory.peak,
        "peak_active_neurons": peak_active,
        "cumulative_unique_active": int(metrics[-1]["cumulative_unique_active"]),
        "last_nonzero_timestep": max(nonzero_after_stimulus) if nonzero_after_stimulus else 0,
        "died_after_stimulus": not nonzero_after_stimulus,
        "runaway_25_percent_peak": runaway,
        "saturated_last_five_steps": saturated_tail,
    }


def make_plot(results: list[dict[str, object]]) -> Path:
    FIGURES.mkdir(parents=True, exist_ok=True)
    width, height = 1100, 760
    left, right = 90, 1060
    panels = [(90, 335), (440, 685)]
    colors = ["#0072B2", "#E69F00", "#009E73", "#CC79A7", "#D55E00", "#56B4E9", "#000000"]
    active_max = max(row["active_neurons"] for result in results for row in result["timesteps"])
    potential_max = max(row["total_absolute_potential"] for result in results for row in result["timesteps"])

    def point(step: int, value: float, top: int, bottom: int, maximum: float) -> tuple[float, float]:
        x = left + step * (right - left) / (STEPS - 1)
        scaled = math.log10(value + 1.0) / max(math.log10(maximum + 1.0), 1e-9)
        y = bottom - scaled * (bottom - top)
        return x, y

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<style>text{font-family:Segoe UI,Arial,sans-serif;fill:#202124}.axis{stroke:#444;stroke-width:1}.grid{stroke:#ddd;stroke-width:1}.series{fill:none;stroke-width:2}</style>',
        '<text x="550" y="35" text-anchor="middle" font-size="22" font-weight="600">FAFB v783 structural propagation — 50 deterministic photoreceptor seeds</text>',
        '<text x="550" y="58" text-anchor="middle" font-size="13">Logarithmic y-axes; values are recorded simulation outputs</text>',
    ]
    labels = [("Active neurons", active_max), ("Total |membrane potential|", potential_max)]
    for panel_index, ((top, bottom), (label, maximum)) in enumerate(zip(panels, labels)):
        parts += [
            f'<line class="axis" x1="{left}" y1="{bottom}" x2="{right}" y2="{bottom}"/>',
            f'<line class="axis" x1="{left}" y1="{top}" x2="{left}" y2="{bottom}"/>',
            f'<text x="22" y="{(top+bottom)/2}" text-anchor="middle" font-size="14" transform="rotate(-90 22 {(top+bottom)/2})">{label} (log10)</text>',
        ]
        for fraction in (0.0, 0.25, 0.5, 0.75, 1.0):
            y = bottom - fraction * (bottom - top)
            value = 10 ** (fraction * math.log10(maximum + 1.0)) - 1.0
            parts.append(f'<line class="grid" x1="{left}" y1="{y:.2f}" x2="{right}" y2="{y:.2f}"/>')
            parts.append(f'<text x="{left-8}" y="{y+4:.2f}" text-anchor="end" font-size="11">{value:.0f}</text>')
        for result_index, result in enumerate(results):
            key = "active_neurons" if panel_index == 0 else "total_absolute_potential"
            points = " ".join(
                f"{x:.2f},{y:.2f}"
                for row in result["timesteps"]
                for x, y in [point(int(row["timestep"]), float(row[key]), top, bottom, maximum)]
            )
            parts.append(f'<polyline class="series" stroke="{colors[result_index]}" points="{points}"/>')
        if panel_index == 1:
            for step in (0, 5, 10, 15, 20, 25, 29):
                x, _ = point(step, 0, top, bottom, maximum)
                parts.append(f'<text x="{x:.2f}" y="{bottom+20}" text-anchor="middle" font-size="11">{step}</text>')
            parts.append(f'<text x="{(left+right)/2}" y="{bottom+45}" text-anchor="middle" font-size="14">Timestep</text>')
    legend_y = 720
    for index, result in enumerate(results):
        x = 70 + index * 145
        parts.append(f'<line x1="{x}" y1="{legend_y}" x2="{x+24}" y2="{legend_y}" stroke="{colors[index]}" stroke-width="3"/>')
        parts.append(f'<text x="{x+28}" y="{legend_y+4}" font-size="11">s={result["weight"]["scale"]}, d={result["neuron"]["decay"]}</text>')
    parts.append("</svg>")
    path = FIGURES / "phase2_activity_vs_timestep.svg"
    path.write_text("\n".join(parts), encoding="utf-8", newline="\n")
    return path


def write_report(payload: dict[str, object], plot_path: Path) -> None:
    build = payload["build"]
    lines = [
        "# FlyCraft Phase 2 Report", "",
        "## Result", "",
        "We built a simplified computational neural model using the structural connectivity of the FAFB fruit-fly connectome and demonstrated signal propagation through it. This is not a recreation of biological fly physiology, cognition, or consciousness.", "",
        "## Simulator architecture", "",
        "- Deterministic dense index: all metadata `root_id` values sorted ascending.",
        "- Population: all 139,255 metadata neurons; graph-absent neurons are explicit isolated nodes.",
        "- Sparse graph: SciPy CSR, rows=postsynaptic neurons and columns=presynaptic neurons.",
        "- The 22,285,323 neuropil-separated records were aggregated by directed pre/post pair using summed `syn_count`.",
        f"- Processed edges: **{build['unique_directed_pairs']:,}**; total raw weight: **{build['aggregate_syn_count']:,}**.",
        "- Default transmitter treatment: unsigned. Unknown/blank transmitter values use explicit positive gain +1; no connection is silently dropped.",
        "- Weight transforms implemented: raw, square root, log1p, clipped, and normalized/clipped.", "",
        "## Neuron update", "",
        "For synchronous timestep `t`, `V[t+1] = decay × V[t] + W × spikes[t] + external_current[t]`. Neurons spike where `V >= threshold`, then reset to `reset_value`. This is a dimensionless leaky-integrate-and-fire-like engineering abstraction.", "",
        "## Stimulation", "",
        f"- Random seed recorded: {payload['random_seed']} (selection itself is deterministic and uses no randomness).",
        f"- Candidate annotation: exact visual `family == Photo Receptors`.",
        f"- Selection rule: first {payload['stimulated_count']} ascending root IDs that have at least one graph edge.",
        f"- External current: {payload['stimulus_strength']} for timestep 0 only.",
        f"- Timesteps per configuration: {payload['steps']}.",
        "- A five-step zero-input baseline was silent for every configuration.", "",
        "## Stability experiments", "",
        "| Weight transform | Scale | Threshold | Decay | Peak active | Peak newly active | Unique active | Last active step | Runaway ≥25% | Saturated tail | ms/step | steps/s | CPU (one-core basis) | Peak RSS |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for result in payload["results"]:
        lines.append(
            f"| {result['weight']['name']} | {result['weight']['scale']} | {result['neuron']['threshold']} | {result['neuron']['decay']} | "
            f"{result['peak_active_neurons']:,} | {max(row['newly_active_neurons'] for row in result['timesteps']):,} | {result['cumulative_unique_active']:,} | {result['last_nonzero_timestep']} | "
            f"{result['runaway_25_percent_peak']} | {result['saturated_last_five_steps']} | "
            f"{result['mean_step_milliseconds']:.3f} | {result['steps_per_second']:.2f} | {result['process_cpu_percent_one_core_basis']:.1f}% | {result['peak_process_rss_bytes'] / 2**20:.2f} MiB |"
        )
    lines += ["", "Exact active-neuron counts by timestep:", ""]
    lines += ["| Scale | Decay | Counts for timesteps 0–29 |", "| ---: | ---: | --- |"]
    for result in payload["results"]:
        counts = ", ".join(str(row["active_neurons"]) for row in result["timesteps"])
        lines.append(f"| {result['weight']['scale']} | {result['neuron']['decay']} | {counts} |")
    lines += [
        "", "## Memory and initialization", "",
        f"- Saved compressed CSR file: {build['csr']['saved_bytes'] / 2**20:.2f} MiB.",
        f"- Raw CSR arrays in memory: {build['csr']['memory_bytes'] / 2**20:.2f} MiB.",
        f"- Graph preprocessing peak process RSS: {build['peak_process_rss_bytes'] / 2**20:.2f} MiB.",
        f"- Graph preprocessing time: {build['build_seconds']:.3f} seconds.",
    ]
    for result in payload["results"]:
        lines.append(
            f"- Scale {result['weight']['scale']}: transformed CSR {result['adjacency_memory_bytes'] / 2**20:.2f} MiB, "
            f"state arrays {result['state_memory_bytes'] / 2**20:.2f} MiB, initialization {result['initialization_seconds']:.3f} s."
        )
    lines += [
        "", "## Visualization", "",
        f"![Active neurons and total network activity](figures/{plot_path.name})", "",
        "The plot is generated from the recorded simulation metrics; it is not decorative or fabricated brain imagery.", "",
        "## Scientific assumptions and limitations", "",
        "- Structural synapse counts are not calibrated voltages or conductances.",
        "- Aggregating across neuropils discards where each synapse occurs, while preserving the total directed-pair count.",
        "- Unsigned propagation intentionally ignores receptor-specific sign. It is a structural propagation baseline, not a claim that all fly synapses excite.",
        "- The synchronous timestep, uniform decay/threshold/reset, one-step delay, and deterministic external current are engineering choices.",
        "- The unthresholded export contains one-synapse records that may include false positives; no biological-confidence filter was imposed in this lossless first build.",
        "- Cell Types and Classification exports remain unavailable, so descending/output neurons are not identified.",
        "- The available files do not explain why 139 metadata neurons have no graph representation.", "",
        "## Reproducibility", "",
        f"- Python {payload['versions']['python']}; NumPy {payload['versions']['numpy']}; SciPy {payload['versions']['scipy']}; Matplotlib {payload['versions']['matplotlib']}; psutil {payload['versions']['psutil']}.",
        "- Full configuration and all timestep metrics: `experiments/phase2/phase2_metrics.json`.",
        "- Processed graph build metadata includes source sizes and SHA-256 digests: `data/processed/build_metadata.json`.",
        "- Data semantics and official references: `docs/data_semantics.md`.", "",
        "## Failures encountered", "",
        "- The first three tested scales (0.01, 0.03, 0.10) produced only the externally driven timestep-0 spikes; this non-propagation result is retained.",
        "- Matplotlib's raster backend was blocked by Windows Application Control after the first simulation run. The plot was reimplemented as dependency-free SVG and the complete experiment rerun.",
        "Successful results above are from commands that completed against the real processed graph.", "",
        "## Phase boundary", "",
        "Phase 2 is complete. Work stops here pending explicit approval for Phase 3.", "",
        "No Minecraft, 2D agent, learning, training, movement decoding, tutorial system, or Fabric work was started.", "",
    ]
    (ROOT / "docs" / "phase2_report.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")


def append_log(payload: dict[str, object], plot_path: Path) -> None:
    path = ROOT / "DEVELOPMENT_LOG.md"
    text = path.read_text(encoding="utf-8")
    marker = "— Phase 2 final stability rerun"
    if marker in text:
        return
    results = payload["results"]
    lines = [
        f"\n## {time.strftime('%Y-%m-%dT%H:%M:%S%z')} {marker}", "",
        "**TASK**", "", "Build and test an efficient first structural-connectome simulator; no behavior, Minecraft, or learning.", "",
        "**WHAT WE TRIED**", "", "- Verified official data semantics; investigated graph-absent metadata neurons; built an all-neuron CSR graph; ran synthetic tests and seven unsigned propagation configurations.", "",
        "**RESULT**", "", f"- 139,255 neurons, 19,773,733 aggregated directed edges, total raw `syn_count` 76,944,499. Plot: `{plot_path.relative_to(ROOT)}`.",
    ]
    for r in results:
        lines.append(f"- log1p scale {r['weight']['scale']}, decay {r['neuron']['decay']}: peak {r['peak_active_neurons']:,}, unique {r['cumulative_unique_active']:,}, {r['steps_per_second']:.2f} steps/s.")
    lines += [
        "", "**ERRORS**", "", "- The first synthetic reset test used `decay=0` while expecting subthreshold accumulation. It failed correctly; the test was fixed to `decay=1` and then passed.",
        "- The first full experiment completed its numerical runs but Matplotlib's `_backend_agg` DLL was blocked by Windows Application Control. Plotting was replaced with dependency-free SVG and the experiment was rerun.", "",
        "**WHAT WORKED**", "", "- Synthetic propagation tests passed; graph counts matched Phase 1; zero-input baselines were silent; full-connectome sparse matvec propagation completed.", "",
        "**WHAT FAILED**", "", "- Reliable descending/output selection remains blocked by missing Cell Types and Classification exports.", "",
        "**ASSUMPTIONS**", "", "- All metadata neurons retained; neuropil rows summed per pair; unsigned transmitter model; dimensionless uniform LIF-like dynamics; log1p numerical weights.", "",
        "**PERFORMANCE**", "", f"- Graph build: {payload['build']['build_seconds']:.3f} s, peak RSS {payload['build']['peak_process_rss_bytes']/2**20:.2f} MiB. Simulation results are detailed in `docs/phase2_report.md`.", "",
        "**NEXT STEP**", "", "Stop at the Phase 2 boundary and await explicit approval. Do not start Minecraft, behavior, or learning.", "",
    ]
    path.write_text(text.rstrip() + "\n" + "\n".join(lines), encoding="utf-8", newline="\n")


def main() -> int:
    np.random.seed(SEED)
    EXPERIMENT_DIR.mkdir(parents=True, exist_ok=True)
    graph = ConnectomeGraph.load(PROCESSED)
    build = json.loads((PROCESSED / "build_metadata.json").read_text(encoding="utf-8"))
    stimulated, stimulated_root_ids = select_stimulation(graph)
    accumulating = NeuronConfig(decay=0.90, threshold=1.0, reset_value=0.0, refractory_steps=0)
    no_accumulation = NeuronConfig(decay=0.0, threshold=1.0, reset_value=0.0, refractory_steps=0)
    configs = [
        (WeightTransformConfig("log1p", 0.01, 32.0), accumulating),
        (WeightTransformConfig("log1p", 0.03, 32.0), accumulating),
        (WeightTransformConfig("log1p", 0.10, 32.0), accumulating),
        (WeightTransformConfig("log1p", 0.12, 32.0), no_accumulation),
        (WeightTransformConfig("log1p", 0.12, 32.0), accumulating),
        (WeightTransformConfig("log1p", 0.30, 32.0), accumulating),
        (WeightTransformConfig("log1p", 1.00, 32.0), accumulating),
    ]
    results = []
    for config, neuron in configs:
        print(f"running scale={config.scale}, decay={neuron.decay}...", flush=True)
        result = run_config(graph, stimulated, config, neuron)
        results.append(result)
        print(
            f"  peak={result['peak_active_neurons']:,} unique={result['cumulative_unique_active']:,} "
            f"speed={result['steps_per_second']:.2f} steps/s",
            flush=True,
        )
    payload = {
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "random_seed": SEED,
        "steps": STEPS,
        "stimulated_count": STIMULATED_COUNT,
        "stimulus_strength": STIMULUS_STRENGTH,
        "stimulation_rule": "first 50 ascending Photo Receptor root IDs with at least one graph edge",
        "stimulated_root_ids": stimulated_root_ids,
        "build": build,
        "versions": {
            "python": platform.python_version(), "numpy": np.__version__,
            "scipy": scipy.__version__, "matplotlib": matplotlib.__version__,
            "psutil": psutil.__version__,
        },
        "results": results,
    }
    metrics_path = EXPERIMENT_DIR / "phase2_metrics.json"
    metrics_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8", newline="\n")
    plot = make_plot(results)
    write_report(payload, plot)
    append_log(payload, plot)
    print(f"wrote {metrics_path}")
    print(f"wrote {plot}")
    print(f"wrote {ROOT / 'docs' / 'phase2_report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
