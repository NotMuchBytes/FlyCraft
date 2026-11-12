"""Acknowledged resource/crafting controller over the existing Phase 7 agent."""

import copy
import json
import math
import threading
import time
from pathlib import Path

import numpy as np

from learning import LinearSoftmaxPolicy
from .agent import AutonomousAgent
from .world import ACTIONS, CRAFT_ACTIONS, ITEMS


OBJECTIVES = {"one_log": "find_collect", "three_logs": "collect_multiple", "planks": "craft_simple",
              "sticks": "craft_sticks", "crafting_table": "craft_table", "wooden_pickaxe": "wooden_pickaxe",
              "pickaxe_transaction": "wooden_pickaxe", "camera_probe": "navigate_object"}
CONDITIONS = ("trained", "frozen", "uniform", "no_neural", "shuffled")


class ObservationError(ValueError):
    pass


class TransactionLedger:
    """Accept acknowledged, server-synchronized inventory; never predict success."""
    def __init__(self):
        self.previous = None
        self.produced = {key: 0 for key in ITEMS}
        self.mined_blocks = 0
        self.inventory_revision = -1
        self.terminal_tick = None

    def observe(self, telemetry: dict, ack: dict | None, *, terminal_tick=None) -> dict:
        if self.terminal_tick is not None:
            raise ObservationError("inventory_episode_already_sealed")
        if any(key in telemetry for key in ("world_seed", "layout_seed", "hidden_blocks", "oracle_target")):
            raise ObservationError("privileged_observation_field")
        if telemetry.get("game_mode") != "SURVIVAL":
            raise ObservationError("Phase 8 evidence requires survival mode")
        if not telemetry.get("inventory_consistent", False):
            raise ObservationError("inventory_inconsistent")
        revision = int(telemetry["inventory_revision"])
        if terminal_tick is not None and (not isinstance(terminal_tick, int) or terminal_tick < 0):
            raise ObservationError("invalid_terminal_tick")
        if terminal_tick is None and revision < self.inventory_revision:
            raise ObservationError("inventory_revision_regressed")
        inventory = {key: int(telemetry["inventory"].get(key, 0)) for key in ITEMS}
        if any(value < 0 or value > 2304 for value in inventory.values()):
            raise ObservationError("invalid_inventory_count")
        inventory["table_placed"] = int(bool(telemetry.get("station_visible", False)))
        if self.previous is not None:
            changed = inventory != self.previous
            if terminal_tick is None and changed and revision == self.inventory_revision and inventory | {"table_placed": 0} != self.previous | {"table_placed": 0}:
                raise ObservationError("inventory_changed_without_server_packet")
            for key in ITEMS:
                self.produced[key] += max(0, inventory[key] - self.previous[key])
        if ack and ack.get("action") == "COLLECT_LOG" and ack.get("block_changed", False):
            self.mined_blocks += 1
        self.previous = inventory
        if terminal_tick is None:
            self.inventory_revision = revision
        self.terminal_tick = terminal_tick
        return inventory

    def to_dict(self):
        return {"previous": self.previous, "produced": self.produced, "mined_blocks": self.mined_blocks, "terminal_tick": self.terminal_tick,
                "inventory_revision": self.inventory_revision}

    @classmethod
    def from_dict(cls, state):
        ledger = cls()
        for key, value in state.items():
            setattr(ledger, key, value)
        return ledger


class LiveResourceController:
    """One outstanding command, action acknowledgments, and bounded goal sessions.

    Experiment control supplies only episode identity, requested goal, policy
    condition and learning enablement. World/layout seeds never enter this API.
    """
    def __init__(self, neural, table, checkpoint: Path, *, frozen_checkpoint: Path | None = None,
                 result_log: Path, checkpoint_dir: Path | None = None, control_file: Path | None = None,
                 mining_checkpoint: Path | None = None, pitch_actions: bool = False):
        self.neural, self.table = neural, table
        self.agent, _ = AutonomousAgent.load(checkpoint, table)
        frozen_agent, _ = AutonomousAgent.load(frozen_checkpoint or checkpoint, table)
        self.pitch_actions = pitch_actions
        if pitch_actions:
            self.agent.enable_live_pitch()
            frozen_agent.enable_live_pitch()
        elif self.agent.policy.actions != ACTIONS or frozen_agent.policy.actions != ACTIONS:
            raise ValueError("pitch checkpoint requires the live pitch adapter")
        self.trained = self.agent.policy
        self.frozen = frozen_agent.policy
        self.uniform = LinearSoftmaxPolicy(self.trained.weights.shape[0], actions=self.trained.actions)
        self.policy_source = "phase8_existing_learned_readout"
        self.lock = threading.Lock()
        result_log.parent.mkdir(parents=True, exist_ok=True)
        self.results = result_log.open("x", encoding="utf-8")
        self.checkpoint_dir = checkpoint_dir
        self.mining_checkpoint = mining_checkpoint
        self.control_file = control_file
        self.terminal_ack_episode = None
        self.raw_neural_features = None
        self.episode_id = None
        self.episode_transport_id = None
        self.condition = "trained"
        self.pending_id = None
        self.pending_transport_id = None
        self.command_id = 0
        self.last_tick = -1
        self.ledger = TransactionLedger()
        self.inventory_waits = 0
        self.ack_waits = 0
        self.recorded = False
        self.started = time.perf_counter()
        self.needs_start = False
        # A saved pending transaction is observed on restoration, never replayed.
        _, metadata = LinearSoftmaxPolicy.load(checkpoint)
        state = metadata["extra"].get("extension", {}).get("phase8")
        if state and self.agent.session and not self.agent.session["done"]:
            self.episode_id, self.pending_id = state["episode_id"], state["pending_id"]
            self.pending_transport_id = state.get("pending_transport_id")
            self.episode_transport_id = state.get("episode_transport_id", self.pending_transport_id)
            self.command_id, self.last_tick = state["command_id"], state["last_tick"]
            self.ledger = TransactionLedger.from_dict(state["ledger"])

    def close(self):
        self._abort("minecraft_connection_lost")
        self._record()
        self.results.close()

    def _abort(self, reason):
        if self.agent.session and not self.agent.session["done"]:
            session = self.agent.session
            if self.agent.pending is not None:
                session["unconfirmed_command_id"] = self.pending_id
                self.agent.pending = None
            # A controller abort has no reliable terminal outcome for training.
            # Confirmed action failures still go through the ordinary observer.
            if session["train"]:
                session["requested_train"] = True
                session["train"] = False
                session["training_suppressed"] = reason
            self.agent._finish(False, reason)
        self.pending_id = None

    def _record(self):
        if self.episode_id is None or self.recorded or not self.agent.session or not self.agent.session["done"]:
            return
        self.agent.session["elapsed_seconds"] = time.perf_counter() - self.started
        row = self.agent.result() | {"episode_id": self.episode_id, "condition": self.condition,
                                     "confirmed_block_changes": self.ledger.mined_blocks}
        self.results.write(json.dumps(row, separators=(",", ":")) + "\n")
        self.results.flush()
        self.recorded = True
        if (self.checkpoint_dir and self.condition == "trained" and self.agent.session["train"]
                and (self.control_file is None or self.ledger.terminal_tick is not None)):
            self.save_state(self.checkpoint_dir / (self.episode_id + ".npz"))

    def save_state(self, path):
        self.agent.save(path, extension={"phase8": {"episode_id": self.episode_id, "pending_id": self.pending_id,
                         "command_id": self.command_id, "last_tick": self.last_tick, "ledger": self.ledger.to_dict(),
                         "episode_transport_id": self.episode_transport_id,
                         "pending_transport_id": self.pending_transport_id if self.pending_id is not None else None}})

    def evaluate_request(self, request):
        started = time.perf_counter()
        with self.lock:
            if request.get("event") == "end_suite":
                self._abort("evaluation_stopped")
                self._record()
                return self._reply("NO_OP", 0, started)
            control, telemetry = request["control"], request["telemetry"]
            # Read the operator's current lifecycle state before using a delayed
            # client packet. No scoring label or fixture seed is consumed here.
            if self.control_file is not None:
                latest = json.loads(self.control_file.read_text(encoding="utf-8"))
                if latest["episode_id"] != control["episode_id"] or not latest.get("active", False) and not latest.get("terminal"):
                    return self._reply("NO_OP", 0, started, observe_only=True)
                control = latest
            terminal = control.get("terminal")
            episode = str(control["episode_id"])
            if not episode or any(char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for char in episode):
                raise ValueError("invalid episode identity")
            tick = int(request["tick_id"])
            world_id = telemetry["session_id"] + ":" + episode
            transport_id = request.get("transport_id")
            if episode == self.episode_id and (
                self.episode_transport_id is not None and transport_id != self.episode_transport_id
                or not self.needs_start and self.agent.session and world_id != self.agent.session["world_id"]
            ):
                # A replacement world/adapter needs a fresh episode identity.
                # A reused numeric command ID cannot acknowledge the old action.
                return self._reply("NO_OP", 0, started, observe_only=True) | {"terminal_acknowledged": False}
            if terminal and episode == self.episode_id and self.recorded:
                self._ack_terminal(episode)
                return self._reply("NO_OP", 0, started)
            if tick <= self.last_tick and episode == self.episode_id:
                raise ValueError("stale or duplicate observation")
            new_episode = episode != self.episode_id
            if new_episode:
                self._abort("minecraft_episode_interrupted")
                self._record()
                self.episode_id, self.last_tick = episode, -1
                self.episode_transport_id = transport_id
                self.terminal_ack_episode = None
                self.condition = control.get("condition", "trained")
                if self.condition not in CONDITIONS or control["goal"] not in OBJECTIVES:
                    raise ValueError("unsupported condition or objective")
                self.agent.policy = self.uniform if self.condition == "uniform" else self.frozen if self.condition == "frozen" else self.trained
                self.agent.rng = np.random.default_rng(int(control.get("policy_seed", 9001)))
                self.ledger, self.recorded = TransactionLedger(), False
                self.pending_id, self.inventory_waits, self.ack_waits = None, 0, 0
                self.started = started
                self.needs_start = True
            ack = request.get("ack")
            if self.pending_id is not None and (not ack or int(ack["command_id"]) < self.pending_id):
                ack = self._reconcile_lost_reply(request.get("reply_loss"), tick, world_id, transport_id) or ack
            if self.pending_id is not None and (not ack or int(ack["command_id"]) != self.pending_id):
                if terminal:
                    # The client may still be canceling an in-flight command.
                    # Never invent its execution or learn from an unacknowledged
                    # outcome. The bounded client/server handshake can retry.
                    self.ack_waits += 1
                    if self.ack_waits >= 5:
                        self.agent.session["requested_train"] = self.agent.session["train"]
                        self.agent.session["train"] = False
                        self.agent.session["training_suppressed"] = "terminal_ack_missing"
                        self.agent.pending = None
                        self._abort("terminal_ack_missing")
                        self._record()
                        self._ack_terminal(episode)
                        return self._reply("NO_OP", 0, started)
                    return self._reply("NO_OP", 0, started, observe_only=True)
                self.ack_waits += 1
                if self.ack_waits >= 5:
                    self._abort("acknowledgment_timeout")
                    self._record()
                    return self._reply("NO_OP", 0, started)
                return self._reply("NO_OP", 0, started, observe_only=True)
            self.ack_waits = 0
            passive_before = None
            if terminal and ack and ack.get("status") == "not_executed" and self.pending_id is not None:
                self.agent.session["requested_train"] = self.agent.session["train"]
                self.agent.session["train"] = False
                self.agent.session["training_suppressed"] = "unexecuted_terminal_command"
                self.agent.session["unexecuted_command_id"] = self.pending_id
                passive_before = self.agent.pending[3] if self.agent.pending is not None else None
                self.agent.pending = None
                self.pending_id = None
            if terminal:
                telemetry = dict(telemetry, inventory=dict(terminal["inventory"]),
                    position=list(terminal["position"]), inventory_consistent=True,
                    visible=False, near=False, station_visible=False, allowed_actions=["NO_OP"])
            try:
                # Validate the complete pose before committing inventory or a
                # block acknowledgment. A rejected packet may be retried with
                # that same acknowledgment and must not partly mutate evidence.
                position = [float(v) for v in telemetry["position"]]
                if len(position) != 3 or not all(math.isfinite(v) for v in position):
                    raise ObservationError("invalid_position")
                visible = bool(telemetry["visible"])
                distance = float(telemetry["target_distance"]) if visible else None
                angle = float(telemetry["target_angle"]) if visible else None
                if visible and (not math.isfinite(distance) or not 0 <= distance <= 12 or not math.isfinite(angle)):
                    raise ObservationError("invalid_visible_geometry")
                pitch_error = telemetry.get("target_pitch_error") if visible and self.pitch_actions else 0.0
                if type(pitch_error) not in (int, float) or not math.isfinite(pitch_error) or abs(pitch_error) > math.pi:
                    raise ObservationError("invalid_visible_pitch_error")
                inventory = self.ledger.observe(telemetry, ack if self.pending_id is not None and ack.get("status") != "not_executed" else None,
                                                terminal_tick=int(terminal["server_tick"]) if terminal else None)
                self.inventory_waits = 0
            except ObservationError as error:
                self.inventory_waits += 1
                if self.inventory_waits >= 5 and self.agent.session:
                    self._abort(str(error))
                    self._record()
                    return self._reply("NO_OP", 0, started)
                return self._reply("NO_OP", 0, started, observe_only=True)
            actions = self.agent.policy.actions
            allowed_actions = [action for action in telemetry["allowed_actions"] if action in actions]
            if control["goal"] == "three_logs":
                # This objective needs logs in inventory. Recipes can consume them.
                allowed_actions = [action for action in allowed_actions if action not in CRAFT_ACTIONS]
            observation = {"world_id": world_id, "position": position,
                "visible": visible, "sector": request.get("sector") if visible else None,
                "near": bool(telemetry["near"]), "distance": distance, "angle": angle,
                "pitch_error": pitch_error,
                "target_id": telemetry.get("target_id"), "inventory": inventory, "produced": dict(self.ledger.produced),
                "allowed_actions": allowed_actions,
                "restrict_recipes": control["goal"] in {"sticks", "crafting_table", "wooden_pickaxe", "pickaxe_transaction"},
                "last_error": ack.get("error", "") if ack and self.pending_id is not None else "",
                "resource_exhausted": False, "interrupted": bool(ack and ack.get("status") == "interrupted")}
            if terminal and self.agent.pending and ack and ack.get("error") == "episode_boundary" \
                    and self.agent.manager.goals[self.agent.manager.root].satisfied(observation):
                # Ending a successful goal cancels any remaining held input.
                # That lifecycle cancellation is not an action failure/recovery.
                observation["last_error"] = ""
                observation["interrupted"] = False
            if self.needs_start or self.agent.session is None:
                self.agent.start(OBJECTIVES[control["goal"]], observation,
                                 train=bool(control.get("train", False)) and self.condition == "trained")
                self.needs_start = False
            elif not terminal and self.pending_id is not None and ack.get("status") == "not_executed":
                if ack.get("action") != actions[self.agent.pending[1]]:
                    self._abort("ack_action_mismatch")
                else:
                    # The adapter rejected delivery, so there is no executed
                    # action to reward, penalize, remember or replay. Sample a
                    # fresh decision from the current observation instead.
                    self.agent.session.setdefault("requested_train", self.agent.session["train"])
                    self.agent.session["train"] = False
                    self.agent.session["training_suppressed"] = "unexecuted_command"
                    rejected = self.agent.session.setdefault("unexecuted_command_ids", [])
                    rejected.append(self.pending_id)
                    self.agent.pending = None
                    self.pending_id = None
                    observation["last_error"] = ""
                    observation["interrupted"] = False
                    self.agent.memory.inventory = inventory.copy()
                    if len(rejected) >= 5:
                        self._abort("command_delivery_rejected")
            elif self.agent.pending:
                if ack.get("action") != actions[self.agent.pending[1]]:
                    self._abort("ack_action_mismatch")
                else:
                    self.agent.observe(observation)
                self.pending_id = None
            self.last_tick = tick
            if terminal:
                self.agent.session["terminal_server_tick"] = int(terminal["server_tick"])
                self.agent.session["terminal_inventory"] = inventory.copy()
                if not self.agent.session["done"]:
                    self.agent.observe_terminal(observation, before=passive_before)
                self._record()
                self._ack_terminal(episode)
                return self._reply("NO_OP", 0, started)
            if self.agent.session["done"]:
                if self.control_file is None:
                    self._record()
                return self._reply("NO_OP", 0, started)
            neural, _, peak = self.neural.neural_observation(request.get("sector"))
            self.raw_neural_features = np.array(neural, copy=True)
            if self.condition == "no_neural":
                neural = np.array([1., 0., 0., 0.])
            elif self.condition == "shuffled":
                # Fixed column permutation of the actual neural window. Bias
                # stays fixed; even centered observations receive the intervention.
                neural = neural[[0, 3, 1, 2]]
            action = self.agent.choose_action(observation, neural=neural)
            if self.agent.session["done"]:
                if self.control_file is None:
                    self._record()
                return self._reply("NO_OP", 0, started)
            self.command_id += 1
            self.pending_id = self.command_id
            self.pending_transport_id = transport_id
            if (action == "COLLECT_LOG" and self.mining_checkpoint is not None
                    and self.condition == "trained" and not self.agent.session["train"]):
                self.save_state(self.mining_checkpoint)
                self.mining_checkpoint = None
            return self._reply(action, self.command_id, started, peak=peak)

    def _reconcile_lost_reply(self, loss, tick, world_id, transport_id):
        if (not isinstance(loss, dict) or not isinstance(transport_id, str) or not transport_id
                or transport_id != self.pending_transport_id or self.agent.pending is None
                or self.agent.session["world_id"] != world_id):
            return None
        since, watermark = loss.get("since_tick"), loss.get("command_watermark")
        # Fabric serializes exchanges through the game-thread callback. No
        # command was accepted after this failed request, and last_tick is
        # the observation that produced the outstanding decision.
        if (type(since) is not int or type(watermark) is not int
                or not 0 <= since <= self.last_tick < tick or not 0 <= watermark < self.pending_id):
            return None
        return {"command_id": self.pending_id, "action": self.agent.policy.actions[self.agent.pending[1]],
                "status": "not_executed", "error": "bridge_reply_lost", "block_changed": False}

    def _ack_terminal(self, episode):
        if self.control_file is not None:
            path = self.control_file.with_suffix(self.control_file.suffix + ".ack")
            temporary = path.with_suffix(path.suffix + ".tmp")
            temporary.write_text(json.dumps({"episode_id": episode}), encoding="utf-8")
            temporary.replace(path)
        self.terminal_ack_episode = episode

    def _reply(self, action, command, started, *, observe_only=False, peak=0):
        done = self.agent.session is not None and self.agent.session["done"] and self.episode_id is not None
        neural = None
        probabilities = None
        inputs = None
        if command and self.agent.pending is not None:
            features, _, distribution, _ = self.agent.pending
            raw = self.raw_neural_features if self.raw_neural_features is not None else features[:4]
            neural = {name: float(value) for name, value in zip(
                ("bias", "left_readout_div50", "right_readout_div50", "total_readout_div50"), raw)}
            inputs = dict(zip(("bias", "left_input", "right_input", "total_input"), map(float, features[:4])))
            probabilities = dict(zip(self.agent.policy.actions, map(float, distribution)))
        return {"action": action, "command_id": command, "observe_only": observe_only,
                "neural_features": neural, "action_probabilities": probabilities,
                "policy_neural_inputs": inputs,
                "feature_intervention": "fixed_activity_permutation_3_1_2_bias_retained" if self.condition=="shuffled" else "zero_activity_bias_retained" if self.condition=="no_neural" else "none",
                "feature_mode": self.condition, "learning_scope": "linear_softmax_readout_only",
                "cumulative_reward": self.agent.session["total_reward"] if self.agent.session else None,
                "terminal_acknowledged": self.terminal_ack_episode == self.episode_id and self.episode_id is not None,
                "autonomy_status": self.agent.session["termination"] if done else "running", "episode_id": self.episode_id,
                "policy_source": self.policy_source + ":" + self.condition, "peak_global_active": peak,
                "neural_steps": 18 if command else 0, "latency_ms": (time.perf_counter() - started) * 1000}
