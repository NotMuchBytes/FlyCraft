"""Explicit curriculum revision; original wood campaign remains immutable.

Only terrain/exploration and wood retention are executable in this revision.
Later skills are reserved, not silently replaced with more wood episodes.
"""
import json
import math
from pathlib import Path
import time

from .agent import AutonomousAgent
from .experiment import Campaign, CONDITIONS, RESOURCE_GOALS, atomic_json, checkpoint_info, digest, seed_catalog, source_manifest
from learning import NeuralFeatureTable

SCHEMA = "staged-terrain-v1"
STAGES = (
    {"id": "terrain", "training_worlds": 64, "terrain_step_fixture": True, "natural_world": False},
    {"id": "exploration", "training_worlds": 128, "terrain_step_fixture": False, "natural_world": True},
)
PENDING = ("stone_tools", "food_and_shelter", "mining_and_survival", "combat", "nether_and_progression")


def reference_start(attempts, *, stage, index, seed):
    """Reuse only an observed own pose from the first matched condition."""
    rows = [a for a in attempts if a.get("curriculum_stage") == stage and a["split"] == "eval_a"
            and a.get("evaluation_task") == "primary" and a["condition"] == "trained"
            and a.get("evaluation_index") == index and a["status"] == "committed"]
    if len(rows) != 1 or rows[0]["world_seed"] != seed:
        raise ValueError("matched natural control needs its completed trained reference")
    initial = [json.loads(line) for line in (Path(rows[0]["results"]) / "server.jsonl.initial.jsonl").read_text().splitlines()]
    if len(initial) != 1 or initial[0].get("world_seed") != seed or initial[0].get("game_mode") != "SURVIVAL":
        raise ValueError("ambiguous or mismatched natural starting-pose evidence")
    pose = initial[0].get("position_xyz_yaw_pitch")
    if not isinstance(pose, list) or len(pose) != 5 or any(type(v) not in (int, float) or not math.isfinite(v) for v in pose):
        raise ValueError("invalid natural reference pose")
    if any(initial[0]["inventory"].values()):
        raise ValueError("natural reference inventory was not empty")
    return list(pose)


def gate_report(attempts, stage):
    """Thirty untouched primary seeds, all five controls, plus retention."""
    rows = [a for a in attempts if a.get("curriculum_stage") == stage and a["split"] == "eval_a" and a["status"] == "committed"]
    cells = {(a["evaluation_task"], a["condition"], a["evaluation_index"]): a for a in rows}
    required = [("primary", c, i) for i in range(30) for c in CONDITIONS] + [("retention", "trained", i) for i in range(30)]
    complete = len(rows) == len(cells) == len(required) and all(k in cells for k in required)
    scores = {c: sum(a["success"] for a in rows if a["evaluation_task"] == "primary" and a["condition"] == c) for c in CONDITIONS}
    retention = sum(a["success"] for a in rows if a["evaluation_task"] == "retention")
    return dict(complete=complete, primary_successes=scores, retention_successes=retention,
                trials_per_condition=30, minimum_successes=24,
                passed=complete and scores["trained"] >= 24 and retention >= 24)


class StagedCampaign(Campaign):
    @classmethod
    def create_from_foundation(cls, folder, *, project_root, handoff, cache, authorization, master=2026112507):
        root, folder, handoff = Path(project_root).resolve(), Path(folder).resolve(), Path(handoff).resolve()
        if not folder.name or len(folder.name) > 24 or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for c in folder.name):
            raise ValueError("curriculum name must be a simple identifier up to 24 characters")
        foundation = json.loads(handoff.read_text())
        if foundation["world_budget_total"] != 10000 or foundation["foundation_world_instances"] != 338:
            raise ValueError("unexpected foundation lineage; review before creating plan")
        for name, sha in foundation["files"].items():
            if digest(handoff.parent / name) != sha:
                raise ValueError("foundation evidence changed")
        if not authorization or digest(foundation["checkpoint"]["path"]) != foundation["checkpoint"]["sha256"]:
            raise ValueError("explicit authorization and intact foundation checkpoint required")
        table = NeuralFeatureTable.from_phase35(root / "experiments/phase35/results/rate_decoder_evaluation.json")
        folder.mkdir(parents=True, exist_ok=False)
        agent, _ = AutonomousAgent.load(foundation["checkpoint"]["path"], table)
        agent.enable_live_terrain()
        migrated = folder / "foundation_terrain_transfer.npz"
        agent.save(migrated, extension={"foundation": foundation["checkpoint"], "transfer_prior": "jump copies forward logits with grounded log(4) penalty; new observations zero for old actions"})
        initial, _ = checkpoint_info(migrated, table)
        old_catalog = json.loads((handoff.parent / "seeds.json").read_text())
        excluded = {n for k, values in old_catalog.items() if k in ("training", "pilot", "eval_a", "eval_b") for n in values}
        for path in (root / "experiments/phase9").glob("*/run.json"):
            run = json.loads(path.read_text())
            excluded.add(run["world_seed"])
            excluded.update(run.get("layout_seeds") or [])
            if type(run.get("layout_start")) is int:
                excluded.add(run["layout_start"])
        catalog = seed_catalog(master, training=9662, pilot=100, evaluation=300, exclude=excluded)
        atomic_json(folder / "seeds.json", catalog)
        manifest = source_manifest(root)
        atomic_json(folder / "source_manifest.json", manifest)
        profile = dict(server_heap_mib=384, client_heap_mib=512, width=854, height=480,
            pitch_actions=True, terrain_actions=True, turn_degrees=15, forward_ticks=8,
            trial_ticks=1200, three_tree_fixture=False, remember_mined_columns=False,
            terrain_step_fixture=True, natural_world=False,
            launch_cache=dict(path=str(Path(cache).resolve()), sha256=digest(cache)))
        config = dict(schema=4, curriculum_schema=SCHEMA, name=folder.name, stage="official_training",
            official_experiment_authorized=True, authorization=authorization, world_limit=10000,
            foundation=foundation, foundation_handoff=dict(path=str(handoff), sha256=digest(handoff)),
            initial_checkpoint=initial, frozen_checkpoint=initial, automatic_final_evaluation=False,
            catalog_sha256=digest(folder / "seeds.json"), implementation_sha256=manifest["implementation_sha256"],
            runtime_profile=profile, goal="one_log", goal_schedule=list(RESOURCE_GOALS),
            supported_stages=list(STAGES), pending_skills=list(PENDING),
            recording_policy="milestones", recording_milestones=[339, 350, 400, 500, 1000, 2500, 5000, 7500, 10000],
            world_budget_definition="338 preserved foundation instances plus new training worlds, including aborted instances; evaluation separate",
            checker=dict(schema=1, graph=dict(path=str(root / "data/processed/connectome_raw_csr.npz"), sha256=digest(root / "data/processed/connectome_raw_csr.npz")),
                launch_ram_mib=1800, recording_launch_ram_mib=3000, readiness_mode="continuous",
                failure_window=10, failure_limit=9, technical_retries=2, automatic_code_changes=False),
            created_unix=time.time())
        atomic_json(folder / "config.json", config)
        atomic_json(folder / "state.json", dict(schema=2, config_sha256=digest(folder / "config.json"),
            current_checkpoint=initial, final_policy=None, active_attempt=None, attempts=[], curriculum_index=0,
            stage_checkpoints={}, gates={}, status="ready"))
        result = cls(folder, project_root=root, table=table)
        result.save()
        return result

    def training_worlds(self):
        return self.config["foundation"]["foundation_world_instances"] + super().training_worlds()

    def runtime_profile(self, goal):
        active = self.state["active_attempt"]
        if active is not None:
            return self.state["attempts"][active]["profile"]
        return self.config["runtime_profile"]

    def environment_expectation(self, profile):
        kind = "vanilla_overworld_spawn" if profile["natural_world"] else "controlled_terrain_step_teaching_fixture" if profile["terrain_step_fixture"] else "controlled_flat_three_tree_fixture" if profile["three_tree_fixture"] else "controlled_flat_survival_fixture"
        return dict(terrain_actions=True, environment_kind=kind, natural_start_requested=profile.get("natural_start"))

    def next_cell(self):
        if self.state["active_attempt"] is not None:
            raise RuntimeError("recover active worker first")
        index = self.state["curriculum_index"]
        if index >= len(self.config["supported_stages"]):
            self.state["status"] = "awaiting_next_skill_implementation"
            self.save()
            return None
        stage = self.config["supported_stages"][index]
        rows = [a for a in self.state["attempts"] if a["curriculum_stage"] == stage["id"]]
        trained = sum(a.get("generated_world_instances") or 0 for a in rows if a["split"] == "training")
        if trained < stage["training_worlds"] and self.training_worlds() < 10000:
            retention = trained % 4 == 3
            goal = list(RESOURCE_GOALS)[(trained // 4) % 4] if retention else "one_log"
            return dict(split="training", condition="trained", goal=goal, retention=retention)
        # Lock the candidate before touching any evaluation seed.
        if stage["id"] not in self.state["stage_checkpoints"]:
            self.state["stage_checkpoints"][stage["id"]] = dict(self.state["current_checkpoint"])
            self.save()
        if self.state["stage_checkpoints"][stage["id"]] != self.state["current_checkpoint"]:
            raise ValueError("candidate changed after held-out evaluation began")
        for task, conditions in (("primary", CONDITIONS), ("retention", ("trained",))):
            for n in range(30):
                for condition in conditions:
                    previous = [a for a in rows if a["split"] == "eval_a" and a["evaluation_task"] == task and a["condition"] == condition and a["evaluation_index"] == n]
                    # An incomplete cell is never silently rerun as a fresh score.
                    if previous and previous[-1]["status"] != "committed":
                        raise ValueError("incomplete evaluation cell requires explicit evidence review")
                    if not previous:
                        return dict(split="eval_a", condition=condition, goal="one_log", retention=task == "retention", evaluation_task=task, evaluation_index=n)
        gate = gate_report(rows, stage["id"])
        self.state["gates"][stage["id"]] = gate
        self.state["status"] = "stage_passed" if gate["passed"] else "stage_gate_failed"
        if gate["passed"]:
            self.state["curriculum_index"] += 1
        self.save()
        return self.next_cell() if gate["passed"] else None

    def begin_next(self, runtime_root):
        if source_manifest(self.root)["implementation_sha256"] != self.config["implementation_sha256"]:
            raise ValueError("curriculum implementation changed; preserve this plan and review a revision")
        self.check_current()
        if (self.folder / "STOP").exists() or (self.folder / "fix_request.json").exists():
            raise ValueError("curriculum is stopped or requires review")
        cell = self.next_cell()
        if cell is None:
            return None
        stage = self.config["supported_stages"][self.state["curriculum_index"]]
        train = cell["split"] == "training"
        own_worlds = self.training_worlds() - 338
        seed_index = own_worlds if train else self.state["curriculum_index"] * 60 + cell["evaluation_index"] + (30 if cell["retention"] else 0)
        seed = self.catalog["training" if train else "eval_a"][seed_index]
        checkpoint = self.config["frozen_checkpoint"] if cell["condition"] == "frozen" else self.state["current_checkpoint"]
        profile = dict(self.config["runtime_profile"])
        profile.update(terrain_step_fixture=stage["terrain_step_fixture"] and not cell["retention"], natural_world=stage["natural_world"] and not cell["retention"])
        if profile["natural_world"] and not train and cell["condition"] != "trained":
            profile["natural_start"] = reference_start(self.state["attempts"], stage=stage["id"],
                index=cell["evaluation_index"], seed=seed)
        if cell["retention"]:
            long = cell["goal"] in ("three_logs", "wooden_pickaxe")
            profile.update(trial_ticks=1500 if long else 400, forward_ticks=2, three_tree_fixture=long, remember_mined_columns=long)
        number = len(self.state["attempts"]) + 1
        run_id = f"{self.config['name']}_{stage['id']}_{number:05d}"
        official_number = self.training_worlds() + 1 if train else 0
        attempt = dict(cell, number=number, episode_number=official_number if train else number,
            run_id=run_id, curriculum_stage=stage["id"], profile=profile,
            world_seed=seed, layout_seed=seed, policy_seed=19001 + seed_index,
            train=train, checkpoint=dict(checkpoint), status="running", started_unix=time.time(),
            generated_world_instances=None, execution_revision=self.config.get("execution_revision", 1),
            experiment_stage="official_training" if train else "staged_curriculum_evaluation",
            implementation_sha256=self.config["implementation_sha256"], official_world_number=official_number,
            video_required=train and official_number in self.config["recording_milestones"],
            runtime=str(Path(runtime_root).resolve() / run_id))
        self.state["attempts"].append(attempt)
        self.state["active_attempt"] = len(self.state["attempts"]) - 1
        self.save()
        return dict(attempt)

    def summary(self):
        result = super().summary()
        total = self.training_worlds()
        result.update(curriculum_schema=SCHEMA, official_training_worlds=total,
            foundation_worlds=338, new_training_worlds=total-338, remaining_world_slots=10000-total,
            estimated_remaining_seconds=None, estimate_basis="broader skills are not yet implemented or timed",
            progression="64 terrain training worlds, locked 30-seed five-condition evaluation and retention gate; then 128 natural exploration worlds; later skills require validated implementation",
            curriculum_status=self.state["status"], curriculum_index=self.state["curriculum_index"], gates=self.state["gates"], pending_skills=self.config["pending_skills"])
        return result
