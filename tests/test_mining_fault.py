import json
from pathlib import Path
import tempfile
import unittest

from tools.run_phase8_live import pending_mining_command


class MiningFaultTests(unittest.TestCase):
    def test_disturbance_requires_an_actual_unfinished_mining_action(self):
        with tempfile.TemporaryDirectory() as directory:
            trace = Path(directory) / "actor.jsonl"
            self.assertIsNone(pending_mining_command(trace))
            def write(events, partial=""):
                trace.write_text("".join(json.dumps(event) + "\n" for event in events) + partial)
            start = {"event": "action_start", "data": {"action": "COLLECT_LOG", "command_id": 7, "server_tick": 120}}
            write([start], '{"event":')
            self.assertEqual(pending_mining_command(trace)["command_id"], 7)
            end = {"event": "action_end", "data": {"ack": {"command_id": 7}}}
            write([start, end])
            self.assertIsNone(pending_mining_command(trace))
            unrelated = {"event": "action_start", "data": {"action": "FORWARD", "command_id": 8}}
            write([start, end, unrelated])
            self.assertIsNone(pending_mining_command(trace))
            write([unrelated, start, {"event": "action_end", "data": {"ack": {"command_id": 6}}}])
            self.assertEqual(pending_mining_command(trace)["command_id"], 7)
