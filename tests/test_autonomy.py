from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

import numpy as np

from autonomy import AutonomousAgent, AutonomyConfig, GOALS, ResourceWorld, SubgoalPlanner
from autonomy.curriculum import Curriculum
from autonomy.features import FEATURE_COUNT
from autonomy.goal_manager import Goal, GoalManager
from autonomy.memory import PersistentMemory
from autonomy.metrics import summarize
from autonomy.recovery import Recovery
from autonomy.world import ACTIONS
from learning import LinearSoftmaxPolicy, NeuralFeatureTable, TrainingConfig

ROOT = Path(__file__).resolve().parents[1]


class AutonomyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.table = NeuralFeatureTable.from_phase35(ROOT / "experiments/phase35/results/rate_decoder_evaluation.json")

    def world_near(self):
        world = ResourceWorld(7, "wooden_pickaxe")
        world.resources = [{"id": "test_tree", "x": 15, "y": 15.8, "logs": 6}]
        return world

    def test_pickaxe_plan_recipe_dependencies_and_consumption(self):
        world = self.world_near()
        manager = SubgoalPlanner().plan("wooden_pickaxe", world.observe())
        # A mechanic fixture deliberately executes a recipe; not an intelligence benchmark.
        actions = ["COLLECT_LOG", "CRAFT_PLANKS", "COLLECT_LOG", "CRAFT_PLANKS", "CRAFT_STICKS",
                   "COLLECT_LOG", "CRAFT_PLANKS", "CRAFT_TABLE", "PLACE_TABLE", "CRAFT_PICKAXE"]
        for action in actions:
            manager.update(world.observe())
            self.assertIsNotNone(manager.active())
            world.step(action)
            self.assertFalse(world.last_error)
        manager.update(world.observe())
        self.assertTrue(manager.success)
        self.assertEqual(world.inventory["wooden_pickaxe"], 1)
        self.assertEqual(world.produced["log"], 3)
        self.assertEqual(world.inventory["planks"], 3)
        self.assertTrue(all(goal.status == "complete" for goal in manager.goals.values()))

    def test_dependencies_priorities_cycles_and_failure(self):
        goals = [Goal("a", "search", "visible", priority=2), Goal("b", "search", "visible", priority=4),
                 Goal("root", "objective", "dependencies", dependencies=("a", "b"))]
        manager = GoalManager(goals)
        self.assertEqual(manager.active().id, "b")
        manager.fail("a")
        self.assertEqual(manager.goals["root"].status, "failed")
        for bad in ([Goal("root", "x", "near", dependencies=("missing",))],
                    [Goal("root", "x", "near", dependencies=("root",))]):
            with self.assertRaises(ValueError):
                GoalManager(bad)

    def test_already_complete_goal_needs_no_actions(self):
        world = self.world_near()
        world.inventory["wooden_pickaxe"] = 1
        agent = AutonomousAgent(self.table)
        row = agent.run_episode(world, "wooden_pickaxe")
        self.assertTrue(row["success"])
        self.assertEqual(row["actions"], 0)

    def test_no_automatic_collection_or_crafting_and_station_required(self):
        world = self.world_near()
        world.step("NO_OP")
        self.assertEqual(sum(world.inventory.values()), 0)
        world.step("CRAFT_PICKAXE")
        self.assertEqual(world.last_error, "missing_precondition")
        world.inventory.update(planks=3, sticks=2)
        self.assertNotIn("CRAFT_PICKAXE", world.observe()["allowed_actions"])

    def test_memory_is_bounded_and_world_scoped(self):
        world = self.world_near()
        memory = PersistentMemory(capacity=3, max_worlds=2)
        memory.begin(world.observe())
        for _ in range(5):
            before = world.observe()
            memory.remember(before, "NO_OP", world.step("NO_OP"), -0.02)
        memory.finish("wooden_pickaxe", False, 5)
        restored = PersistentMemory.from_dict(copy.deepcopy(memory.to_dict()))
        self.assertEqual(restored.to_dict(), memory.to_dict())
        self.assertEqual(len(restored.recent), 3)
        restored.begin(ResourceWorld(8).observe())
        self.assertEqual(len(restored.recent), 0)
        self.assertEqual(restored.attempts["wooden_pickaxe"]["failures"], 1)
        restored.begin(ResourceWorld(9).observe())
        self.assertEqual(len(restored.worlds), 2)

    def test_recovery_detects_stagnation_interruptions_and_is_bounded(self):
        recovery = Recovery(stagnation_limit=3, repeat_limit=2, max_recoveries=1)
        obs = self.world_near().observe()
        after = obs | {"last_error": "blocked"}
        self.assertIsNone(recovery.inspect("FORWARD", obs, after, progress=False, step=1))
        self.assertEqual(recovery.inspect("FORWARD", obs, after, progress=False, step=2), "replan:repeated_failure")
        recovery.inspect("TURN_LEFT", obs, obs, progress=True, step=3)
        self.assertEqual(recovery.successes, 1)
        self.assertEqual(recovery.inspect("NO_OP", obs, obs | {"interrupted": True}, progress=False, step=4), "unreachable:interrupted")

    def test_obstacles_block_motion_and_enter_memory(self):
        world = self.world_near()
        world.obstacles = [(15, 15.5, 0.3)]
        before = world.observe()
        after = world.step("FORWARD")
        self.assertEqual(after["position"], before["position"])
        self.assertEqual(after["last_error"], "blocked")
        memory = PersistentMemory()
        memory.begin(before)
        memory.remember(before, "FORWARD", after, -1)
        self.assertEqual(len(memory.worlds[memory.world_id]["obstacles"]), 1)

    def test_curriculum_requires_heldout_performance(self):
        curriculum = Curriculum(threshold=0.75, min_evaluations=4)
        rows = [{"goal": GOALS[0], "world_seed": i, "train": False, "success": i < 3, "actions": 10} for i in range(4)]
        self.assertFalse(curriculum.assess(rows[:2], training_seeds={100}))
        self.assertEqual(curriculum.level, 0)
        self.assertTrue(curriculum.assess(rows, training_seeds={100}))
        self.assertEqual(curriculum.level, 1)
        with self.assertRaises(ValueError):
            Curriculum().assess(rows, training_seeds={1})

    def test_transfer_keeps_original_readout_weights_and_train_config(self):
        policy = LinearSoftmaxPolicy()
        policy.weights[:] = np.arange(16).reshape(4, 4)
        agent = AutonomousAgent.transfer_phase65(self.table, policy, config=AutonomyConfig.from_training(TrainingConfig(max_steps=40)))
        np.testing.assert_array_equal(agent.policy.weights[:4, :4], policy.weights)
        self.assertEqual(agent.config.max_steps, 40)

    def test_masked_entropy_reinforce_updates_policy_from_delayed_failure(self):
        policy = LinearSoftmaxPolicy(FEATURE_COUNT, actions=ACTIONS)
        features = np.ones(FEATURE_COUNT)
        mask = np.array([action in ("NO_OP", "FORWARD") for action in ACTIONS])
        probabilities = policy.probabilities(features, mask)
        trajectory = [(features, 3, probabilities, 0), (features, 3, probabilities, -2)]
        before = probabilities[3]
        policy.apply_reinforce(trajectory, learning_rate=0.01, gamma=0.99, baseline_retention=0.95, gradient_clip=5, entropy_coefficient=0.02)
        self.assertLess(policy.probabilities(features, mask)[3], before)
        np.testing.assert_array_equal(policy.weights[:, 4:], 0)

    def test_exact_mid_action_checkpoint_resume_and_artifact_protection(self):
        config = AutonomyConfig(max_steps=35)
        agent = AutonomousAgent(self.table, seed=123, config=config)
        world = ResourceWorld(456, "collect_multiple")
        agent.start("collect_multiple", world.observe(), train=True, world_seed=world.seed)
        action = agent.choose_action(world.observe())
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.npz"
            agent.save(path, world=world)
            with self.assertRaises(FileExistsError):
                agent.save(path, world=world)
            restored, restored_world = AutonomousAgent.load(path, self.table)
        self.assertEqual(restored.memory.to_dict(), agent.memory.to_dict())
        agent.observe(world.step(action))
        restored.observe(restored_world.step(action))
        for controller, environment in ((agent, world), (restored, restored_world)):
            while not controller.session["done"]:
                choice = controller.choose_action(environment.observe())
                if not controller.session["done"]:
                    controller.observe(environment.step(choice))
        self.assertEqual(agent.result(), restored.result())
        np.testing.assert_array_equal(agent.policy.weights, restored.policy.weights)
        self.assertEqual(agent.rng.bit_generator.state, restored.rng.bit_generator.state)

    def test_simulated_end_to_end_training_fixed_seed_and_metrics(self):
        def run():
            agent = AutonomousAgent(self.table, seed=31, config=AutonomyConfig(max_steps=30))
            rows = [agent.run_episode(ResourceWorld(seed), GOALS[0], train=True) for seed in range(12)]
            for row in rows:
                row["elapsed_seconds"] = 0
            return agent, rows
        first, rows = run()
        second, repeated = run()
        self.assertEqual(rows, repeated)
        np.testing.assert_array_equal(first.policy.weights, second.policy.weights)
        self.assertGreater(np.linalg.norm(first.policy.weights), 0)
        self.assertEqual(first.policy.episodes_trained, 12)
        self.assertEqual(summarize(rows)["episodes"], 12)
        frozen = first.policy.weights.copy()
        first.run_episode(ResourceWorld(999), GOALS[0], train=False)
        np.testing.assert_array_equal(first.policy.weights, frozen)

    def test_missing_resources_terminates_without_infinite_replanning(self):
        world = self.world_near()
        world.resources = []
        agent = AutonomousAgent(self.table)
        row = agent.run_episode(world, "collect_multiple")
        self.assertEqual(row["termination"], "unreachable:missing_resources")
        self.assertLessEqual(row["actions"], 1)

    def test_crafting_continues_after_last_tree_is_exhausted(self):
        world = self.world_near()
        world.resources = []
        world.inventory["log"] = 1
        agent = AutonomousAgent(self.table, seed=5)
        agent.start("craft_simple", world.observe(), train=True)
        action = agent.choose_action(world.observe())
        agent.observe(world.step(action))
        self.assertNotEqual(agent.session["termination"], "unreachable:missing_resources")

    def test_all_goals_terminate_even_when_resources_are_spent_off_plan(self):
        agent = AutonomousAgent(self.table, seed=11, config=AutonomyConfig(max_steps=120))
        for goal in GOALS:
            for seed in range(10):
                row = agent.run_episode(ResourceWorld(seed, goal), goal, train=True)
                self.assertLessEqual(row["actions"], 120)
                self.assertTrue(row["done"])

    def test_lost_resources_reopen_dependencies_with_bounded_recovery(self):
        world = self.world_near()
        agent = AutonomousAgent(self.table, seed=1)
        agent.start("collect_multiple", world.observe())
        # Observe a valid action while an external inventory loss invalidates
        # a formerly completed production prerequisite.
        for _ in range(3):
            world.step("COLLECT_LOG")
        world.inventory["log"] = 0
        action = agent.choose_action(world.observe())
        agent.observe(world.step(action))
        self.assertGreaterEqual(agent.session["replans"], 1)

    def test_surplus_crafting_does_not_earn_progress_reward(self):
        world = self.world_near()
        agent = AutonomousAgent(self.table)
        world.inventory["log"] = 1
        # collect_multiple needs more logs; turning one into unrequested
        # planks must not be rewarded just because production increased.
        agent.start("collect_multiple", world.observe())
        agent.policy.weights[:, :] = 0
        agent.policy.weights[0, ACTIONS.index("CRAFT_PLANKS")] = 1000
        action = agent.choose_action(world.observe())
        self.assertEqual(action, "CRAFT_PLANKS")
        agent.observe(world.step(action))
        self.assertLess(agent.session["total_reward"], 0)


if __name__ == "__main__":
    unittest.main()
