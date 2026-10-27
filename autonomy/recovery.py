"""Detect failed progress and request bounded replanning and exploration."""

from dataclasses import asdict, dataclass, field

from .world import CRAFT_ACTIONS


@dataclass
class Recovery:
    stagnation_limit: int = 24
    repeat_limit: int = 4
    max_recoveries: int = 4
    stagnant: int = 0
    repeated: int = 0
    last_action: str = ""
    events: list = field(default_factory=list)
    cooldown_action: str = ""
    cooldown: int = 0
    pending_step: int | None = None
    successes: int = 0

    def inspect(self, action: str, before: dict, after: dict, *, progress: bool, step: int) -> str | None:
        if self.cooldown:
            self.cooldown -= 1
        failed = bool(after["last_error"])
        self.repeated = self.repeated + 1 if failed and action == self.last_action else int(failed)
        self.last_action = action
        if progress:
            self.stagnant = 0
            if self.pending_step is not None:
                self.successes += 1
                self.pending_step = None
        else:
            self.stagnant += 1
        reason = None
        if after.get("resource_exhausted"):
            reason = "missing_resources"
        elif after.get("interrupted"):
            reason = "interrupted"
        elif after.get("environment_changed") or (action not in CRAFT_ACTIONS and any(after["inventory"].get(k, 0) < v for k, v in before["inventory"].items())):
            reason = "environment_changed"
        elif self.repeated >= self.repeat_limit:
            reason = "repeated_failure"
        elif self.stagnant >= self.stagnation_limit:
            reason = "stagnation"
        if reason:
            if len(self.events) >= self.max_recoveries or reason == "missing_resources":
                return "unreachable:" + reason
            self.events.append({"reason": reason, "step": step})
            self.pending_step = step
            self.stagnant = self.repeated = 0
            # Remove one recently ineffective action, leaving policy sampling in control.
            self.cooldown_action, self.cooldown = action, 3
            return "replan:" + reason
        return None

    def to_dict(self) -> dict:
        return asdict(self)
