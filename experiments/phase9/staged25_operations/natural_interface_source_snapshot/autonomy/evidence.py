"""Independent checks of recorded Minecraft evidence. Never chooses actor actions."""

from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import subprocess

GOALS = {"one_log": ("log", 1), "three_logs": ("log", 3),
         "planks": ("planks", 4), "wooden_pickaxe": ("wooden_pickaxe", 1)}
TECHNICAL_STOPS = {"available_ram_guard", "free_disk_guard", "gpu_temperature_guard",
                   "wall_budget", "manual_stop", "coordinator_lost"}
RECIPES = {"planks": ("CRAFT_PLANKS",), "wooden_pickaxe": (
    "CRAFT_PLANKS", "CRAFT_STICKS", "CRAFT_TABLE", "PLACE_TABLE", "CRAFT_PICKAXE")}


class EvidenceError(ValueError):
    def __init__(self, code, detail, *, verified_episodes=None):
        self.code = code
        self.verified_episodes = verified_episodes or []
        super().__init__(f"{code}: {detail}")


def require(condition, code, detail):
    if not condition:
        raise EvidenceError(code, detail)


def file_sha256(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def records(path, *, required=True, interrupted=False):
    path = Path(path)
    if not path.exists() and not required:
        return []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise EvidenceError("missing_evidence", str(path)) from error
    result = []
    for index, line in enumerate(lines):
        try:
            value = json.loads(line)
            require(isinstance(value, dict), "malformed_evidence", str(path))
            result.append(value)
        except json.JSONDecodeError as error:
            # A killed writer can leave only its final append incomplete.
            if interrupted and index == len(lines) - 1:
                break
            raise EvidenceError("malformed_evidence", f"{path}:{index + 1}") from error
    return result


def indexed(rows, name):
    result = {}
    for row in rows:
        identity = row.get("episode_id")
        require(isinstance(identity, str) and identity, "episode_identity", name)
        require(identity not in result, "duplicate_episode", f"{name}/{identity}")
        result[identity] = row
    return result


def inventory(value):
    require(isinstance(value, dict) and value, "inventory", "missing inventory")
    require(all(type(n) is int and n >= 0 for n in value.values()), "inventory", "invalid item count")
    return value


def same_inventory(actual, expected):
    inventory(actual)
    return all(actual.get(key) == count for key, count in inventory(expected).items())


def verify_start_pose(meta, starts):
    requested = meta.get("natural_start_requested")
    if requested is None:
        return
    require(meta.get("environment_kind") == "vanilla_overworld_spawn"
            and isinstance(requested, list) and len(requested) == 5
            and all(type(v) in (int, float) and math.isfinite(v) for v in requested),
            "matched_start", "invalid requested natural pose")
    require(len(starts) == 1, "matched_start", "missing or ambiguous native start")
    actual = next(iter(starts.values())).get("position_xyz_yaw_pitch")
    require(isinstance(actual, list) and len(actual) == 5
            and all(type(a) in (int, float) and math.isfinite(a) and math.isclose(a,b,rel_tol=0,abs_tol=1e-4)
                    for a,b in zip(actual,requested)),
            "matched_start", "native starting pose differs from matched reference")


def _audit_run(directory, *, expected=None, verify_video=True):
    """Accept valid policy failures; reject contradictions and unexecuted success.

    Partial technical attempts retain all completed episode results. Callers
    must never retry a scored cell merely because its surrounding process died.
    Historical sources are checked against their own frozen manifest, not the
    current checkout. Inputs are evidence, never executable repair instructions.
    """
    directory = Path(directory).resolve()
    try:
        meta = json.loads((directory / "run.json").read_text(encoding="utf-8"))
        manifest = json.loads((directory / "source_manifest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise EvidenceError("missing_run_metadata", str(directory)) from error
    hashes = manifest["files"]
    manifest_hash = hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()
    require(manifest_hash == manifest["implementation_sha256"] == meta["implementation_sha256"],
            "source_manifest", directory.name)
    require(type(meta.get("train")) is bool and type(meta.get("world_seed")) is int,
            "metadata_schema", "invalid training mode or world seed")
    for key, value in (expected or {}).items():
        require(meta.get(key) == value, "configuration", f"{key}: {meta.get(key)!r} != {value!r}")
    require(meta.get("available_ram_guard_mib", 0) >= 768 and meta.get("free_disk_guard_mib", 0) >= 2048,
            "resource_guards", "required reserves were reduced")
    interrupted = meta["stop_reason"] != "suite_complete"
    scored = records(directory / "server.jsonl", required=not interrupted, interrupted=interrupted)
    require(len(scored) == meta["completed"], "episode_count", "metadata and raw scores disagree")
    require(type(meta["requested"]) is int and 0 <= len(scored) <= meta["requested"], "episode_count", "invalid requested count")
    if not interrupted:
        require(len(scored) == meta["requested"], "episode_count", "suite_complete omitted episodes")
    scores = indexed(scored, "server")
    controllers = indexed(records(directory / "controller.jsonl", required=bool(scored), interrupted=interrupted), "controller")
    starts = indexed(records(directory / "server.jsonl.initial.jsonl", required=bool(scored), interrupted=interrupted), "initial")
    if scored:
        verify_start_pose(meta, starts)
    deliveries = indexed(records(directory / "server.jsonl.delivery.jsonl", required=bool(scored), interrupted=interrupted), "delivery")
    if not interrupted:
        require(set(scores) == set(starts) == set(controllers) == set(deliveries),
                "episode_join", "completed suite contains orphaned or missing episode records")
    bridge = records(directory / "bridge.jsonl", required=bool(scored), interrupted=interrupted)
    events = records(directory / "headless.jsonl", required=bool(scored), interrupted=interrupted)
    commands, boundaries, intervention_commands, observed_acks = {}, {}, set(), {}
    for row in bridge:
        try:
            request = json.loads(row["request"]) if isinstance(row["request"], str) else row["request"]
            response = row.get("response") or {}
            episode = response.get("episode_id")
            if episode not in scores:
                continue
            control = request.get("control", {})
            if control.get("episode_id") != episode:
                require(not response.get("command_id") and not control.get("terminal"),
                        "training_control", str(episode))
                continue  # Observe-only lifecycle replies and end_suite do not select actions.
            require(control.get("episode_id") == episode and control.get("train") is meta["train"],
                    "training_control", str(episode))
            ack = request.get("ack")
            if ack and ack.get("command_id"):
                observed_acks.setdefault((episode, ack["command_id"]), []).append(ack)
            terminal = control.get("terminal")
            if terminal and response.get("terminal_acknowledged") is True:
                require(control.get("episode_id") == episode and control.get("active") is False
                        and response.get("status") == "ok" and type(terminal.get("server_tick")) is int
                        and request.get("tick_id", -1) >= terminal["server_tick"], "terminal_boundary", episode)
                proof = terminal["server_tick"], terminal["inventory"]
                require(episode not in boundaries or boundaries[episode] == proof, "terminal_boundary", episode)
                boundaries[episode] = proof
            command = response.get("command_id")
            if not command:
                continue
            require(type(command) is int and command > 0, "command_identity", str(command))
            key = episode, command
            require(key not in commands or commands[key] == response["action"], "command_identity", str(key))
            commands[key] = response["action"]
            if meta.get("terrain_actions"):
                telemetry = request["telemetry"]
                require(telemetry.get("terrain_observation_schema") == "visible-terrain-v1"
                        and not meta.get("jump_on_blocked_forward"), "terrain_interface", str(key))
                for field in ("health", "food"):
                    number = telemetry.get(field)
                    require(type(number) in (int, float) and math.isfinite(number) and 0 <= number <= 20,
                            "terrain_vitals", str(key))
                for field in ("on_ground", "obstacle_visible", "support_visible", "drop_visible", "water_visible"):
                    require(type(telemetry.get(field)) is bool, "terrain_visibility", str(key))
                require(response["action"] in telemetry["allowed_actions"], "terrain_legal_action", str(key))
            condition = scores[episode]["condition"]
            require(response["feature_mode"] == condition and response["neural_steps"] == 18,
                    "neural_intervention", str(key))
            raw = [response["neural_features"][key] for key in
                   ("bias", "left_readout_div50", "right_readout_div50", "total_readout_div50")]
            actual = [response["policy_neural_inputs"][key] for key in
                      ("bias", "left_input", "right_input", "total_input")]
            require(raw[0] == actual[0] == 1, "neural_intervention", "bias is not neural activity")
            target = [1., 0., 0., 0.] if condition == "no_neural" else (
                [raw[n] for n in (0, 3, 1, 2)] if condition == "shuffled" else raw)
            require(all(math.isfinite(a) and math.isfinite(b) and abs(a-b) <= 1e-12
                        for a, b in zip(actual, target)), "neural_intervention", str(key))
            probabilities = response["action_probabilities"]
            positive = [p for p in probabilities.values() if p > 0]
            require(positive and all(math.isfinite(p) and 0 <= p <= 1 for p in probabilities.values())
                    and abs(sum(positive)-1) < 1e-8, "policy_probabilities", str(key))
            if condition == "uniform":
                require(max(positive)-min(positive) <= 1e-12, "uniform_probabilities", str(key))
            intervention_commands.add(key)
        except (KeyError, TypeError, ValueError) as error:
            if isinstance(error, EvidenceError):
                raise
            raise EvidenceError("bridge_schema", str(directory)) from error
    ended = {}
    for row in events:
        if row.get("event") != "action_end" or row.get("episode_id") not in scores:
            continue
        ack = row["data"]["ack"]
        key = row["episode_id"], ack["command_id"]
        require(key not in ended, "duplicate_ack", str(key))
        require(commands.get(key) == ack["action"], "unissued_action", str(key))
        if ack["action"] == "JUMP_FORWARD":
            require(meta.get("terrain_actions") is True and ack.get("policy_selected_jump") is True
                    and ack.get("jump_assisted") is False, "jump_policy_selection", str(key))
            if ack["status"] == "success":
                require(ack.get("movement_confirmed") is True and ack.get("peak_vertical_displacement", 0) > .08,
                        "jump_physics", str(key))
        require(any(all(other.get(field) == ack.get(field) for field in ("action", "status", "block_changed"))
                    for other in observed_acks.get(key, [])), "ack_disagreement", str(key))
        ended[key] = ack
    episodes = []
    for identity, score in scores.items():
        require(identity in starts and identity in controllers and identity in deliveries,
                "episode_join", identity)
        start, controller = starts[identity], controllers[identity]
        require(deliveries[identity].get("acknowledged") is True and identity in boundaries,
                "terminal_acknowledgment", identity)
        require(not any(inventory(start["inventory"]).values()), "starting_inventory", identity)
        require(start["world_seed"] == meta["world_seed"] and start["layout_seed"] == score["layout_seed"]
                and start["goal"] == score["goal"], "seed_identity", identity)
        require(score["goal"] in meta["goals"] and score["condition"] in meta["conditions"]
                and controller["condition"] == score["condition"], "condition_identity", identity)
        require(score["condition"] in ("trained", "frozen", "uniform", "no_neural", "shuffled"),
                "condition_identity", identity)
        require(score["goal"] in GOALS, "goal", score["goal"])
        require(type(score["success"]) is bool and score["success"] == controller["success"]
                and controller["done"] is True, "success_agreement", identity)
        final = inventory(score["inventory"])
        require(same_inventory(boundaries[identity][1], final), "terminal_inventory", identity)
        if "terminal_inventory" in controller:
            require(same_inventory(controller["terminal_inventory"], final), "terminal_inventory", identity)
        else:
            require(not score["train"] and not controller["train"], "training_terminal", identity)
        item, count = GOALS[score["goal"]]
        require(score["success"] == (final.get(item, 0) >= count), "inventory_success", identity)
        require(type(score["ticks"]) is int and 0 <= score["ticks"] <= meta["trial_tick_limit"], "tick_budget", identity)
        require(type(controller["actions"]) is int and 0 <= controller["actions"] <= 120,
                "action_budget", identity)
        require(isinstance(controller.get("elapsed_seconds"), (int, float))
                and math.isfinite(controller["elapsed_seconds"]) and controller["elapsed_seconds"] >= 0,
                "elapsed_time", identity)
        delta = controller["update"]["weight_delta_norm"]
        require(math.isfinite(delta) and delta >= 0, "checkpoint_update", identity)
        require(score["train"] == meta["train"], "training_mode", identity)
        if not meta["train"]:
            require(controller["train"] is False and delta == 0, "evaluation_update", identity)
        elif not controller["train"]:
            require(bool(controller.get("training_suppressed")) and delta == 0, "suppressed_update", identity)
        completed = [ack for (ep, _), ack in ended.items() if ep == identity and ack["status"] == "success"]
        breaks = sum(ack["action"] == "COLLECT_LOG" and ack["block_changed"] is True for ack in completed)
        require(controller["confirmed_block_changes"] == breaks, "block_confirmation", identity)
        crafts = Counter(ack["action"] for ack in completed if ack["action"].startswith("CRAFT_")
                         or ack["action"] == "PLACE_TABLE" and ack["block_changed"] is True)
        if score["success"]:
            require(breaks >= (3 if score["goal"] in ("three_logs", "wooden_pickaxe") else 1),
                    "missing_block_break", identity)
            require(all(crafts[action] for action in RECIPES.get(score["goal"], ())), "missing_recipe", identity)
        failure = "success" if score["success"] else "break_without_enough_pickup" if breaks else "no_confirmed_break"
        if not score["success"] and score["goal"] == "wooden_pickaxe":
            for action in ("PLACE_TABLE", "CRAFT_TABLE", "CRAFT_STICKS", "CRAFT_PLANKS"):
                if crafts[action]:
                    failure = "stopped_after_" + action.lower()
                    break
        episodes.append({"episode_id": identity, "goal": score["goal"], "condition": score["condition"],
                         "layout_seed": score["layout_seed"], "success": score["success"],
                         "actions": controller["actions"], "game_seconds": score["ticks"]/20,
                         "elapsed_seconds": controller["elapsed_seconds"], "confirmed_breaks": breaks,
                         "crafts": dict(crafts), "failure_mode": failure, "inventory": final,
                         "weight_delta_norm": delta, "training_applied": bool(controller["train"] and delta > 0)})
    video_report = None
    if meta.get("milestone") is not None:
        try:
            video = meta.get("milestone_video") or {}
            require(meta.get("milestone_video_status") == "verified" and video.get("episode_coverage_complete")
                    and video.get("visual_content_preflight_verified") and meta.get("capture_content_proof", {}).get("matched"),
                    "milestone_capture", directory.name)
            require(file_sha256(video["path"]) == video["sha256"], "milestone_hash", directory.name)
            if verify_video:
                from tools.milestone_video import verify_mp4
                video_report = verify_mp4(video["path"], minimum_seconds=sum(row["game_seconds"] for row in episodes))
                require(video_report["sha256"] == video["sha256"], "milestone_hash", directory.name)
        except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
            issue = error if isinstance(error, EvidenceError) else EvidenceError("milestone_playback", str(error))
            issue.verified_episodes = episodes
            raise issue
    known_stop = meta["stop_reason"] in TECHNICAL_STOPS or meta["stop_reason"] == "suite_complete"
    status = "needs_attention" if not known_stop else "verified" if episodes else "technical_stop"
    return {"schema": 1, "run_id": directory.name, "status": status, "stop_reason": meta["stop_reason"],
            "episodes": episodes, "intervention_commands_verified": len(intervention_commands),
            "video": video_report, "implementation_sha256": meta["implementation_sha256"],
            "evidence_sha256": {p.name: file_sha256(p) for p in sorted(directory.iterdir())
                                if p.is_file() and p.suffix in (".json", ".jsonl", ".log", ".png")}}


def audit_run(directory, *, expected=None, verify_video=True):
    """Turn malformed/unreadable evidence into an explicit failed gate."""
    try:
        return _audit_run(directory, expected=expected, verify_video=verify_video)
    except EvidenceError:
        raise
    except (OSError, ValueError, KeyError, TypeError, AttributeError, IndexError,
            OverflowError, subprocess.SubprocessError) as error:
        raise EvidenceError("evidence_schema", f"{directory}: {error}") from error
