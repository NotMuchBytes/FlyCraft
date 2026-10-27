"""Seeded resource/recipe extension of the existing World2D, not Minecraft."""

import math
from dataclasses import asdict

import numpy as np

from environment import AngularSensor, World2D
from learning.policy import ACTIONS as NAVIGATION_ACTIONS

from .subgoal_planner import GOALS, RECIPES


CRAFT_ACTIONS = {"CRAFT_PLANKS": "planks", "CRAFT_STICKS": "sticks", "CRAFT_TABLE": "crafting_table",
                 "PLACE_TABLE": "table_placed", "CRAFT_PICKAXE": "wooden_pickaxe"}
ACTIONS = NAVIGATION_ACTIONS + ("COLLECT_LOG",) + tuple(CRAFT_ACTIONS)
ITEMS = ("log", "planks", "sticks", "crafting_table", "table_placed", "wooden_pickaxe")


class ResourceWorld:
    """Simple mechanics: collect one log per explicit interaction; craft one batch.

    No automatic collection, crafting, path following, or scripted actions.
    Obstacles block movement and vision. Station use is local to the placed table.
    """

    def __init__(self, seed: int, objective: str = "navigate_object", *, obstacles: bool = False) -> None:
        if objective not in GOALS:
            raise ValueError("unknown world objective")
        self.seed, self.objective = seed, objective
        self.world_id = f"sim:{seed}:{objective}:{int(obstacles)}"
        rng = np.random.default_rng(seed)
        self.world = World2D(width=30, height=30, start_x=15, start_y=15, start_heading=math.pi / 2)
        level = GOALS.index(objective)
        bearing = rng.uniform(-1.1, 1.1) if level < 2 else rng.uniform(-math.pi, math.pi)
        distance = rng.uniform(2, 4) if level < 2 else rng.uniform(3, 7)
        direction = self.world.heading + bearing
        x, y = 15 + distance * math.cos(direction), 15 + distance * math.sin(direction)
        self.resources = [{"id": "tree0", "x": x, "y": y, "logs": 3},
                          {"id": "tree1", "x": 15 + rng.uniform(-7, 7), "y": 15 + rng.uniform(-7, 7), "logs": 3}]
        self.obstacles = [(15 + (x - 15) * 0.5, 15 + (y - 15) * 0.5, 0.6)] if obstacles else []
        self.inventory = {item: 0 for item in ITEMS}
        self.produced = dict(self.inventory)
        self.station: list[float] | None = None
        self.last_error = ""
        self.steps = 0
        self.sensor = AngularSensor(field_of_view=math.pi, max_distance=12)

    def target(self) -> dict | None:
        remaining = [resource for resource in self.resources if resource["logs"] > 0]
        return min(remaining, key=lambda r: math.hypot(r["x"] - self.world.x, r["y"] - self.world.y)) if remaining else None

    def _occluded(self, target: dict) -> bool:
        dx, dy = target["x"] - self.world.x, target["y"] - self.world.y
        for x, y, radius in self.obstacles:
            t = max(0, min(1, ((x - self.world.x) * dx + (y - self.world.y) * dy) / max(1e-10, dx * dx + dy * dy)))
            if math.hypot(x - (self.world.x + t * dx), y - (self.world.y + t * dy)) < radius:
                return True
        return False

    def can_craft(self, item: str) -> bool:
        _, inputs, station = RECIPES[item]
        return all(self.inventory[key] >= count for key, count in inputs.items()) and (
            station is None or self.station is not None and math.hypot(self.world.x - self.station[0], self.world.y - self.station[1]) <= 2)

    def observe(self) -> dict:
        target = self.target()
        if target:
            self.world.target_x, self.world.target_y = target["x"], target["y"]
            visual = self.sensor.observe(self.world)
            visible = visual.visible and not self._occluded(target)
            distance, angle = visual.distance, visual.relative_angle
        else:
            visible, distance, angle = False, None, None
        near = bool(visible and distance <= 1.0)
        allowed = list(NAVIGATION_ACTIONS)
        if near:
            allowed.append("COLLECT_LOG")
        allowed += [action for action, item in CRAFT_ACTIONS.items() if self.can_craft(item)]
        return {"world_id": self.world_id, "position": list(self.world.state), "visible": visible,
                "sector": visual.sector if visible else None, "near": near,
                "distance": distance if visible else None, "angle": angle if visible else None,
                "target_id": target["id"] if visible else None,
                "inventory": dict(self.inventory), "produced": dict(self.produced), "allowed_actions": allowed,
                "last_error": self.last_error, "resource_exhausted": target is None, "interrupted": False}

    def step(self, action: str) -> dict:
        if action not in ACTIONS:
            raise ValueError(f"unknown resource action: {action}")
        before = self.observe()
        self.last_error = ""
        if action not in before["allowed_actions"]:
            self.last_error = "missing_precondition"
        elif action in NAVIGATION_ACTIONS:
            x, y, _ = self.world.state
            self.world.step(action)
            if action == "FORWARD" and (any(math.hypot(self.world.x - ox, self.world.y - oy) <= radius for ox, oy, radius in self.obstacles)
                                        or (x, y) == (self.world.x, self.world.y)):
                self.world.x, self.world.y = x, y
                self.last_error = "blocked"
        elif action == "COLLECT_LOG":
            self.target()["logs"] -= 1
            self.inventory["log"] += 1
            self.produced["log"] += 1
        else:
            item = CRAFT_ACTIONS[action]
            amount, inputs, _ = RECIPES[item]
            for key, count in inputs.items():
                self.inventory[key] -= count
            self.inventory[item] += amount
            self.produced[item] += amount
            if item == "table_placed":
                self.station = [self.world.x, self.world.y]
        self.steps += 1
        return self.observe()

    def to_dict(self) -> dict:
        return {"seed": self.seed, "objective": self.objective, "world_id": self.world_id,
                "world_config": asdict(self.world), "pose": list(self.world.state), "resources": self.resources,
                "obstacles": self.obstacles, "inventory": self.inventory, "produced": self.produced,
                "station": self.station, "last_error": self.last_error, "steps": self.steps}

    @classmethod
    def from_dict(cls, data: dict) -> "ResourceWorld":
        result = cls(data["seed"], data["objective"])
        result.world = World2D(**data["world_config"])
        result.world.x, result.world.y, result.world.heading = data["pose"]
        for key in ("world_id", "resources", "obstacles", "inventory", "produced", "station", "last_error", "steps"):
            setattr(result, key, data[key])
        return result
