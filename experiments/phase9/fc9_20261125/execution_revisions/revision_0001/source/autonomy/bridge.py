"""Optional bounded live navigation over the original Fabric TCP protocol."""

import math
import threading
import time
from pathlib import Path

from learning import NeuralFeatureTable

from .agent import AutonomousAgent


class LiveNavigationController:
    def __init__(self, neural_controller, checkpoint: Path, objective: str = "navigate_object", save_path: Path | None = None):
        if objective != "navigate_object":
            raise ValueError("Fabric currently supports navigation goals only")
        table = NeuralFeatureTable.from_phase35(Path(__file__).resolve().parents[1] / "experiments/phase35/results/rate_decoder_evaluation.json")
        self.agent, _ = AutonomousAgent.load(checkpoint, table)
        if self.agent.session and not self.agent.session["done"]:
            raise ValueError("live controller needs an episode-boundary checkpoint")
        self.neural, self.objective, self.save_path = neural_controller, objective, save_path
        self.policy_source = "phase7_learned_readout:" + checkpoint.name
        self.lock = threading.Lock()
        self.world_id, self.last_tick = None, -1
        self.last_position, self.last_action = None, "NO_OP"
        self.saved = False
        self.started = 0.0

    def evaluate_request(self, request: dict) -> dict:
        started = time.perf_counter()
        with self.lock:
            tick = int(request["tick_id"])
            telemetry = request.get("telemetry")
            if not isinstance(telemetry, dict):
                raise ValueError("Phase 7 needs updated Fabric telemetry; legacy mode remains supported separately")
            world_id = "minecraft:" + str(telemetry["session_id"])
            position = telemetry["position"]
            if len(position) != 3 or not all(math.isfinite(float(value)) for value in position):
                raise ValueError("invalid live position")
            sector = request.get("sector")
            visible = sector not in (None, "not_visible")
            distance = float(telemetry["target_distance"]) if visible else None
            if visible and (not math.isfinite(distance) or distance < 0 or distance > 20):
                raise ValueError("invalid ray distance")
            if world_id == self.world_id and tick <= self.last_tick:
                raise ValueError("stale or duplicate observation tick")
            blocked = world_id == self.world_id and self.last_action == "FORWARD" and self.last_position is not None and math.hypot(
                position[0] - self.last_position[0], position[1] - self.last_position[1]) < 0.01
            angles = {"far_left": 40, "left": 20, "center": 0, "right": -20, "far_right": -40}
            observation = {"world_id": world_id, "position": position, "visible": visible, "sector": sector if visible else None,
                           # Block-face ray distance + half a block diagonal
                           # stays within the server's 1.6-block center radius.
                           "near": bool(visible and distance <= 0.85), "distance": distance,
                           "angle": math.radians(angles[sector]) if visible else None,
                           "target_id": "gold_marker", "inventory": {}, "produced": {},
                           "allowed_actions": ["NO_OP", "TURN_LEFT", "TURN_RIGHT", "FORWARD"],
                           "last_error": "blocked" if blocked else "", "resource_exhausted": False, "interrupted": False}
            if self.world_id != world_id:
                if self.agent.session and not self.agent.session["done"]:
                    self.agent._finish(False, "world_changed")
                self.agent.start(self.objective, observation, train=False)
                self.started = started
                self.world_id = world_id
                self.last_position, self.last_action = None, "NO_OP"
            elif self.agent.pending is not None:
                self.agent.observe(observation)
            self.last_tick = tick
            probabilities = None
            if self.agent.session["done"]:
                action, peak = "NO_OP", 0
            else:
                neural, _, peak = self.neural.neural_observation(sector)
                action = self.agent.choose_action(observation, neural=neural)
                if self.agent.pending:
                    probabilities = self.agent.pending[2].tolist()
            self.last_position, self.last_action = list(position), action
            if self.agent.session["done"] and self.agent.session["elapsed_seconds"] == 0:
                self.agent.session["elapsed_seconds"] = time.perf_counter() - self.started
            if self.agent.session["done"] and self.save_path is not None and not self.saved:
                self.agent.save(self.save_path)
                self.saved = True
            return {"action": action, "action_probabilities": probabilities, "policy_source": self.policy_source,
                    "autonomy_status": self.agent.session["termination"], "goal": self.objective,
                    "goal_actions": self.agent.session["actions"], "peak_global_active": peak,
                    "neural_steps": 0 if peak == 0 and self.agent.session["done"] else 18,
                    "latency_ms": (time.perf_counter() - started) * 1000,
                    "goal_result": self.agent.result() if self.agent.session["done"] else None}
