"""Explicit goal and memory interface to the existing linear policy readout."""

import hashlib
import math

import numpy as np

from .world import ACTIONS, ITEMS, PITCH_ACTIONS


KINDS = ("search", "navigate", "collect", "craft_planks", "craft_sticks", "craft_crafting_table",
         "craft_table_placed", "craft_wooden_pickaxe")
FEATURE_COUNT = 4 + 4 * len(KINDS) + len(KINDS) + len(ITEMS) + 3 + len(ACTIONS)
SCHEMA = "phase7-context-v1"
PITCH_FEATURE_COUNT = FEATURE_COUNT + 1 + len(PITCH_ACTIONS)
PITCH_SCHEMA = "live-pitch-context-v1"
TERRAIN_FEATURE_COUNT = PITCH_FEATURE_COUNT + 8
TERRAIN_SCHEMA = "live-terrain-context-v1"


def encode(neural: np.ndarray, kind: str, observation: dict, memory, recovery, *, pitch=False, terrain=False) -> np.ndarray:
    context = np.zeros(len(KINDS))
    context[KINDS.index(kind)] = 1
    previous = np.zeros(len(ACTIONS))
    previous_action = memory.recent[-1]["action"] if memory.recent else None
    if previous_action in ACTIONS:
        previous[ACTIONS.index(previous_action)] = 1
    features = (neural, np.outer(context, neural).ravel(), context * float(observation["near"]),
                [min(observation["inventory"].get(item, 0), 12) / 12 for item in ITEMS],
                [memory.failure_fraction, min(recovery.stagnant / recovery.stagnation_limit, 1),
                 float(observation["visible"])], previous)
    if pitch:
        pitch_error = observation.get("pitch_error", 0.0) / math.pi
        features += ([pitch_error, *(float(previous_action == action) for action in PITCH_ACTIONS)],)
    if terrain:
        if not pitch:
            raise ValueError("terrain features require the preserved pitch prefix")
        features += ([observation["health"] / 20, observation["food"] / 20,
            float(observation["on_ground"]), float(observation["obstacle_visible"]),
            float(observation["support_visible"]), float(observation["drop_visible"]),
            float(observation["water_visible"]), float(previous_action == "JUMP_FORWARD")],)
    return np.concatenate(features)


def table_digest(table) -> str:
    digest = hashlib.sha256()
    for key in sorted(table.features):
        digest.update(key.encode())
        digest.update(np.asarray(table.features[key], dtype="<f8").tobytes())
    return digest.hexdigest()
