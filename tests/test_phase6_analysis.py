import tempfile
import unittest
from pathlib import Path

from tools.analyze_phase6 import parse_log, summarize


class Phase6AnalysisTests(unittest.TestCase):
    def test_parses_episode_and_summarizes(self) -> None:
        line = (
            "[00:00:00] FLYCRAFT_PHASE6 episode_end episode=1 task=T1_ORIENT seed=6101 "
            "success=true termination=success steps=3 reward=3.5 initial_distance=7.0 "
            "final_distance=6.5 initial_angle_error=40.0 final_angle_error=5.0\n"
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "server.log"
            path.write_text(line, encoding="utf-8")
            episodes = parse_log(path, "trained")
        self.assertEqual(len(episodes), 1)
        self.assertEqual(episodes[0]["seed"], 6101)
        self.assertTrue(episodes[0]["success"])
        metrics = summarize(episodes)
        self.assertEqual(metrics["success_rate"], 1.0)
        self.assertEqual(metrics["mean_steps_to_success"], 3.0)


if __name__ == "__main__":
    unittest.main()
