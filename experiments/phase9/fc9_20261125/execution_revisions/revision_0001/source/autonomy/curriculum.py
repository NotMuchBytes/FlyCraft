"""Promotion requires a complete, separate held-out evaluation window."""

from dataclasses import asdict, dataclass, field

from .subgoal_planner import GOALS


@dataclass
class Curriculum:
    threshold: float = 0.70
    min_evaluations: int = 30
    max_mean_actions: float = 120.0
    level: int = 0
    history: list = field(default_factory=list)

    def __post_init__(self) -> None:
        if not 0 < self.threshold <= 1 or self.min_evaluations < 1 or self.max_mean_actions <= 0 or not 0 <= self.level < len(GOALS):
            raise ValueError("invalid curriculum configuration")

    @property
    def objective(self) -> str:
        return GOALS[self.level]

    def assess(self, rows: list[dict], *, training_seeds: set[int]) -> bool:
        seeds = [row["world_seed"] for row in rows]
        if len(set(seeds)) != len(seeds) or set(seeds) & training_seeds:
            raise ValueError("curriculum evaluation seeds must be unique and held out")
        if any(row["goal"] != self.objective or row.get("train", True) for row in rows):
            raise ValueError("curriculum needs evaluation rows for its current goal")
        successes = [row for row in rows if row["success"]]
        rate = len(successes) / max(1, len(rows))
        mean_actions = sum(row["actions"] for row in successes) / max(1, len(successes))
        passed = len(rows) >= self.min_evaluations and rate >= self.threshold and mean_actions <= self.max_mean_actions
        self.history.append({"level": self.level + 1, "episodes": len(rows), "success_rate": rate,
                             "mean_success_actions": mean_actions if successes else None, "passed": passed})
        if passed and self.level < len(GOALS) - 1:
            self.level += 1
        return passed

    def to_dict(self) -> dict:
        return asdict(self)
