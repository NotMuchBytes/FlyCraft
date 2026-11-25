"""Budget, seed and progression checks; synthetic, not live skill scores."""
import unittest
from autonomy.staged import StagedCampaign, STAGES, RETENTION_MINIMUMS, gate_report
from autonomy.experiment import CONDITIONS


class StagedTests(unittest.TestCase):
    def campaign(self):
        c = StagedCampaign.__new__(StagedCampaign)
        c.config = dict(foundation=dict(foundation_world_instances=338), supported_stages=list(STAGES))
        c.state = dict(curriculum_index=0, active_attempt=None, attempts=[], status="ready",
                       current_checkpoint=dict(path="candidate", sha256="frozen"), stage_checkpoints={}, gates={})
        c.save = lambda: None
        return c

    def evaluated(self, successes=24):
        return [dict(curriculum_stage="terrain", split="eval_a", status="committed", evaluation_task=task,
            condition=condition, evaluation_index=i, success=i < successes, train=False, generated_world_instances=1)
            for task, conditions in [("primary", CONDITIONS)] + [("retention_"+g, ("trained",)) for g in RETENTION_MINIMUMS]
            for condition in conditions for i in range(30)]

    def test_gate_requires_all_controls_and_retention_and_never_counts_duplicates(self):
        rows = self.evaluated()
        self.assertTrue(gate_report(rows, "terrain")["passed"])
        self.assertFalse(gate_report(rows[:-1], "terrain")["passed"])
        self.assertFalse(gate_report(rows + [rows[0]], "terrain")["passed"])
        self.assertFalse(gate_report(self.evaluated(23), "terrain")["passed"])
        rows[150]["success"] = False
        self.assertFalse(gate_report(rows, "terrain")["passed"])

    def test_each_retained_goal_has_its_own_original_success_threshold(self):
        rows = self.evaluated(30)
        for row in rows:
            if row["evaluation_task"].startswith("retention_"):
                goal = row["evaluation_task"][len("retention_"):]
                row["success"] = row["evaluation_index"] < RETENTION_MINIMUMS[goal]
        self.assertTrue(gate_report(rows,"terrain")["passed"])
        pick = next(r for r in rows if r["evaluation_task"]=="retention_wooden_pickaxe" and r["success"])
        pick["success"] = False
        self.assertFalse(gate_report(rows,"terrain")["passed"])

    def test_foundation_budget_retention_and_locked_evaluation(self):
        c = self.campaign()
        self.assertEqual(c.training_worlds(), 338)
        self.assertEqual(c.next_cell()["split"], "training")
        c.state["attempts"] = [dict(curriculum_stage="terrain", split="training", train=True,
            status="committed", generated_world_instances=1) for _ in range(3)]
        self.assertTrue(c.next_cell()["retention"])
        c.state["attempts"] *= 21
        self.assertEqual(len(c.state["attempts"]), 63)
        c.state["attempts"].append(dict(c.state["attempts"][0]))
        self.assertEqual(c.training_worlds(), 402)
        self.assertEqual(c.next_cell()["evaluation_task"], "primary")
        self.assertEqual(c.state["stage_checkpoints"]["terrain"], c.state["current_checkpoint"])
        c.state["attempts"] += self.evaluated(23)
        self.assertIsNone(c.next_cell())
        self.assertEqual(c.state["status"], "stage_gate_failed")
        self.assertEqual(c.state["curriculum_index"], 0)
        c.state["attempts"] = c.state["attempts"][:64] + self.evaluated(24)
        self.assertEqual(c.next_cell()["split"], "training")
        self.assertEqual(c.state["curriculum_index"], 1)

    def test_pending_skills_do_not_fall_back_to_wood_training(self):
        c = self.campaign()
        c.state["curriculum_index"] = len(STAGES)
        self.assertIsNone(c.next_cell())
        self.assertEqual(c.state["status"], "awaiting_next_skill_implementation")
