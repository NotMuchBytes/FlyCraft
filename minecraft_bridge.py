#!/usr/bin/env python3
"""Local newline-JSON bridge between Minecraft and the FlyCraft simulator."""

from __future__ import annotations

import argparse
import gc
import json
import socketserver
import sys
import threading
import time
from dataclasses import asdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from interface import RateActionDecoder, SensoryEncoder, select_phase3_populations, select_superclass_population
from learning import LinearSoftmaxPolicy
from simulator import BoundedRateSimulator, ConnectomeGraph, RateConfig, normalize_incoming


class NeuralController:
    """Thread-safe fixed-window Phase 3.5 neural controller."""

    def __init__(self, *, checkpoint: Path | None = None, untrained_policy: bool = False, policy_mode: str = "stochastic", seed: int = 42) -> None:
        data_dir = ROOT / "data"
        graph = ConnectomeGraph.load(data_dir / "processed")
        self.neuron_count = graph.neuron_count
        self.adjacency = normalize_incoming(graph.adjacency_raw, minimum=5, gain=0.8)
        # Inference uses the unchanged normalized matrix. Release its raw source
        # copy; diagnostics can still explicitly obtain the original full graph.
        self._graph_for_inspection = None
        del graph
        gc.collect()
        inputs, _ = select_phase3_populations(data_dir)
        readout = select_superclass_population(data_dir, "visual_projection")
        self.encoder = SensoryEncoder.from_population(inputs, self.neuron_count, 50, 1.05, 3)
        self.decoder = RateActionDecoder(readout, minimum_total_activity=0.01, turn_margin=0.01, activity_floor=0.01)
        self.policy = None
        self.policy_source = "phase4_engineering_decoder"
        if checkpoint is not None:
            self.policy, metadata = LinearSoftmaxPolicy.load(checkpoint)
            if self.policy.actions != ("NO_OP", "TURN_LEFT", "TURN_RIGHT", "FORWARD") or self.policy.weights.shape != (4, 4):
                raise ValueError("use --autonomy-checkpoint for a Phase 7 checkpoint")
            self.policy_source = f"trained_checkpoint:{checkpoint.name}:episodes={self.policy.episodes_trained}:seed={metadata['training_seed']}"
        elif untrained_policy:
            self.policy = LinearSoftmaxPolicy()
            self.policy_source = f"untrained_policy:seed={seed}"
        self.policy_mode = policy_mode
        self.rng = np.random.default_rng(seed)
        self.lock = threading.Lock()

    @property
    def graph(self):
        """Compatibility access to the preserved raw graph, loaded on demand."""
        if self._graph_for_inspection is None:
            self._graph_for_inspection = ConnectomeGraph.load(ROOT / "data/processed")
        return self._graph_for_inspection

    def evaluate(self, sector: str | None) -> dict[str, object]:
        started = time.perf_counter()
        with self.lock:
            features, response, peak_active = self.neural_observation(sector)
            probabilities = None
            if self.policy is None:
                action = self.decoder.decode(response)
            else:
                probabilities = self.policy.probabilities(features)
                if self.policy_mode == "greedy":
                    action = self.policy.greedy(features)
                else:
                    _, action, probabilities = self.policy.sample(features, self.rng)
        return {
            "action": action,
            "readout": asdict(response),
            "policy_source": self.policy_source,
            "action_probabilities": None if probabilities is None else probabilities.tolist(),
            "peak_global_active": peak_active,
            "neural_steps": 18,
            "latency_ms": (time.perf_counter() - started) * 1000.0,
        }

    def neural_observation(self, sector: str | None) -> tuple[np.ndarray, object, int]:
        """Existing full-network window, shared by legacy and autonomous control."""
        if sector == "not_visible":
            sector = None
        if sector is not None and sector not in self.encoder.sector_indices:
            raise ValueError(f"invalid sector: {sector}")
        simulator = BoundedRateSimulator(self.adjacency, RateConfig(decay=0.0, activity_floor=1e-7))
        integrated = np.zeros(self.neuron_count, dtype=np.float32)
        peak_active = 0
        for step in range(18):
            activity = simulator.step(self.encoder.encode(sector, 0 if step < 3 else 1))
            integrated += activity
            peak_active = max(peak_active, int(np.count_nonzero(activity >= 0.01)))
        response = self.decoder.observe(integrated)
        features = np.array([1.0, response.left_activity / 50.0, response.right_activity / 50.0, response.total_activity / 50.0])
        return features, response, peak_active


class BridgeServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, address: tuple[str, int], controller: NeuralController, log_path: Path):
        super().__init__(address, BridgeHandler)
        self.controller = controller
        self.log_path = log_path
        self.log_lock = threading.Lock()
        self.log_handle = log_path.open("a", encoding="utf-8")

    def write_log(self, event: dict[str, object]) -> None:
        event = {"timestamp_unix": time.time(), **event}
        with self.log_lock:
            self.log_handle.write(json.dumps(event, separators=(",", ":")) + "\n")
            self.log_handle.flush()

    def server_close(self) -> None:
        super().server_close()
        if hasattr(self, "log_handle"):
            with self.log_lock:
                self.log_handle.close()


class BridgeHandler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        line = self.rfile.readline(16_384)
        try:
            request = json.loads(line)
            tick_id = int(request["tick_id"])
            sector = request.get("sector")
            if hasattr(self.server.controller, "evaluate_request"):
                result = self.server.controller.evaluate_request(request)
            else:
                result = self.server.controller.evaluate(sector)
            response = {"status": "ok", "tick_id": tick_id, "sector": sector, **result}
        except Exception as error:
            response = {"status": "error", "error": f"{type(error).__name__}: {error}"}
        self.server.write_log({"remote": self.client_address[0], "request": line.decode("utf-8", errors="replace").strip(), "response": response})
        self.wfile.write((json.dumps(response, separators=(",", ":")) + "\n").encode("utf-8"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--checkpoint", type=Path)
    parser.add_argument("--autonomy-checkpoint", type=Path, help="Phase 7 navigation checkpoint; requires telemetry-enabled Fabric client")
    parser.add_argument("--phase8-checkpoint", type=Path, help="Phase 8 acknowledged survival interactions")
    parser.add_argument("--phase8-pitch-actions", action="store_true", help="Enable the expanded headless pitch readout")
    parser.add_argument("--terrain-actions", action="store_true", help="Versioned visible-terrain features and policy-selected jump-forward")
    parser.add_argument("--phase8-explore-forward", action="store_true",
                        help="Triple legal forward odds during target-absent resource search")
    parser.add_argument("--phase8-frozen-checkpoint", type=Path)
    parser.add_argument("--phase8-results", type=Path)
    parser.add_argument("--phase8-save-dir", type=Path)
    parser.add_argument("--phase8-control", type=Path, help="Current lifecycle and final own-inventory snapshot")
    parser.add_argument("--phase8-mining-checkpoint", type=Path, help="Save the first pending mining decision for a restart diagnostic")
    parser.add_argument("--goal", choices=("navigate_object",), default="navigate_object")
    parser.add_argument("--save-autonomy-state", type=Path, help="New checkpoint written when bounded live goal ends")
    parser.add_argument("--untrained-policy", action="store_true")
    parser.add_argument("--policy-mode", choices=("stochastic", "greedy"), default="stochastic")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--log", type=Path, help="JSONL request/response log (default: experiments/phase4/bridge_service.jsonl)")
    args = parser.parse_args()
    if sum((args.checkpoint is not None, args.autonomy_checkpoint is not None, args.phase8_checkpoint is not None, args.untrained_policy)) > 1:
        parser.error("checkpoint, autonomy-checkpoint, and untrained-policy are mutually exclusive")
    if args.save_autonomy_state and (not args.autonomy_checkpoint or args.save_autonomy_state.exists()):
        parser.error("save-autonomy-state requires autonomy mode and a new output path")
    if args.phase8_mining_checkpoint and (not args.phase8_checkpoint or args.phase8_mining_checkpoint.exists()):
        parser.error("phase8-mining-checkpoint requires a Phase 8 controller and a new output path")
    return args


def main() -> None:
    args = parse_args()
    log_path = args.log if args.log is not None else ROOT / "experiments" / "phase4" / "bridge_service.jsonl"
    if not log_path.is_absolute():
        log_path = ROOT / log_path
    log_path.parent.mkdir(parents=True, exist_ok=True)
    if args.phase8_checkpoint:
        if not args.phase8_results:
            raise SystemExit("--phase8-results is required")
        from autonomy.minecraft import LiveResourceController
        from learning import NeuralFeatureTable
        table = NeuralFeatureTable.from_phase35(ROOT / "experiments/phase35/results/rate_decoder_evaluation.json")
        controller = LiveResourceController(NeuralController(), table, args.phase8_checkpoint,
            frozen_checkpoint=args.phase8_frozen_checkpoint, result_log=args.phase8_results, checkpoint_dir=args.phase8_save_dir,
            control_file=args.phase8_control, mining_checkpoint=args.phase8_mining_checkpoint,
            pitch_actions=args.phase8_pitch_actions, explore_forward=args.phase8_explore_forward, terrain_actions=args.terrain_actions)
    elif args.autonomy_checkpoint:
        from autonomy.bridge import LiveNavigationController
        controller = LiveNavigationController(NeuralController(), args.autonomy_checkpoint, args.goal, args.save_autonomy_state)
    else:
        controller = NeuralController(checkpoint=args.checkpoint, untrained_policy=args.untrained_policy, policy_mode=args.policy_mode, seed=args.seed)
    with BridgeServer((args.host, args.port), controller, log_path) as server:
        print(json.dumps({"status": "ready", "host": args.host, "port": args.port, "pid": __import__("os").getpid(), "policy_source": controller.policy_source, "policy_mode": args.policy_mode}), flush=True)
        server.serve_forever()


if __name__ == "__main__":
    main()
