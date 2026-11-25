import copy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

from tools.launch_cache import freeze_cache, cached_commands
from tools.resource_readiness import ResourceReadiness
from tools.continue_phase9 import check_transport_changes, HARNESS
from autonomy.experiment import digest, source_manifest


class PerformanceTests(unittest.TestCase):
    def test_execution_revision_keeps_world_counter_seeds_checkpoint_and_fault_evidence(self):
        from autonomy import AutonomousAgent
        from autonomy.experiment import Campaign, atomic_json
        from learning import NeuralFeatureTable
        from tools.continue_phase9 import continue_execution
        project = Path(__file__).resolve().parents[1]
        table = NeuralFeatureTable.from_phase35(project / "experiments/phase35/results/rate_decoder_evaluation.json")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            graph = root / "data/processed/connectome_raw_csr.npz"
            graph.parent.mkdir(parents=True)
            graph.write_bytes(b"UNIT GRAPH MARKER")
            (root / "tools").mkdir()
            (root / "tools/supervise_phase9.py").write_text("# original launcher\n")
            initial = root / "initial.npz"
            AutonomousAgent(table).save(initial)
            campaign = Campaign.create(root / "campaign", project_root=root, name="revision_unit", checkpoint=initial,
                table=table, worlds=10000, official=True, checked=True, compact=True,
                authorization=dict(statement="unit only", authorized_date="unit"))
            row = dict(split="training", status="interrupted", generated_world_instances=1, world_seed=campaign.catalog["training"][0],
                goal="one_log", started_unix=0, finished_unix=1, error="preserve original failure")
            campaign.state["attempts"].append(row)
            campaign.save()
            (campaign.folder / "STOP").touch()
            (campaign.folder / "attention").mkdir()
            atomic_json(campaign.folder / "fix_request.json", dict(reason="original fault"))
            archive = campaign.folder / "execution_revisions/revision_0001"
            archive.mkdir(parents=True)
            import shutil
            for name in ("config.json", "state.json", "source_manifest.json"):
                shutil.copy2(campaign.folder / name, archive / name)
            (archive / "source/tools").mkdir(parents=True)
            shutil.copy2(root / "tools/supervise_phase9.py", archive / "source/tools/supervise_phase9.py")
            old_source = campaign.config["implementation_sha256"]
            seeds = (campaign.folder / "seeds.json").read_bytes()
            checkpoint = dict(campaign.state["current_checkpoint"])
            (root / "tools/supervise_phase9.py").write_text("# changed launcher only\n")
            current = source_manifest(root)["implementation_sha256"]
            cache = root / "cache.json"
            atomic_json(cache, dict(implementation_sha256=current, files={}, profile=dict(server_heap_mib=384,
                client_heap_mib=512, capture_width=854, capture_height=480, graphics_backend="opengl")))
            validation = root / "validation.json"
            atomic_json(validation, dict(passed=True, tests_passed=154, implementation_sha256=current, runs=[str(root / str(i)) for i in range(8)]))
            with mock.patch("tools.continue_phase9.audit_run", return_value=dict(status="verified", episodes=[{}])):
                revision = continue_execution(campaign, cache, validation, "unit transport revision")
            self.assertEqual(revision["first_world"], 2)
            self.assertEqual(campaign.training_worlds(), 1)
            self.assertEqual(campaign.state["attempts"], [row])
            self.assertEqual(campaign.state["current_checkpoint"], checkpoint)
            self.assertEqual((campaign.folder / "seeds.json").read_bytes(), seeds)
            self.assertEqual(campaign.config["execution_revisions"][0]["implementation_sha256"], old_source)
            self.assertTrue((archive / "state.json").exists())
            self.assertTrue((campaign.folder / "attention/fix_request_resolved_revision_0002.json").exists())
            self.assertFalse((campaign.folder / "fix_request.json").exists())

    def test_continuous_readiness_retains_healthy_window_and_resets_on_pressure(self):
        now = [0]
        memory = [3500]
        free = [9000]
        thermal = [40]
        ready = ResourceReadiness("unit", lambda: thermal[0], clock=lambda: now[0],
            memory=lambda: SimpleNamespace(available=memory[0] * 1024**2),
            disk=lambda _: SimpleNamespace(free=free[0] * 1024**2))
        ready.sample()
        self.assertFalse(ready.readiness(1800)[0])
        now[0] = 30
        ready.sample()
        self.assertTrue(ready.readiness(1800)[0])
        # A second launch reuses healthy history; no thresholds are reduced.
        now[0] = 45
        ready.sample()
        self.assertTrue(ready.readiness(1800)[0])
        memory[0] = 2500
        ready.sample()
        self.assertTrue(ready.readiness(1800)[0])
        self.assertFalse(ready.readiness(3000)[0])
        for metric in (memory, free, thermal):
            old = metric[0]
            metric[0] = 1700 if metric is memory else 2000 if metric is free else 75
            ready.sample()
            self.assertFalse(ready.readiness(1800)[0])
            metric[0] = old
            now[0] += 1
            ready.sample()
            self.assertFalse(ready.readiness(1800)[0])
            now[0] += 30
            ready.sample()
            self.assertTrue(ready.readiness(1800)[0])
        now[0] += 6
        self.assertFalse(ready.readiness(1800)[0], "stale telemetry cannot authorize launch")

    def cache(self, root):
        folder = root / "cache"
        folder.mkdir()
        java = root / "java.fixture"
        java.write_bytes(b"UNIT EXECUTABLE MARKER, NOT JAVA")
        dependency = root / "dependency.jar"
        dependency.write_bytes(b"UNIT DEPENDENCY MARKER, NOT A JAR")
        config = root / "launch.cfg"
        config.write_text("commonProperties\n")
        for task in ("runServer", "runClient"):
            (folder / (task + ".json")).write_text(json.dumps(dict(schema=1, executable=str(java),
                arguments=["-Dfabric.dli.config=" + str(config), "-cp", str(dependency), "UnitMain", "nogui"])))
        settings = dict(server_heap_mib=384, client_heap_mib=512, capture_width=854, capture_height=480, graphics_backend="opengl")
        ref = freeze_cache(folder, root, settings)
        return ref, java, dependency, SimpleNamespace(**settings, headless=True, spectator=False)

    def test_cached_command_retains_export_and_rejects_artifact_source_or_profile_changes(self):
        for damage in (None, "dependency", "source", "profile", "manifest"):
            with self.subTest(damage=damage), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                ref, java, dependency, args = self.cache(root)
                if damage == "dependency":
                    dependency.write_bytes(b"modified")
                elif damage == "source":
                    (root / "minecraft_bridge.py").write_text("# modified\n")
                elif damage == "profile":
                    args.server_heap_mib = 512
                elif damage == "manifest":
                    Path(ref["path"]).write_text("{}")
                if damage:
                    with self.assertRaises(ValueError):
                        cached_commands(ref["path"], ref["sha256"], root, args, root / "launch", java)
                else:
                    before = Path(ref["path"]).parent.joinpath("runServer.json").read_bytes()
                    commands = cached_commands(ref["path"], ref["sha256"], root, args, root / "launch", java)
                    self.assertEqual(set(commands), {"server"})
                    self.assertEqual(Path(ref["path"]).parent.joinpath("runServer.json").read_bytes(), before)
                    self.assertIn("nogui", (root / "launch/server.args").read_text())
                    args.spectator = True
                    self.assertEqual(set(cached_commands(ref["path"], ref["sha256"], root, args, root / "filmed", java)), {"server", "client"})

    def test_revision_rejects_actor_or_scoring_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "archive"
            original = "Files.move(temporary, controlFile, StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE);\n"
            for base in (root, archive / "source"):
                (base / HARNESS).parent.mkdir(parents=True, exist_ok=True)
                (base / HARNESS).write_text(original)
            previous = source_manifest(root)
            (root / HARNESS).write_text("AtomicFiles.replace(temporary, controlFile);\n")
            self.assertEqual(check_transport_changes(previous, source_manifest(root), archive, root), [HARNESS])
            (root / HARNESS).write_text("// altered scoring\nAtomicFiles.replace(temporary, controlFile);\n")
            with self.assertRaisesRegex(ValueError, "harness"):
                check_transport_changes(previous, source_manifest(root), archive, root)
            (root / HARNESS).write_text("AtomicFiles.replace(temporary, controlFile);\n")
            (root / "autonomy").mkdir()
            (root / "autonomy/agent.py").write_text("# altered policy\n")
            with self.assertRaisesRegex(ValueError, "transport/launcher"):
                check_transport_changes(previous, source_manifest(root), archive, root)
