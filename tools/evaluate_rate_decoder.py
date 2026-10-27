#!/usr/bin/env python3
"""Evaluate the Phase 3.5 readout-to-action interface without Minecraft."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from interface import RateActionDecoder, SensoryEncoder, select_phase3_populations, select_superclass_population
from simulator import BoundedRateSimulator, ConnectomeGraph, RateConfig, normalize_incoming


def main() -> None:
    data_dir = ROOT / "data"
    graph = ConnectomeGraph.load(data_dir / "processed")
    inputs, _ = select_phase3_populations(data_dir)
    readout_records = select_superclass_population(data_dir, "visual_projection")
    encoder = SensoryEncoder.from_population(inputs, graph.neuron_count, 50, 1.05, 3)
    adjacency = normalize_incoming(graph.adjacency_raw, minimum=5, gain=0.8)
    decoder = RateActionDecoder(readout_records, minimum_total_activity=0.01, turn_margin=0.01, activity_floor=0.01)
    outcomes = []
    for sector in (*encoder.sector_indices, None):
        simulator = BoundedRateSimulator(adjacency, RateConfig(decay=0.0, activity_floor=1e-7))
        integrated = np.zeros(graph.neuron_count, dtype=np.float32)
        active_by_step = []
        for step in range(18):
            activity = simulator.step(encoder.encode(sector, 0 if step < 3 else 1))
            integrated += activity
            active_by_step.append(int(np.count_nonzero(activity >= 0.01)))
        response = decoder.observe(integrated)
        outcomes.append(
            {
                "condition": sector or "not_visible",
                "response": {
                    "left_activity": response.left_activity,
                    "right_activity": response.right_activity,
                    "center_activity": response.center_activity,
                    "total_activity": response.total_activity,
                    "active_cells": response.active_cells,
                },
                "action": decoder.decode(response),
                "global_active_by_step": active_by_step,
            }
        )
    payload = {
        "model": {"type": "bounded_rate", "minimum_synapses": 5, "gain": 0.8, "decay": 0.0, "steps": 18, "pulse_steps": 3},
        "decoder": {"readout_superclass": "visual_projection", "minimum_total_activity": 0.01, "turn_margin": 0.01, "activity_floor": 0.01},
        "information_boundary": "decoder receives only integrated visual_projection activity grouped by annotation side; it does not receive condition labels or coordinates",
        "outcomes": outcomes,
    }
    output = ROOT / "experiments" / "phase35" / "results" / "rate_decoder_evaluation.json"
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
