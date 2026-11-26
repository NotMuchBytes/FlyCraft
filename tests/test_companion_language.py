"""Synthetic language/goal protocol checks, separate from live Minecraft proof."""
import copy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from autonomy.subgoal_planner import SubgoalPlanner
from autonomy.agent import AutonomousAgent
import test_phase8 as fixtures

ROOT=Path(__file__).resolve().parents[1]


class CompanionLanguageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):fixtures.Phase8Tests.setUpClass()

    def test_requested_counts_need_explicit_nontraining_companion_and_cannot_change(self):
        helper=fixtures.Phase8Tests()
        with tempfile.TemporaryDirectory() as directory:
            c=helper.controller(Path(directory))
            try:
                request=helper.request(10);request['control']['requested_count']=3
                with self.assertRaises(ValueError):c.evaluate_request(request)
                self.assertIsNone(c.ledger.previous)
                request['control'].update(companion_request=True,train=True)
                with self.assertRaises(ValueError):c.evaluate_request(request)
                request['control']['train']=False
                first=c.evaluate_request(request)
                self.assertEqual(c.agent.manager.goals['root'].count,3)
                altered=helper.request(20,ack=helper.ack(first));altered['control'].update(companion_request=True,requested_count=2)
                with self.assertRaises(ValueError):c.evaluate_request(altered)
                self.assertEqual(c.agent.session['actions'],0)
            finally:c.close()

    def test_three_requested_logs_need_three_actual_inventory_gains(self):
        helper=fixtures.Phase8Tests()
        with tempfile.TemporaryDirectory() as directory:
            c=helper.controller(Path(directory))
            try:
                request=helper.request(10);request['control'].update(companion_request=True,requested_count=3)
                result=c.evaluate_request(request)
                for i in range(1,4):
                    inventory={key:0 for key in fixtures.ITEMS};inventory['log']=i
                    request=helper.request(10+i*10,ack=helper.ack(result),telemetry=helper.telemetry(inventory=inventory,inventory_revision=1+i))
                    request['control'].update(companion_request=True,requested_count=3)
                    result=c.evaluate_request(request)
                    self.assertEqual(c.agent.session['success'],i==3)
                self.assertFalse(c.agent.session['train'])
                self.assertEqual(c.agent.session['update']['weight_delta_norm'],0)
            finally:c.close()

    def test_planner_batches_and_replan_keep_the_requested_inventory_count(self):
        planner=SubgoalPlanner();observation=dict(inventory={},produced={})
        planned=planner.plan('craft_simple',observation,target_count=5)
        self.assertEqual(planned.goals['root'].count,5)
        collection=[g for g in planned.goals.values() if g.kind=='collect']
        self.assertEqual(collection[0].count,2)
        for count in (0,17,True,2.5):
            with self.assertRaises(ValueError):planner.plan('find_collect',observation,target_count=count)
        agent=AutonomousAgent(fixtures.Phase8Tests.table)
        observed=dict(world_id='request-replan',inventory={},produced={},visible=True,near=True)
        agent.start('find_collect',observed,target_count=3)
        agent._replan(observed|dict(inventory={'log':1},produced={'log':1}))
        self.assertEqual(agent.manager.goals['root'].count,3)
        self.assertFalse(agent.manager.success)

    @unittest.skipUnless((ROOT/'.runtime/jdk-25/bin/javac.exe').exists(),'Local JDK unavailable')
    def test_real_java_language_ownership_receipts_and_persistent_word_learning(self):
        with tempfile.TemporaryDirectory() as directory:
            src=ROOT/'minecraft_mod/src'
            files=[src/'main/java/org/flycraft/bridge/AtomicFiles.java',
                *sorted((src/'main/java/org/flycraft/bridge/language').glob('*.java')),
                src/'test/java/org/flycraft/bridge/language/EnglishOrdersTest.java']
            command=[str(ROOT/'.runtime/jdk-25/bin/javac.exe'),'-d',directory,*map(str,files)]
            compiled=subprocess.run(command,capture_output=True,text=True,timeout=30)
            self.assertEqual(compiled.returncode,0,compiled.stderr)
            result=subprocess.run([str(ROOT/'.runtime/jdk-25/bin/java.exe'),'-cp',directory,'org.flycraft.bridge.language.EnglishOrdersTest'],capture_output=True,text=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertTrue(json.loads(result.stdout)['delivery_verified'])
