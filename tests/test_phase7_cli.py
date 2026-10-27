import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

from autonomy import AutonomousAgent
from learning import NeuralFeatureTable

ROOT = Path(__file__).resolve().parents[1]


class Phase7CliTests(unittest.TestCase):
    def test_cli_resume_matches_uninterrupted_training_and_protects_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            def run(name, episodes, *extra):
                return subprocess.run([sys.executable, str(ROOT / "tools/train_phase7.py"), "--episodes", str(episodes),
                                       "--seed", "55", "--goal", "collect_nearby", "--max-steps", "30", "--evaluate-every", "5",
                                       "--checkpoint", str(folder / (name + ".npz")), "--output", str(folder / (name + ".jsonl")), *extra],
                                      cwd=ROOT, capture_output=True, text=True, timeout=30)
            for name, count, extra in (("full", 20, ()), ("part", 10, ()), ("resumed", 10, ("--resume", str(folder / "part.npz")))):
                result = run(name, count, *extra)
                self.assertEqual(result.returncode, 0, result.stderr)
            table = NeuralFeatureTable.from_phase35(ROOT / "experiments/phase35/results/rate_decoder_evaluation.json")
            full, _ = AutonomousAgent.load(folder / "full.npz", table)
            resumed, _ = AutonomousAgent.load(folder / "resumed.npz", table)
            np.testing.assert_array_equal(full.policy.weights, resumed.policy.weights)
            self.assertEqual(full.policy.baseline, resumed.policy.baseline)
            self.assertEqual(full.rng.bit_generator.state, resumed.rng.bit_generator.state)
            self.assertEqual(full.memory.to_dict(), resumed.memory.to_dict())
            original = (folder / "full.npz").read_bytes()
            self.assertNotEqual(run("full", 20).returncode, 0)
            self.assertEqual(original, (folder / "full.npz").read_bytes())


if __name__ == "__main__":
    unittest.main()
