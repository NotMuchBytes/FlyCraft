"""Validated dependency graphs with observation-based completion."""

from dataclasses import asdict, dataclass


@dataclass
class Goal:
    id: str
    kind: str
    predicate: str
    item: str = ""
    count: int = 1
    dependencies: tuple[str, ...] = ()
    priority: int = 0
    status: str = "pending"

    def satisfied(self, observation: dict) -> bool:
        if self.predicate in {"visible", "near"}:
            return bool(observation[self.predicate])
        if self.predicate in {"inventory", "produced"}:
            return observation[self.predicate].get(self.item, 0) >= self.count
        if self.predicate == "dependencies":
            return True
        raise ValueError(f"unknown goal predicate {self.predicate}")


class GoalManager:
    def __init__(self, goals: list[Goal], root: str = "root") -> None:
        self.goals = {goal.id: goal for goal in goals}
        self.root = root
        if len(self.goals) != len(goals) or root not in self.goals:
            raise ValueError("duplicate goals or absent root")
        visited, visiting = set(), set()

        def visit(key: str) -> None:
            if key not in self.goals or key in visiting:
                raise ValueError("missing dependency or cyclic goal graph")
            if key in visited:
                return
            visiting.add(key)
            for dependency in self.goals[key].dependencies:
                visit(dependency)
            visiting.remove(key)
            visited.add(key)

        for key in self.goals:
            visit(key)

    def update(self, observation: dict) -> list[str]:
        completed = []
        root = self.goals[self.root]
        changed = True
        while changed:
            changed = False
            for goal in self.goals.values():
                if goal.status != "pending":
                    continue
                dependencies = [self.goals[key].status for key in goal.dependencies]
                if "failed" in dependencies:
                    goal.status = "failed"
                    changed = True
                elif all(value == "complete" for value in dependencies) and goal.satisfied(observation):
                    goal.status = "complete"
                    completed.append(goal.id)
                    changed = True
        # Credit ready subgoals before accepting an already-owned root item.
        if root.status == "pending" and root.predicate == "inventory" and root.satisfied(observation):
            root.status = "complete"
            completed.append(root.id)
        return completed

    def active(self) -> Goal | None:
        if self.goals[self.root].status != "pending":
            return None
        ready = [goal for goal in self.goals.values() if goal.status == "pending"
                 and all(self.goals[key].status == "complete" for key in goal.dependencies)]
        return min(ready, key=lambda goal: (-goal.priority, goal.id)) if ready else None

    def fail(self, key: str) -> None:
        self.goals[key].status = "failed"
        changed = True
        while changed:
            changed = False
            for goal in self.goals.values():
                if goal.status == "pending" and any(self.goals[key].status == "failed" for key in goal.dependencies):
                    goal.status = "failed"
                    changed = True

    @property
    def success(self) -> bool:
        return self.goals[self.root].status == "complete"

    def to_dict(self) -> dict:
        return {"root": self.root, "goals": [asdict(goal) for goal in self.goals.values()]}

    @classmethod
    def from_dict(cls, data: dict) -> "GoalManager":
        return cls([Goal(**(row | {"dependencies": tuple(row["dependencies"])})) for row in data["goals"]], data["root"])
