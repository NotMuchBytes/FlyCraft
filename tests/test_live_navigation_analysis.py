"""Synthetic audit fixtures, never offered as gameplay or video evidence."""

import json
import math
from pathlib import Path
import tempfile
import unittest

from tools.analyze_live_navigation import analyze_run


class NavigationAnalysisTests(unittest.TestCase):
    def analyze(self, rows):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            (folder / "run.json").write_text(json.dumps({"turn_degrees": 15, "forward_ticks": 2}))
            (folder / "bridge.jsonl").write_text("\n".join(map(json.dumps, rows)))
            return analyze_run(folder)

    def row(self, command, action, *, x=0, yaw=0, ack=None, episode="test"):
        return {"request": json.dumps({"control": {"episode_id": episode}, "telemetry": {
            "position": [x, 0, math.radians(yaw)], "visible": False, "near": False,
            "allowed_actions": ["FORWARD", "TURN_LEFT", "TURN_RIGHT"]}, "ack": ack}),
            "response": {"command_id": command, "action": action}}

    def test_unexecuted_duplicate_and_wrong_episode_are_not_movement(self):
        ack = {"command_id": 1, "action": "FORWARD", "status": "not_executed"}
        result = self.analyze([self.row(1, "FORWARD"), self.row(0, "NO_OP", x=2, ack=ack),
                               self.row(0, "NO_OP", x=3, ack=ack),
                               self.row(1, "FORWARD", episode="new"),
                               self.row(0, "NO_OP", x=4, ack=ack)])
        self.assertEqual(result["not_executed_commands"], 1)
        self.assertEqual(result["motions"], [])
        self.assertEqual(result["unmatched_commands"], 1)

    def test_turn_endpoint_wraparound_and_actual_forward_displacement(self):
        result = self.analyze([self.row(1, "TURN_RIGHT", yaw=175),
            self.row(2, "FORWARD", yaw=-170, ack={"command_id": 1, "action": "TURN_RIGHT", "status": "success"}),
            self.row(0, "NO_OP", x=.3, yaw=-170, ack={"command_id": 2, "action": "FORWARD", "status": "success"})])
        self.assertAlmostEqual(result["max_absolute_turn_endpoint_error"], 0)
        self.assertAlmostEqual(result["median_forward_displacement"], .3)
        self.assertEqual(result["actions_acknowledged"], {"TURN_RIGHT": 1, "FORWARD": 1})

    def test_mismatched_action_ack_cannot_credit_execution(self):
        result = self.analyze([self.row(1, "FORWARD"), self.row(0, "NO_OP", x=9,
            ack={"command_id": 1, "action": "TURN_LEFT", "status": "success"})])
        self.assertEqual(result["ack_statuses"], {"ack_action_mismatch": 1})
        self.assertEqual(result["motions"], [])


if __name__ == "__main__":
    unittest.main()
