"""Sense, plan, sample the neural readout, learn, remember, and recover."""

import math
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from learning import LinearSoftmaxPolicy, NeuralFeatureTable, TrainingConfig

from .curriculum import Curriculum
from .features import FEATURE_COUNT, PITCH_FEATURE_COUNT, PITCH_SCHEMA, SCHEMA, TERRAIN_FEATURE_COUNT, TERRAIN_SCHEMA, encode, table_digest
from .goal_manager import GoalManager
from .memory import PersistentMemory
from .recovery import Recovery
from .subgoal_planner import SubgoalPlanner
from .world import ACTIONS, CRAFT_ACTIONS, LIVE_PITCH_ACTIONS, TERRAIN_ACTIONS, ResourceWorld


@dataclass(frozen=True)
class AutonomyConfig:
    max_steps: int = 120
    learning_rate: float = 0.025
    gamma: float = 0.99
    baseline_retention: float = 0.95
    gradient_clip: float = 5.0
    entropy_coefficient: float = 0.02
    stagnation_limit: int = 24
    repeat_limit: int = 4
    max_recoveries: int = 4
    goal_baselines: bool = False

    def __post_init__(self) -> None:
        if self.max_steps < 1 or self.stagnation_limit < 1 or self.repeat_limit < 1 or self.max_recoveries < 0:
            raise ValueError("invalid autonomy stopping limits")
        if self.learning_rate <= 0 or not 0 <= self.gamma <= 1 or not 0 <= self.baseline_retention < 1 or self.gradient_clip <= 0 or self.entropy_coefficient < 0:
            raise ValueError("invalid learning configuration")

    @classmethod
    def from_training(cls, config: TrainingConfig, **kwargs) -> "AutonomyConfig":
        return cls(**({key: getattr(config, key) for key in
                      ("max_steps", "learning_rate", "gamma", "baseline_retention", "gradient_clip")} | kwargs))


class AutonomousAgent:
    def __init__(self, table: NeuralFeatureTable, *, seed: int = 42, policy: LinearSoftmaxPolicy | None = None,
                 config: AutonomyConfig | None = None) -> None:
        self.table, self.seed = table, seed
        self.rng = np.random.default_rng(seed)
        self.policy = policy or LinearSoftmaxPolicy(FEATURE_COUNT, actions=ACTIONS)
        expected = {ACTIONS: FEATURE_COUNT, LIVE_PITCH_ACTIONS: PITCH_FEATURE_COUNT, TERRAIN_ACTIONS: TERRAIN_FEATURE_COUNT}.get(self.policy.actions)
        if expected is None or self.policy.weights.shape != (expected, len(self.policy.actions)):
            raise ValueError("Phase 7 readout schema mismatch; use transfer_phase65")
        self.config = config or AutonomyConfig()
        self.memory, self.curriculum = PersistentMemory(), Curriculum()
        self.planner = SubgoalPlanner()
        self.session: dict | None = None
        self.manager: GoalManager | None = None
        self.recovery = Recovery()
        self.trajectory: list = []
        self.pending: tuple | None = None

    @classmethod
    def transfer_phase65(cls, table: NeuralFeatureTable, policy: LinearSoftmaxPolicy, **kwargs) -> "AutonomousAgent":
        return cls(table, policy=policy.expanded(FEATURE_COUNT, ACTIONS), **kwargs)

    def enable_live_pitch(self) -> None:
        if self.policy.actions in (LIVE_PITCH_ACTIONS, TERRAIN_ACTIONS):
            return
        if self.session is not None and not self.session["done"]:
            raise ValueError("cannot expand an in-flight checkpoint")
        self.policy = self.policy.expanded(PITCH_FEATURE_COUNT, LIVE_PITCH_ACTIONS)

    def enable_live_terrain(self) -> None:
        if self.policy.actions == TERRAIN_ACTIONS:
            return
        if self.session is not None and not self.session["done"]:
            raise ValueError("cannot expand an in-flight checkpoint")
        self.enable_live_pitch()
        self.policy = self.policy.expanded(TERRAIN_FEATURE_COUNT, TERRAIN_ACTIONS)
        # Explicit transfer prior, not a learned jump skill: on grounded
        # observations jumping starts at one quarter of FORWARD's odds.
        # Zero logits dominated the already trained, mostly negative logits.
        self.policy.weights[:PITCH_FEATURE_COUNT, -1] = self.policy.weights[:PITCH_FEATURE_COUNT, TERRAIN_ACTIONS.index("FORWARD")]
        self.policy.weights[PITCH_FEATURE_COUNT + 2, -1] = -math.log(4)
        self.trajectory = []

    def start(self, objective: str, observation: dict, *, train: bool = False, world_seed: int = 0,
              target_count: int | None = None) -> None:
        if self.session is not None and not self.session["done"]:
            raise RuntimeError("finish the active goal before starting another")
        manager = self.planner.plan(objective, observation, target_count=target_count)
        self.memory.begin(observation)
        self.manager = manager
        self.manager.update(observation)
        self.recovery = Recovery(self.config.stagnation_limit, self.config.repeat_limit, self.config.max_recoveries)
        self.trajectory, self.pending = [], None
        self.session = {"goal": objective, "world_seed": world_seed, "world_id": observation["world_id"],
                        "train": train, "actions": 0, "total_reward": 0.0, "done": False, "success": False,
                        "termination": "running", "completed": [], "failed_actions": 0, "replans": 0,
                        "subgoals": len(self.manager.goals) - 1,
                        "subgoals_complete": sum(g.status == "complete" for g in self.manager.goals.values() if g.id != "root"),
                        "elapsed_seconds": 0.0, "update": {"weight_delta_norm": 0.0, "gradient_norm": 0.0}}
        if target_count is not None:
            self.session["target_count"] = target_count
        if self.policy.actions == TERRAIN_ACTIONS:
            self.session["exploration_cells"] = [f"{math.floor(observation['position'][0]/2)},{math.floor(observation['position'][1]/2)}"]
        if self.manager.success:
            self._finish(True, "already_complete")

    def choose_action(self, observation: dict, *, neural: np.ndarray | None = None,
                      explore_forward: bool = False) -> str:
        if self.session is None or self.session["done"]:
            return "NO_OP"
        if self.pending is not None:
            raise RuntimeError("observe the previous action outcome first")
        if observation["world_id"] != self.session["world_id"]:
            self._finish(False, "world_changed")
            return "NO_OP"
        self.manager.update(observation)
        if self.manager.success:
            self._finish(True, "success")
            return "NO_OP"
        active = self.manager.active()
        if active is not None and active.kind == "objective":
            decision = self.recovery.inspect("NO_OP", observation, observation | {"environment_changed": True},
                                             progress=False, step=self.session["actions"])
            if decision.startswith("unreachable:"):
                self._finish(False, decision)
                return "NO_OP"
            self._replan(observation)
            active = self.manager.active()
        if active is None:
            self._finish(False, "dependency_failure")
            return "NO_OP"
        neural = self.table.for_sector(observation["sector"]) if neural is None else neural
        actions = self.policy.actions
        features = encode(neural, active.kind, observation, self.memory, self.recovery,
                          pitch=actions in (LIVE_PITCH_ACTIONS, TERRAIN_ACTIONS), terrain=actions == TERRAIN_ACTIONS)
        allowed = observation["allowed_actions"]
        if observation.get("restrict_recipes"):
            allowed = [action for action in allowed if action not in CRAFT_ACTIONS or CRAFT_ACTIONS[action] == active.item]
        mask = np.array([action in allowed for action in actions])
        if self.recovery.cooldown and self.recovery.cooldown_action in actions:
            index = actions.index(self.recovery.cooldown_action)
            if mask.sum() > 1:
                mask[index] = False
        offsets = None
        if explore_forward and not observation["visible"] and active.kind in {"search", "collect"}:
            offsets = np.zeros(len(actions))
            offsets[actions.index("FORWARD")] = math.log(3)
        index, action, probabilities = self.policy.sample(features, self.rng, mask, logit_offsets=offsets)
        self.pending = (features, index, probabilities, observation | {"active_goal_item": active.item, "active_goal_count": active.count})
        return action

    def observe(self, after: dict) -> None:
        if self.pending is None:
            raise RuntimeError("no action awaits an outcome")
        features, index, probabilities, before = self.pending
        self.pending = None
        action = self.policy.actions[index]
        self.session["actions"] += 1
        changed_world = after["world_id"] != before["world_id"]
        completed = [] if changed_world else self.manager.update(after)
        self.session["completed"] = sorted(set(self.session["completed"]) | set(completed))
        self.session["subgoals_complete"] += sum(key != "root" for key in completed)
        # Reward outcomes, never an action label. Dense geometric shaping is
        # limited to the same visible resource; production and success are delayed.
        reward = -0.02 - 0.10 * bool(after["last_error"])
        geometric_progress = 0.0
        pitch_progress = 0.0
        exploration_progress = False
        if not changed_world and before["visible"] and after["visible"] and before.get("target_id") == after.get("target_id"):
            geometric_progress = before["distance"] - after["distance"]
            reward += geometric_progress + 0.2 * (abs(before["angle"]) - abs(after["angle"]))
            if self.policy.actions in (LIVE_PITCH_ACTIONS, TERRAIN_ACTIONS):
                pitch_progress = abs(before.get("pitch_error", 0.0)) - abs(after.get("pitch_error", 0.0))
                reward += 0.2 * pitch_progress
        if self.policy.actions == TERRAIN_ACTIONS and not changed_world:
            # Novelty comes only from visited own poses, never unseen resources.
            cell = f"{math.floor(after['position'][0]/2)},{math.floor(after['position'][1]/2)}"
            visited = self.session.setdefault("exploration_cells", [])
            if not before["visible"] and cell not in visited and len(visited) < 128:
                distance_moved = math.hypot(after["position"][0]-before["position"][0], after["position"][1]-before["position"][1])
                if distance_moved > .05:
                    visited.append(cell)
                    exploration_progress = True
                    if len(visited) <= 16:
                        reward += .05 * min(distance_moved, 1)
            reward -= .2 * max(0, before["health"] - after["health"])
        # Pay only production still required by the active subgoal. Rewarding
        # every craft allowed surplus-item farming to outweigh the root goal.
        item = before.get("active_goal_item", "")
        production = min(max(0, before.get("active_goal_count", 0) - before["produced"].get(item, 0)),
                         max(0, after["produced"].get(item, 0) - before["produced"].get(item, 0))) if not changed_world else 0
        reward += 0.25 * production
        success = self.manager.success and not changed_world
        if success:
            reward += 8.0
        self.session["failed_actions"] += int(bool(after["last_error"]))
        if not changed_world:
            self.memory.remember(before, action, after, reward)
        active = self.manager.active()
        recovery_observation = after | {"resource_exhausted": after.get("resource_exhausted", False)
                                       and active is not None and active.kind in {"search", "navigate", "collect"},
                                       "environment_changed": after.get("environment_changed", False)
                                       or active is not None and active.kind == "objective"}
        progress = bool(completed or production or geometric_progress > 0.05 or pitch_progress > 0.05 or exploration_progress)
        decision = None if changed_world else self.recovery.inspect(action, before, recovery_observation,
                                                                    progress=progress, step=self.session["actions"])
        reason = None
        if changed_world:
            reason = "world_changed"
        elif not success and decision:
            if decision.startswith("unreachable:"):
                reason = decision
            else:
                self._replan(after)
        if not success and self.session["actions"] >= self.config.max_steps:
            reason = reason or "max_steps"
        if reason:
            reward -= 2.0
        self.trajectory.append((features, index, probabilities, reward))
        self.session["total_reward"] += reward
        self.memory.progress = self.manager.to_dict()
        if success or reason:
            self._finish(success, "success" if success else reason)

    def _replan(self, observation: dict) -> None:
        self.manager = self.planner.plan(self.session["goal"], observation, target_count=self.session.get("target_count"))
        self.manager.update(observation)
        self.session["subgoals"] += len(self.manager.goals) - 1
        self.session["subgoals_complete"] += sum(g.status == "complete" for g in self.manager.goals.values() if g.id != "root")
        self.session["replans"] += 1

    def observe_terminal(self, after: dict, *, before: dict | None = None) -> None:
        """Account for a final passive outcome without inventing an action.

        An item may arrive after the last acknowledged action and before the
        scoring boundary. Its environment reward is recorded separately from
        action returns; no policy gradient is inferred for an unexecuted command.
        """
        if self.pending is not None:
            raise RuntimeError("acknowledge or discard the pending command first")
        if self.session is None or self.session["done"]:
            return
        if after["world_id"] != self.session["world_id"]:
            raise ValueError("terminal observation belongs to another world")
        was_success = self.manager.success
        active = self.manager.active()
        completed = self.manager.update(after)
        self.session["completed"] = sorted(set(self.session["completed"]) | set(completed))
        self.session["subgoals_complete"] += sum(key != "root" for key in completed)
        production = 0
        if before is not None and active is not None:
            item = before.get("active_goal_item", active.item)
            count = before.get("active_goal_count", active.count)
            production = min(max(0, count - before["produced"].get(item, 0)),
                             max(0, after["produced"].get(item, 0) - before["produced"].get(item, 0)))
        reward = 0.25 * production + 8.0 * (self.manager.success and not was_success)
        self.session["unattributed_terminal_reward"] = reward
        self.session["terminal_completed"] = completed
        self.session["total_reward"] += reward
        if reward and self.session["train"]:
            self.session["requested_train"] = True
            self.session["train"] = False
            self.session["training_suppressed"] = "passive_terminal_outcome"
        self.memory.inventory = dict(after["inventory"])
        self._finish(self.manager.success, "success" if self.manager.success else "episode_boundary")

    def _finish(self, success: bool, reason: str) -> None:
        if self.session["done"]:
            return
        self.session.update(done=True, success=success, termination=reason)
        if not success and self.manager.active() is not None:
            self.manager.fail(self.manager.active().id)
        self.memory.progress = self.manager.to_dict()
        if self.session["train"] and self.trajectory:
            goal_stats = self.memory.attempts.setdefault(self.session["goal"], {"successes": 0, "failures": 0, "best_steps": None})
            if self.config.goal_baselines:
                self.policy.baseline = goal_stats.get("return_baseline", 0.0)
            self.session["update"] = self.policy.apply_reinforce(
                self.trajectory, learning_rate=self.config.learning_rate, gamma=self.config.gamma,
                baseline_retention=self.config.baseline_retention, gradient_clip=self.config.gradient_clip,
                entropy_coefficient=self.config.entropy_coefficient)
            if self.config.goal_baselines:
                goal_stats["return_baseline"] = self.policy.baseline
        self.memory.finish(self.session["goal"], success, self.session["actions"])

    def result(self) -> dict:
        if self.session is None or not self.session["done"]:
            raise RuntimeError("goal is still active")
        return self.session | {"recovery_attempts": len(self.recovery.events), "recovery_successes": self.recovery.successes,
                               "recovery_events": list(self.recovery.events)}

    def run_episode(self, world: ResourceWorld, objective: str, *, train: bool = False) -> dict:
        started = time.perf_counter()
        self.start(objective, world.observe(), train=train, world_seed=world.seed)
        while not self.session["done"]:
            action = self.choose_action(world.observe())
            if not self.session["done"]:
                self.observe(world.step(action))
        self.session["elapsed_seconds"] = time.perf_counter() - started
        return self.result()

    def save(self, path: Path, *, world: ResourceWorld | None = None, extension: dict | None = None) -> None:
        schema = TERRAIN_SCHEMA if self.policy.actions == TERRAIN_ACTIONS else PITCH_SCHEMA if self.policy.actions == LIVE_PITCH_ACTIONS else SCHEMA
        state = {"schema": schema, "table_digest": table_digest(self.table), "config": asdict(self.config),
                 "memory": self.memory.to_dict(), "curriculum": self.curriculum.to_dict(), "session": self.session,
                 "manager": self.manager.to_dict() if self.manager else None, "recovery": self.recovery.to_dict(),
                 "trajectory": [[f.tolist(), i, p.tolist(), r] for f, i, p, r in self.trajectory],
                 "pending": None if self.pending is None else [self.pending[0].tolist(), self.pending[1], self.pending[2].tolist(), self.pending[3]],
                 "world": world.to_dict() if world else None, "extension": extension or {}}
        self.policy.save_atomic(path, training_seed=self.seed, rng_state=self.rng.bit_generator.state,
                                extra_metadata=state, overwrite=False)

    @classmethod
    def load(cls, path: Path, table: NeuralFeatureTable) -> tuple["AutonomousAgent", ResourceWorld | None]:
        policy, metadata = LinearSoftmaxPolicy.load(path)
        state = metadata["extra"]
        schema = TERRAIN_SCHEMA if policy.actions == TERRAIN_ACTIONS else PITCH_SCHEMA if policy.actions == LIVE_PITCH_ACTIONS else SCHEMA
        if state.get("schema") != schema or state.get("table_digest") != table_digest(table):
            raise ValueError("checkpoint schema or connectome feature cache mismatch")
        result = cls(table, seed=metadata["training_seed"], policy=policy, config=AutonomyConfig(**state["config"]))
        result.rng.bit_generator.state = metadata["rng_state"]
        result.memory = PersistentMemory.from_dict(state["memory"])
        result.curriculum = Curriculum(**state["curriculum"])
        result.session = state["session"]
        result.manager = GoalManager.from_dict(state["manager"]) if state["manager"] else None
        result.recovery = Recovery(**state["recovery"])
        result.trajectory = [(np.array(f), i, np.array(p), r) for f, i, p, r in state["trajectory"]]
        if state["pending"]:
            f, i, p, observation = state["pending"]
            result.pending = (np.array(f), i, np.array(p), observation)
        return result, ResourceWorld.from_dict(state["world"]) if state["world"] else None
