#!/usr/bin/env python3
"""Render the Phase 3.5 evidence bundle as publication-readable figures."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "experiments" / "phase35" / "results"
FIGURES = ROOT / "docs" / "figures"
SECTORS = ("far_left", "left", "center", "right", "far_right")
COLORS = ("#4361ee", "#4895ef", "#2a9d8f", "#f4a261", "#e63946")


def load(name: str) -> dict:
    return json.loads((RESULTS / name).read_text(encoding="utf-8"))


def save(fig: plt.Figure, stem: str) -> None:
    fig.tight_layout()
    for suffix in ("png", "svg"):
        fig.savefig(FIGURES / f"{stem}.{suffix}", dpi=180, bbox_inches="tight")
    plt.close(fig)


def selected_result(model: dict) -> dict:
    selected = model["selected_pass"]
    return next(item for item in model["results"] if item["config"] == selected["config"])


def plot_selected_dynamics(model: dict) -> None:
    result = selected_result(model)
    fig, ax = plt.subplots(figsize=(9, 4.8))
    for sector, color in zip(SECTORS, COLORS, strict=True):
        condition = next(item for item in result["conditions"] if item["condition"] == sector)
        ax.plot(range(1, len(condition["global_active_by_step"]) + 1), condition["global_active_by_step"], marker="o", markersize=3, color=color, label=sector.replace("_", " "))
    ax.axhline(139_255 * 0.10, color="#555", linestyle="--", linewidth=1, label="10% stability ceiling")
    ax.set(title="Selected bounded-rate configuration stays sparse", xlabel="Simulation step", ylabel="Neurons with activity ≥ 0.01")
    ax.legend(ncol=3, frameon=False)
    ax.grid(alpha=0.2)
    save(fig, "phase35_selected_dynamics")


def plot_readout_discrimination(model: dict) -> None:
    result = selected_result(model)
    chosen = [next(item for item in result["conditions"] if item["condition"] == sector) for sector in ("left", "center", "right")]
    readouts = ("optic", "visual_projection", "descending")
    values = np.array([[condition["readouts"][name]["active_cells"] for condition in chosen] for name in readouts])
    x = np.arange(len(readouts))
    width = 0.24
    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    for offset, sector, color in zip((-width, 0, width), ("left", "center", "right"), COLORS[1:4], strict=True):
        ax.bar(x + offset, values[:, ("left", "center", "right").index(sector)], width, label=sector, color=color)
    ax.axhline(5, color="#555", linestyle="--", linewidth=1, label="minimum active-cell criterion")
    ax.set(title="Selected dynamics reach visual-projection cells; descending stays silent", ylabel="Active readout cells", xticks=x, xticklabels=("optic", "visual projection", "descending"))
    ax.legend(frameon=False)
    ax.grid(axis="y", alpha=0.2)
    save(fig, "phase35_readout_discrimination")


def plot_path_convergence(paths: dict) -> None:
    hops = np.arange(1, 7)
    curves = np.array([[entry[f"reachable_jaccard_through_hop_{hop}"] for hop in hops] for entry in paths["structural_convergence"].values()])
    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    for curve in curves:
        ax.plot(hops, curve, color="#90caf9", alpha=0.38, linewidth=1)
    ax.plot(hops, curves.mean(axis=0), color="#0d47a1", marker="o", linewidth=2.5, label="mean across 10 sector pairs")
    ax.fill_between(hops, curves.min(axis=0), curves.max(axis=0), color="#2196f3", alpha=0.12, label="pairwise range")
    ax.set(title="Structural reachability converges after three hops", xlabel="Maximum directed hops", ylabel="Jaccard overlap of reachable neurons", xticks=hops, ylim=(-0.02, 1.03))
    ax.legend(frameon=False)
    ax.grid(alpha=0.2)
    save(fig, "phase35_path_convergence")


def plot_performance(profile: dict) -> None:
    bench = profile["execution_benchmark"]
    labels = ("Sequential", "2 threads", "4 threads", "Batched SpMM")
    times = (bench["sequential"]["wall_seconds"], bench["threads"]["2"]["wall_seconds"], bench["threads"]["4"]["wall_seconds"], bench["batched"]["wall_seconds"])
    fig, ax = plt.subplots(figsize=(8, 4.8))
    bars = ax.bar(labels, times, color=("#6c757d", "#90caf9", "#2a9d8f", "#e9c46a"))
    for bar, value in zip(bars, times, strict=True):
        ax.text(bar.get_x() + bar.get_width() / 2, value + 0.04, f"{value:.2f}s", ha="center", va="bottom")
    ax.set(title="Shared-memory condition parallelism is the fastest safe mode", ylabel="Wall time for 4 × 24 steps", ylim=(0, max(times) * 1.18))
    ax.grid(axis="y", alpha=0.2)
    save(fig, "phase35_performance")


def main() -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    model = load("model_investigation.json")
    plot_selected_dynamics(model)
    plot_readout_discrimination(model)
    plot_path_convergence(load("path_analysis.json"))
    plot_performance(load("performance_profile.json"))
    print(f"Wrote 8 figure files to {FIGURES}")


if __name__ == "__main__":
    main()
