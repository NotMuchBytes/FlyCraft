"""Artificial action decoder over metadata-selected descending neurons."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .populations import PopulationRecord


@dataclass(frozen=True)
class OutputResponse:
    left_activity: int
    right_activity: int
    center_activity: int
    total_activity: int
    active_indices: tuple[int, ...]


class ActionDecoder:
    """Engineering mapping; action labels are not biological interpretations."""

    def __init__(self, records: list[PopulationRecord], minimum_activity: int = 1, turn_margin: int = 1) -> None:
        self.left = np.array([r.dense_index for r in records if r.side == "left"], dtype=np.int64)
        self.right = np.array([r.dense_index for r in records if r.side == "right"], dtype=np.int64)
        self.center = np.array([r.dense_index for r in records if r.side not in {"left", "right"}], dtype=np.int64)
        self.all_indices = np.array([r.dense_index for r in records], dtype=np.int64)
        self.minimum_activity = minimum_activity
        self.turn_margin = turn_margin

    def observe(self, spikes: np.ndarray) -> OutputResponse:
        active = self.all_indices[spikes[self.all_indices]]
        return OutputResponse(
            left_activity=int(np.count_nonzero(spikes[self.left])),
            right_activity=int(np.count_nonzero(spikes[self.right])),
            center_activity=int(np.count_nonzero(spikes[self.center])),
            total_activity=int(active.size),
            active_indices=tuple(int(v) for v in active),
        )

    def decode(self, response: OutputResponse) -> str:
        if response.total_activity < self.minimum_activity:
            return "NO_OP"
        difference = response.left_activity - response.right_activity
        if difference >= self.turn_margin:
            return "TURN_LEFT"
        if difference <= -self.turn_margin:
            return "TURN_RIGHT"
        return "FORWARD"


@dataclass(frozen=True)
class RateOutputResponse:
    left_activity: float
    right_activity: float
    center_activity: float
    total_activity: float
    active_cells: int


class RateActionDecoder:
    """Engineering action mapping over a continuous annotated readout.

    The decoder never sees the sensory condition or target coordinates. It
    compares activity assigned to anatomical sides in the selected population.
    """

    def __init__(
        self,
        records: list[PopulationRecord],
        minimum_total_activity: float = 0.01,
        turn_margin: float = 0.01,
        activity_floor: float = 0.01,
    ) -> None:
        self.left = np.array([r.dense_index for r in records if r.side == "left"], dtype=np.int64)
        self.right = np.array([r.dense_index for r in records if r.side == "right"], dtype=np.int64)
        self.center = np.array([r.dense_index for r in records if r.side not in {"left", "right"}], dtype=np.int64)
        self.all_indices = np.array([r.dense_index for r in records], dtype=np.int64)
        self.minimum_total_activity = minimum_total_activity
        self.turn_margin = turn_margin
        self.activity_floor = activity_floor

    def observe(self, activity: np.ndarray) -> RateOutputResponse:
        readout = activity[self.all_indices]
        return RateOutputResponse(
            left_activity=float(activity[self.left].sum(dtype=np.float64)),
            right_activity=float(activity[self.right].sum(dtype=np.float64)),
            center_activity=float(activity[self.center].sum(dtype=np.float64)),
            total_activity=float(readout.sum(dtype=np.float64)),
            active_cells=int(np.count_nonzero(readout >= self.activity_floor)),
        )

    def decode(self, response: RateOutputResponse) -> str:
        if response.total_activity < self.minimum_total_activity:
            return "NO_OP"
        difference = response.left_activity - response.right_activity
        if difference >= self.turn_margin:
            return "TURN_LEFT"
        if difference <= -self.turn_margin:
            return "TURN_RIGHT"
        return "FORWARD"
