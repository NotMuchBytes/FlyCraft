"""Recipe assistance supplies outcomes and dependencies, never motor actions."""

import math
from collections import defaultdict

from .goal_manager import Goal, GoalManager


GOALS = ("navigate_object", "collect_nearby", "find_collect", "collect_multiple", "craft_simple", "wooden_pickaxe")
# Output, consumed ingredients, reusable station. These are simulator mechanics.
RECIPES = {
    "planks": (4, {"log": 1}, None),
    "sticks": (4, {"planks": 2}, None),
    "crafting_table": (1, {"planks": 4}, None),
    "table_placed": (1, {"crafting_table": 1}, None),
    "wooden_pickaxe": (1, {"planks": 3, "sticks": 2}, "table_placed"),
}


class SubgoalPlanner:
    def plan(self, objective: str, observation: dict) -> GoalManager:
        if objective not in GOALS:
            raise ValueError(f"unsupported goal: {objective}")
        nodes = []
        previous: tuple[str, ...] = ()

        def append(kind: str, predicate: str, item: str = "", count: int = 1) -> None:
            nonlocal previous
            key = f"{len(nodes):03d}:{kind}:{item}"
            nodes.append(Goal(key, kind, predicate, item, count, previous, priority=10))
            previous = (key,)

        if objective == "navigate_object":
            append("search", "visible")
            append("navigate", "near")
            nodes.append(Goal("root", "objective", "near", dependencies=previous))
            return GoalManager(nodes)

        item, amount = {"collect_nearby": ("log", 1), "find_collect": ("log", 1),
                        "collect_multiple": ("log", 3), "craft_simple": ("planks", 4),
                        "wooden_pickaxe": ("wooden_pickaxe", 1)}[objective]
        available = defaultdict(int, observation["inventory"])
        production = defaultdict(int, observation["produced"])

        def require(resource: str, count: int, consume: bool = True) -> None:
            missing = max(0, count - available[resource])
            if missing:
                if resource == "log":
                    append("search", "visible")
                    append("navigate", "near")
                    production[resource] += missing
                    append("collect", "produced", resource, production[resource])
                    available[resource] += missing
                else:
                    output, inputs, station = RECIPES[resource]
                    batches = math.ceil(missing / output)
                    for ingredient, quantity in inputs.items():
                        require(ingredient, quantity * batches)
                    if station:
                        require(station, 1, consume=False)
                    production[resource] += output * batches
                    append("craft_" + resource, "produced", resource, production[resource])
                    available[resource] += output * batches
            if consume:
                available[resource] -= count

        require(item, amount, consume=False)
        nodes.append(Goal("root", "objective", "inventory", item, amount, previous))
        return GoalManager(nodes)
