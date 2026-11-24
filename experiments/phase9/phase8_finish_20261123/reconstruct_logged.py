"""Reconstruct training features from recorded operational observations and acknowledgments."""

import json
from pathlib import Path
import sys
import tempfile

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from autonomy.minecraft import LiveResourceController
from learning import NeuralFeatureTable

table = NeuralFeatureTable.from_phase35(ROOT / "experiments/phase35/results/rate_decoder_evaluation.json")
checkpoint = ROOT / "checkpoints/phase9/dev_pilot_20261029_b_pilot_trained_00002_a0003/trial_0000.npz"


class RecordedNeural:
    response = None

    def neural_observation(self, sector):
        neural = self.response["neural_features"]
        return np.array([neural[key] for key in (
            "bias", "left_readout_div50", "right_readout_div50", "total_readout_div50")]), None, 0


def reconstruct(run_id):
    neural = RecordedNeural()
    trajectories = {}
    acknowledgments = {}
    events = [json.loads(line) for line in (ROOT / "experiments/phase9" / run_id / "bridge.jsonl").read_text().splitlines()]
    scored_ids = {json.loads(line)["episode_id"] for line in
                  (ROOT / "experiments/phase9" / run_id / "server.jsonl").read_text().splitlines()}
    terminals = {}
    for event in events:
        request = json.loads(event["request"])
        control = request.get("control", {})
        if control.get("terminal"):
            terminals[control["episode_id"]] = control["terminal"]
    with tempfile.TemporaryDirectory() as directory:
        controller = LiveResourceController(neural, table, checkpoint,
            result_log=Path(directory) / "reconstruction.jsonl", pitch_actions=True)
        current = {}

        def sample(features, rng, mask=None, *, logit_offsets=None):
            probabilities = controller.agent.policy.probabilities(features, mask, logit_offsets=logit_offsets)
            expected = current["response"]
            logged = np.array([expected["action_probabilities"][action] for action in controller.agent.policy.actions])
            np.testing.assert_allclose(probabilities, logged, rtol=1e-10, atol=1e-12)
            action = expected["action"]
            index = controller.agent.policy.actions.index(action)
            assert mask[index]
            return index, action, probabilities

        controller.trained.sample = sample
        observe = controller.agent.observe

        def observe_with_acknowledgment(observation):
            acknowledgment = dict(current["request"]["ack"])
            observe(observation)
            acknowledgments.setdefault(controller.episode_id, []).append(acknowledgment)

        controller.agent.observe = observe_with_acknowledgment
        try:
            for event in events:
                request = json.loads(event["request"])
                expected = event.get("response") or {}
                if expected.get("status") != "ok":
                    continue
                if "control" in request and request["control"]["episode_id"] not in scored_ids:
                    continue
                if "control" in request and expected.get("terminal_acknowledged") and not request["control"].get("terminal"):
                    episode = expected["episode_id"]
                    request["control"] = request["control"] | {"active":False,"terminal":terminals[episode]}
                current["response"] = expected
                current["request"] = request
                neural.response = expected
                response = controller.evaluate_request(request)
                assert response["command_id"] == expected["command_id"], (request["tick_id"], response, expected)
                if controller.recorded and controller.episode_id not in trajectories:
                    trajectories[controller.episode_id] = {
                        "session": dict(controller.agent.session),
                        "trajectory": [(f.copy(), i, p.copy(), r) for f, i, p, r in controller.agent.trajectory],
                        "acknowledgments": list(acknowledgments.get(controller.episode_id, [])),
                    }
                    assert len(trajectories[controller.episode_id]["trajectory"]) == len(
                        trajectories[controller.episode_id]["acknowledgments"])
        finally:
            controller.close()
    return trajectories


if __name__ == "__main__":
    for run_id in sys.argv[1:]:
        try:
            episodes = reconstruct(run_id)
            print(run_id, [(key, len(value["trajectory"]), value["session"]["success"])
                            for key, value in episodes.items()])
        except Exception as error:
            print(run_id, type(error).__name__, str(error)[:500])
