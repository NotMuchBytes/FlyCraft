"""Explicit goal and memory interface to the existing linear policy readout."""

import hashlib

import numpy as np

from .world import ACTIONS, ITEMS


KINDS = ("search", "navigate", "collect", "craft_planks", "craft_sticks", "craft_crafting_table",
         "craft_table_placed", "craft_wooden_pickaxe")
FEATURE_COUNT = 4 + 4 * len(KINDS) + len(KINDS) + len(ITEMS) + 3 + len(ACTIONS)
SCHEMA = "phase7-context-v1"


def encode(neural: np.ndarray, kind: str, observation: dict, memory, recovery) -> np.ndarray:
    context = np.zeros(len(KINDS))
    context[KINDS.index(kind)] = 1
    previous = np.zeros(len(ACTIONS))
    if memory.recent:
        previous[ACTIONS.index(memory.recent[-1]["action"])] = 1
    return np.concatenate((neural, np.outer(context, neural).ravel(), context * float(observation["near"]),
                           [min(observation["inventory"].get(item, 0), 12) / 12 for item in ITEMS],
                           [memory.failure_fraction, min(recovery.stagnant / recovery.stagnation_limit, 1),
                            float(observation["visible"])], previous))


def table_digest(table) -> str:
    digest = hashlib.sha256()
    for key in sorted(table.features):
        digest.update(key.encode())
        digest.update(np.asarray(table.features[key], dtype="<f8").tobytes())
    return digest.hexdigest()
