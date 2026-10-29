"""Durable episode bookkeeping; never supplies seeds or scoring labels to policy."""

import hashlib
import json
import os
from pathlib import Path
import time

import psutil
import numpy as np

from .agent import AutonomousAgent
from learning import NeuralFeatureTable
from tools.milestone_video import MILESTONES

SPLITS = ("pilot", "training", "eval_a", "eval_b")
CONDITIONS = ("trained", "frozen", "uniform", "no_neural", "shuffled")
RESOURCE_GOALS = {"one_log": ("log", 1), "planks": ("planks", 4)}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source_manifest(root):
    root = Path(root)
    files = [root / "minecraft_bridge.py", root / "minecraft_mod/build.gradle", root / "requirements.txt"]
    for folder in ("autonomy", "learning", "simulator", "interface", "minecraft_mod/src", "tools"):
        files.extend(p for p in (root / folder).rglob("*") if p.is_file() and p.suffix in {".py", ".java", ".json", ".png", ".lua"})
    hashes = {p.relative_to(root).as_posix(): digest(p) for p in sorted(set(files)) if p.is_file()}
    return {"implementation_sha256": hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest(), "files": hashes}


def replace_file(temporary, path):
    """Windows readers may briefly deny replacement; retain the old full frame."""
    deadline = time.monotonic() + 1
    while True:
        try:
            os.replace(temporary, path)
            return
        except PermissionError:
            if time.monotonic() >= deadline:
                raise
            time.sleep(.01)


def atomic_json(path, data):
    path = Path(path)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(data, handle, indent=2, allow_nan=False)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    replace_file(temporary, path)


def seed_catalog(master, *, training=10000, pilot=100, evaluation=100):
    """Versioned SHA256 derivation, not dependent on Python RNG implementation."""
    used = {44556777, 44556778, 44556779}  # historical development worlds
    result = {"schema": 1, "master": int(master), "derivation": "sha256-v1-signed63"}
    for split, count in (("pilot", pilot), ("training", training), ("eval_a", evaluation), ("eval_b", evaluation)):
        if count < 1:
            raise ValueError("seed partitions must be nonempty")
        rows, nonce = [], 0
        while len(rows) < count:
            value = int.from_bytes(hashlib.sha256(f"FlyCraft-phase9-v1:{master}:{split}:{nonce}".encode()).digest()[:8], "big") & ((1 << 63) - 1)
            nonce += 1
            if value not in used:
                used.add(value)
                rows.append(value)
        result[split] = rows
    return result


def checkpoint_info(path, table):
    path = Path(path).resolve()
    agent, _ = AutonomousAgent.load(path, table)
    if not np.isfinite(agent.policy.weights).all():
        raise ValueError("nonfinite checkpoint weights")
    return {"path": str(path), "sha256": digest(path)}, agent


def verified_terminal_inventory(results, score, outcome):
    """Validate a terminal result or an acknowledged boundary in the raw log.

    Older controllers can emit an early evaluation success before writing the
    terminal field. Never synthesize it from the success flag or rerun actions.
    Training still requires its checkpoint's ordinary terminal result.
    """
    if "terminal_inventory" in outcome:
        return outcome["terminal_inventory"], "controller_result"
    if score.get("train") or outcome.get("train"):
        raise ValueError("training result lacks sealed terminal inventory")
    proofs = []
    for line in (Path(results) / "bridge.jsonl").read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        request = row["request"]
        if isinstance(request, str):
            request = json.loads(request)
        control, response = request.get("control", {}), row.get("response", {})
        terminal = control.get("terminal")
        if not terminal or control.get("episode_id") != score["episode_id"]:
            continue
        tick = terminal.get("server_tick")
        if control.get("active") is not False or type(tick) is not int or tick < 0 \
                or request.get("tick_id", -1) < tick or response.get("status") != "ok" \
                or response.get("episode_id") != score["episode_id"] \
                or response.get("terminal_acknowledged") is not True:
            continue
        inventory = terminal["inventory"]
        if any(inventory.get(key) != value for key, value in score["inventory"].items()):
            raise ValueError("acknowledged boundary inventory differs from server score")
        proofs.append((tick, inventory))
    if not proofs or any(proof != proofs[0] for proof in proofs[1:]):
        raise ValueError("missing or inconsistent acknowledged terminal inventory evidence")
    return dict(proofs[0][1]), "acknowledged_bridge_boundary"


class CampaignLock:
    """OS-backed exclusion; process death releases ownership automatically."""
    def __init__(self, folder):
        self.path = Path(folder) / "coordinator.lock"

    def __enter__(self):
        self.handle = self.path.open("a+b")
        if self.handle.seek(0,2) == 0:
            self.handle.write(b"\0"); self.handle.flush()
        self.handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(self.handle.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(self.handle.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError as error:
            self.handle.close()
            raise RuntimeError("campaign or Minecraft worker already has a live owner") from error
        self.handle.seek(0); self.handle.truncate()
        self.handle.write(json.dumps({"pid":os.getpid(),"created":psutil.Process().create_time()}).encode())
        self.handle.flush()
        return self

    def __exit__(self, *unused):
        self.handle.seek(0)
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(self.handle.fileno(),msvcrt.LK_UNLCK,1)
        else:
            import fcntl
            fcntl.flock(self.handle.fileno(),fcntl.LOCK_UN)
        self.handle.close()


class Campaign:
    def __init__(self, folder, *, project_root, table=None):
        self.folder, self.root = Path(folder).resolve(), Path(project_root).resolve()
        self.config = json.loads((self.folder / "config.json").read_text())
        self.catalog = json.loads((self.folder / "seeds.json").read_text())
        if digest(self.folder / "seeds.json") != self.config["catalog_sha256"]:
            raise ValueError("seed catalog integrity mismatch")
        self.state = json.loads((self.folder / "state.json").read_text())
        if digest(self.folder / "config.json") != self.state["config_sha256"]:
            raise ValueError("frozen campaign configuration changed")
        self.table = table or NeuralFeatureTable.from_phase35(self.root / "experiments/phase35/results/rate_decoder_evaluation.json")
        self.check_current()

    @classmethod
    def create(cls, folder, *, project_root, name, checkpoint, master=20261029, worlds=100, table=None, compact=False, frozen_checkpoint=None, forward_ticks=5, recording_policy="all", recording_milestones=None, goal="one_log"):
        if not name or len(name) > 36 or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for c in name):
            raise ValueError("campaign name must be a simple identifier up to 36 characters")
        if not 1 <= worlds <= 100:
            raise ValueError("development campaigns permit 1-100 worlds; official launch is not enabled")
        if goal not in RESOURCE_GOALS:
            raise ValueError("only the implemented one-log and plank interactions are enabled")
        if not isinstance(forward_ticks, int) or isinstance(forward_ticks, bool) or not 1 <= forward_ticks <= 10:
            raise ValueError("forward duration must be an integer from 1 to 10 ticks")
        if recording_policy not in ("all", "milestones"):
            raise ValueError("unknown recording policy")
        milestones = tuple(MILESTONES if recording_milestones is None else recording_milestones)
        if not milestones or any(type(n) is not int or not 1 <= n <= 10000 for n in milestones) or len(set(milestones)) != len(milestones):
            raise ValueError("recording milestones must be unique episode numbers from 1 to 10000")
        folder, root = Path(folder).resolve(), Path(project_root).resolve()
        table = table or NeuralFeatureTable.from_phase35(root / "experiments/phase35/results/rate_decoder_evaluation.json")
        initial, _ = checkpoint_info(checkpoint, table)
        frozen, _ = checkpoint_info(frozen_checkpoint or checkpoint, table)
        folder.mkdir(parents=True, exist_ok=False)
        atomic_json(folder / "seeds.json", seed_catalog(master))
        manifest = source_manifest(root)
        atomic_json(folder / "source_manifest.json", manifest)
        config = {"schema": 1, "name": name, "stage": "development", "world_limit": worlds,
                  "goal": goal, "curriculum_level": 1, "initial_checkpoint": initial,
                  "frozen_checkpoint": frozen,
                  "catalog_sha256": digest(folder / "seeds.json"), "created_unix": time.time(),
                  "implementation_sha256": manifest["implementation_sha256"],
                  "recording_policy": recording_policy, "recording_milestones": sorted(milestones),
                  "runtime_profile": {"server_heap_mib": 384 if compact else 512,
                                      "client_heap_mib": 512 if compact else 768,
                                      "forward_ticks": forward_ticks,
                                      "width": 854 if compact else 1280, "height": 480 if compact else 720},
                  "final_policy": None, "official_experiment_authorized": False}
        atomic_json(folder / "config.json", config)
        atomic_json(folder / "state.json", {"schema": 1, "config_sha256": digest(folder / "config.json"),
                    "current_checkpoint": initial, "active_attempt": None, "attempts": [], "final_policy": None})
        return cls(folder, project_root=root, table=table)

    def save(self):
        atomic_json(self.folder / "state.json", self.state)
        atomic_json(self.folder / "summary.json", self.summary())

    def check_current(self):
        expected = self.state["current_checkpoint"]
        if digest(expected["path"]) != expected["sha256"]:
            raise ValueError("committed checkpoint integrity mismatch")

    def begin(self, split="pilot", condition="trained", *, runtime_root=None):
        if self.state["active_attempt"] is not None:
            raise RuntimeError("recover the interrupted attempt before starting another")
        if split not in ("pilot", "eval_a", "eval_b") or condition not in CONDITIONS:
            raise ValueError("unsupported development split/condition")
        if split == "pilot" and condition != "trained":
            raise ValueError("pilot training must use the trained policy")
        if split == "pilot" and sum(a["generated_world_instances"] or 0 for a in self.state["attempts"] if a["split"] == "pilot") >= self.config["world_limit"]:
            raise ValueError("development world-instance limit reached, including interrupted worlds")
        if self.state["final_policy"] is not None and split == "pilot":
            raise ValueError("training is frozen after final policy selection")
        if split == "eval_b" and self.state["final_policy"] is None:
            raise ValueError("select and freeze the final policy before using eval_b")
        if source_manifest(self.root)["implementation_sha256"] != self.config["implementation_sha256"]:
            raise ValueError("implementation changed; start a new development campaign")
        self.check_current()
        checkpoint = self.state["final_policy"] if split == "eval_b" else self.state["current_checkpoint"]
        if condition == "frozen":
            checkpoint = self.config.get("frozen_checkpoint", self.config["initial_checkpoint"])
        completed = [a for a in self.state["attempts"] if a["status"] == "committed" and a["split"] == split and a["condition"] == condition
                     and (split != "eval_a" or a["checkpoint"]["sha256"] == checkpoint["sha256"])]
        index = len(completed)
        limit = self.config["world_limit"] if split == "pilot" else len(self.catalog[split])
        if index >= limit:
            raise ValueError("split is complete; its worlds cannot be evaluated again")
        if digest(checkpoint["path"]) != checkpoint["sha256"]:
            raise ValueError("selected checkpoint integrity mismatch")
        attempt = {"number": len(self.state["attempts"]) + 1, "episode_number": index + 1,
                   "run_id": f"{self.config['name']}_{split}_{condition}_{index+1:05d}_a{len(self.state['attempts'])+1:04d}",
                   "split": split, "condition": condition, "world_seed": self.catalog[split][index],
                   "layout_seed": self.catalog[split][index], "policy_seed": 9001 + index,
                   "goal": self.config["goal"], "train": split == "pilot", "checkpoint": dict(checkpoint),
                   "status": "running", "started_unix": time.time(), "generated_world_instances": None}
        attempt["video_required"] = (self.config.get("recording_policy", "all") == "all"
                                     or index + 1 in self.config.get("recording_milestones", MILESTONES))
        attempt["runtime"] = str(Path(runtime_root).resolve() / attempt["run_id"]) if runtime_root else None
        self.state["attempts"].append(attempt)
        self.state["active_attempt"] = len(self.state["attempts"]) - 1
        self.save()
        return dict(attempt)

    def recover(self):
        """Commit complete evidence once; otherwise preserve an interrupted attempt."""
        index = self.state["active_attempt"]
        if index is None:
            return None
        attempt = self.state["attempts"][index]
        if attempt.get("worker_pid"):
            try:
                if abs(psutil.Process(attempt["worker_pid"]).create_time()-attempt["worker_created"])<.01:
                    raise RuntimeError("worker is still alive; wait for safe shutdown before recovery")
            except psutil.NoSuchProcess:
                pass
        if attempt.get("runtime"):
            attempt["generated_world_instances"] = int((Path(attempt["runtime"]) / "server/world/level.dat").is_file())
        results = self.root / "experiments/phase9" / attempt["run_id"]
        try:
            run = json.loads((results / "run.json").read_text())
            attempt["generated_world_instances"] = run.get("generated_world_instances", 0)
            if run["stop_reason"] != "suite_complete" or run["completed"] != 1:
                raise ValueError("worker did not complete exactly one episode")
            video_required = attempt.get("video_required", True)
            if not run.get("server_exited_cleanly") or video_required and not run.get("client_exited_cleanly"):
                raise ValueError("game process did not exit cleanly")
            if run["checkpoint_sha256"] != attempt["checkpoint"]["sha256"] or digest(attempt["checkpoint"]["path"]) != attempt["checkpoint"]["sha256"]:
                raise ValueError("input checkpoint changed")
            if run["world_seed"] != attempt["world_seed"] or run["train"] != attempt["train"]:
                raise ValueError("worker configuration differs from planned attempt")
            if run["implementation_sha256"] != self.config["implementation_sha256"]:
                raise ValueError("worker implementation differs from frozen campaign")
            scores = [json.loads(line) for line in (results / "server.jsonl").read_text().splitlines()]
            outcomes = [json.loads(line) for line in (results / "controller.jsonl").read_text().splitlines()]
            delivery = [json.loads(line) for line in (results / "server.jsonl.delivery.jsonl").read_text().splitlines()]
            if len(scores) != 1 or len(outcomes) != 1 or len(delivery) != 1 or not delivery[0]["acknowledged"]:
                raise ValueError("incomplete or duplicate episode evidence")
            score, outcome = scores[0], outcomes[0]
            if delivery[0].get("episode_id") != score["episode_id"]:
                raise ValueError("terminal delivery belongs to another episode")
            if score["success"] != outcome["success"] or score["episode_id"] != outcome["episode_id"]:
                raise ValueError("controller and Minecraft scoring disagree")
            item, count = RESOURCE_GOALS[attempt["goal"]]
            if score.get("goal", attempt["goal"]) != attempt["goal"]:
                raise ValueError("Minecraft scored a different goal")
            if score["success"] != (score["inventory"][item] >= count) or score["layout_seed"] != attempt["layout_seed"]:
                raise ValueError("score differs from inventory goal or planned layout")
            terminal_inventory, terminal_source = verified_terminal_inventory(results, score, outcome)
            if any(terminal_inventory.get(key) != value for key,value in score["inventory"].items()):
                raise ValueError("terminal inventory mismatch")
            if not attempt["train"] and (score["train"] or outcome["train"] or outcome["update"]["weight_delta_norm"] != 0):
                raise ValueError("evaluation attempted learning")
            video = run.get("milestone_video")
            if video_required:
                video = video or {}
                if run.get("milestone_video_status") != "verified" or not video.get("episode_coverage_complete") or not video.get("visual_content_preflight_verified"):
                    raise ValueError("verified milestone MP4 is missing")
                if digest(video["path"]) != video["sha256"]:
                    raise ValueError("episode MP4 integrity mismatch")
            elif run.get("headless") is not True or run.get("spectator") is not False \
                    or run.get("recording_mode") != "structured_event_logs_no_video" \
                    or run.get("milestone") is not None or run.get("recording") is not None:
                raise ValueError("routine episode differs from planned headless event-only execution")
            next_checkpoint = self.state["current_checkpoint"]
            if attempt["train"] and outcome["train"]:
                path = self.root / "checkpoints/phase9" / attempt["run_id"] / "trial_0000.npz"
                next_checkpoint, restored = checkpoint_info(path, self.table)
                if not restored.session["done"] or restored.session["success"] != score["success"]:
                    raise ValueError("checkpoint session differs from scored episode")
                previous, _ = checkpoint_info(attempt["checkpoint"]["path"], self.table)
                before_agent, _ = AutonomousAgent.load(previous["path"], self.table)
                delta = float(np.linalg.norm(restored.policy.weights-before_agent.policy.weights))
                if not np.isclose(delta,outcome["update"]["weight_delta_norm"],rtol=1e-9,atol=1e-12):
                    raise ValueError("saved readout update differs from reported weight change")
            attempt.update(status="committed", finished_unix=time.time(), success=score["success"],
                           ticks=score["ticks"], actions=outcome["actions"], total_reward=outcome["total_reward"],
                           update=outcome["update"], training_applied=bool(outcome["train"] and outcome["update"]["weight_delta_norm"]>0),
                           terminal_unattributed_reward=outcome.get("unattributed_terminal_reward", 0),
                           training_suppressed=outcome.get("training_suppressed"),
                           termination=outcome["termination"], results=str(results), video=video,
                           terminal_inventory_source=terminal_source,
                           wall_seconds=run["elapsed_seconds"], checkpoint_after=next_checkpoint,
                           implementation_sha256=run["implementation_sha256"])
            self.state["current_checkpoint"] = next_checkpoint
        except (OSError, ValueError, KeyError) as error:
            attempt.update(status="interrupted", finished_unix=time.time(), error=str(error), results=str(results))
        self.state["active_attempt"] = None
        self.save()
        return dict(attempt)

    def freeze_final(self):
        if self.state["active_attempt"] is not None:
            raise ValueError("finish active episode before final policy selection")
        if self.state["final_policy"] is not None:
            raise ValueError("final policy was already frozen")
        self.check_current()
        self.state["final_policy"] = dict(self.state["current_checkpoint"])
        self.save()

    def amend_validation_only(self, reason):
        """Audited development repair, never a policy/runtime configuration thaw.

        Only the result validator module may differ. Immutable snapshots retain
        every previous configuration, source manifest and state. No active job,
        training history or final benchmark is eligible for this narrow repair.
        """
        if not reason or self.state["active_attempt"] is not None or self.state["final_policy"] is not None \
                or any(a["train"] or a["split"] == "eval_b" for a in self.state["attempts"]):
            raise ValueError("validation amendment requires idle development evaluation only")
        previous = json.loads((self.folder / "source_manifest.json").read_text())
        current = source_manifest(self.root)
        changed = sorted(key for key in previous["files"].keys() | current["files"].keys()
                         if previous["files"].get(key) != current["files"].get(key))
        if changed != ["autonomy/experiment.py"]:
            raise ValueError("only the result validator may change; actor, controller, runner and policy must stay frozen")
        archive = self.folder / "validation_revisions" / f"revision_{len(self.state.get('validation_revisions', []))+1:04d}"
        archive.mkdir(parents=True, exist_ok=False)
        for name, value in (("config.json", self.config), ("source_manifest.json", previous), ("state.json", self.state)):
            atomic_json(archive / name, value)
        revision = {"created_unix": time.time(), "reason": reason, "changed_files": changed,
                    "previous_source_sha256": self.config["implementation_sha256"],
                    "source_sha256": current["implementation_sha256"], "archive": str(archive)}
        atomic_json(archive / "amendment.json", revision)
        self.config["implementation_sha256"] = current["implementation_sha256"]
        atomic_json(self.folder / "source_manifest.json", current)
        atomic_json(self.folder / "config.json", self.config)
        self.state["config_sha256"] = digest(self.folder / "config.json")
        self.state.setdefault("validation_revisions", []).append(revision)
        self.save()
        return revision

    def summary(self):
        attempts = self.state["attempts"]
        committed = [a for a in attempts if a["status"] == "committed"]
        training = [a for a in committed if a["train"]]
        recent = training[-20:]
        finished_training = [a for a in attempts if a["split"]=="pilot" and a.get("finished_unix") is not None]
        seconds = sum(a.get("wall_seconds",a["finished_unix"]-a["started_unix"]) for a in finished_training)
        rate = len(training) / seconds if seconds else None
        generated_training=sum(a["generated_world_instances"] or 0 for a in attempts if a["split"]=="pilot")
        remaining=max(0,self.config["world_limit"]-generated_training)
        attempt_seconds=seconds/len(finished_training) if finished_training else None
        return {"stage": "development", "official_training_worlds": 0,
                "generated_world_instances": sum(a["generated_world_instances"] or 0 for a in attempts),
                "unverified_world_counts": sum(a["generated_world_instances"] is None for a in attempts),
                "distinct_generated_seeds": len({a["world_seed"] for a in attempts if a["generated_world_instances"]}),
                "committed_episodes": len(committed), "training_episodes": len(training),
                "training_updates": sum(a["training_applied"] for a in training),
                "evaluation_episodes": len(committed)-len(training),
                "recording_policy": self.config.get("recording_policy", "all"),
                "recorded_episodes": sum(a.get("video_required", True) for a in committed),
                "event_only_episodes": sum(not a.get("video_required", True) for a in committed),
                "recent_training_success_rate": sum(a["success"] for a in recent)/len(recent) if recent else None,
                "mean_training_reward": sum(a["total_reward"] for a in recent)/len(recent) if recent else None,
                "measured_training_worlds_per_hour": rate*3600 if rate else None,
                "mean_actions_per_success": sum(a["actions"] for a in recent if a["success"])/sum(a["success"] for a in recent) if any(a["success"] for a in recent) else None,
                "estimated_remaining_seconds": remaining*attempt_seconds if attempt_seconds is not None else None,
                "estimate_basis": "remaining generated-world slots times measured attempt wall time; interruptions included",
                "curriculum_level": 1, "goal": self.config["goal"], "progression": "operator-selected interaction goal; no automatic curriculum advancement",
                "checkpoint": self.state["current_checkpoint"], "active_attempt": self.state["active_attempt"],
                "recent_errors": [a.get("error") for a in attempts if a["status"] == "interrupted"][-5:],
                "updated_unix": time.time()}
