"""Bounded JSON-serializable episodic memory; spatial facts are world-scoped."""

from collections import deque


class PersistentMemory:
    def __init__(self, capacity: int = 64, max_worlds: int = 16) -> None:
        if capacity < 1 or max_worlds < 1:
            raise ValueError("memory limits must be positive")
        self.capacity, self.max_worlds = capacity, max_worlds
        self.recent = deque(maxlen=capacity)
        self.worlds: dict[str, dict] = {}
        self.attempts: dict[str, dict] = {}
        self.world_id = ""
        self.inventory: dict[str, int] = {}
        self.progress: dict = {}

    def begin(self, observation: dict) -> None:
        world_id = observation["world_id"]
        if world_id != self.world_id:
            self.recent.clear()
            self.progress = {}
        self.world_id = world_id
        if world_id not in self.worlds:
            if len(self.worlds) >= self.max_worlds:
                del self.worlds[next(iter(self.worlds))]
            self.worlds[world_id] = {"obstacles": [], "last_visible_sector": None}
        self.inventory = dict(observation["inventory"])

    def remember(self, before: dict, action: str, after: dict, reward: float) -> None:
        self.inventory = dict(after["inventory"])
        self.recent.append({"action": action, "sector": before["sector"], "position": before["position"],
                            "failed": bool(after["last_error"]), "reward": reward})
        facts = self.worlds[self.world_id]
        if after["visible"]:
            facts["last_visible_sector"] = after["sector"]
            facts["last_seen_position"] = after["position"]
        if after["last_error"] == "blocked":
            facts["obstacles"] = (facts["obstacles"] + [after["position"]])[-16:]

    def finish(self, objective: str, success: bool, steps: int) -> None:
        stats = self.attempts.setdefault(objective, {"successes": 0, "failures": 0, "best_steps": None})
        stats["successes" if success else "failures"] += 1
        if success:
            stats["best_steps"] = min(stats["best_steps"] or steps, steps)

    @property
    def failure_fraction(self) -> float:
        rows = list(self.recent)[-8:]
        return sum(row["failed"] for row in rows) / max(1, len(rows))

    def to_dict(self) -> dict:
        return {"capacity": self.capacity, "max_worlds": self.max_worlds, "recent": list(self.recent),
                "worlds": self.worlds, "attempts": self.attempts, "world_id": self.world_id,
                "inventory": self.inventory, "progress": self.progress}

    @classmethod
    def from_dict(cls, data: dict) -> "PersistentMemory":
        result = cls(data["capacity"], data["max_worlds"])
        for key in ("worlds", "attempts", "world_id", "inventory", "progress"):
            setattr(result, key, data[key])
        result.recent.extend(data["recent"])
        return result
