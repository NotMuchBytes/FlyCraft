"""Metadata-grounded selection of Phase 3 input and output populations."""

from __future__ import annotations

import csv
import gzip
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class PopulationRecord:
    root_id: int
    dense_index: int
    side: str
    primary_type: str
    visual_type: str
    family: str
    subsystem: str
    flow: str
    super_class: str
    cell_class: str
    sub_class: str
    reason: str


def _read_gzip_csv(path: Path) -> list[dict[str, str]]:
    with gzip.open(path, "rt", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _dense_index(root_ids: np.ndarray, root_id: int) -> int:
    position = int(np.searchsorted(root_ids, np.uint64(root_id)))
    if position >= root_ids.size or int(root_ids[position]) != root_id:
        raise KeyError(root_id)
    return position


def select_phase3_populations(data_dir: Path) -> tuple[list[PopulationRecord], list[PopulationRecord]]:
    """Select metadata-supported photoreceptor inputs and descending outputs.

    Input selection requires agreement between the visual catalog and the
    hierarchical classification. Output selection uses the explicit
    ``descending`` superclass. No action semantics are inferred here.
    """

    with np.load(data_dir / "processed" / "neuron_index.npz", allow_pickle=False) as mapping:
        root_ids = mapping["root_ids"].astype(np.uint64, copy=False)

    classifications = {int(row["root_id"]): row for row in _read_gzip_csv(data_dir / "classification.csv.gz")}
    cell_types = {int(row["root_id"]): row for row in _read_gzip_csv(data_dir / "consolidated_cell_types.csv.gz")}
    visuals = {int(row["root_id"]): row for row in _read_gzip_csv(data_dir / "visual_neuron_types.csv.gz")}

    inputs: list[PopulationRecord] = []
    for root_id, visual in visuals.items():
        classification = classifications.get(root_id)
        if not classification:
            continue
        if visual["family"] != "Photo Receptors" or classification["sub_class"] != "photo_receptor":
            continue
        cell_type = cell_types.get(root_id, {})
        inputs.append(
            PopulationRecord(
                root_id=root_id,
                dense_index=_dense_index(root_ids, root_id),
                side=classification["side"] or visual["side"],
                primary_type=cell_type.get("primary_type", ""),
                visual_type=visual["type"],
                family=visual["family"],
                subsystem=visual["subsystem"],
                flow=classification["flow"],
                super_class=classification["super_class"],
                cell_class=classification["class"],
                sub_class=classification["sub_class"],
                reason="visual family=Photo Receptors AND classification sub_class=photo_receptor",
            )
        )

    outputs: list[PopulationRecord] = []
    for root_id, classification in classifications.items():
        if classification["super_class"] != "descending":
            continue
        cell_type = cell_types.get(root_id, {})
        visual = visuals.get(root_id, {})
        outputs.append(
            PopulationRecord(
                root_id=root_id,
                dense_index=_dense_index(root_ids, root_id),
                side=classification["side"],
                primary_type=cell_type.get("primary_type", ""),
                visual_type=visual.get("type", ""),
                family=visual.get("family", ""),
                subsystem=visual.get("subsystem", ""),
                flow=classification["flow"],
                super_class=classification["super_class"],
                cell_class=classification["class"],
                sub_class=classification["sub_class"],
                reason="classification super_class=descending",
            )
        )

    inputs.sort(key=lambda record: record.root_id)
    outputs.sort(key=lambda record: record.root_id)
    return inputs, outputs


def select_superclass_population(data_dir: Path, superclass: str) -> list[PopulationRecord]:
    """Select a population using the explicit classification superclass."""

    with np.load(data_dir / "processed" / "neuron_index.npz", allow_pickle=False) as mapping:
        root_ids = mapping["root_ids"].astype(np.uint64, copy=False)

    classifications = _read_gzip_csv(data_dir / "classification.csv.gz")
    cell_types = {int(row["root_id"]): row for row in _read_gzip_csv(data_dir / "consolidated_cell_types.csv.gz")}
    visuals = {int(row["root_id"]): row for row in _read_gzip_csv(data_dir / "visual_neuron_types.csv.gz")}
    records: list[PopulationRecord] = []
    for classification in classifications:
        if classification["super_class"] != superclass:
            continue
        root_id = int(classification["root_id"])
        cell_type = cell_types.get(root_id, {})
        visual = visuals.get(root_id, {})
        records.append(
            PopulationRecord(
                root_id=root_id,
                dense_index=_dense_index(root_ids, root_id),
                side=classification["side"],
                primary_type=cell_type.get("primary_type", ""),
                visual_type=visual.get("type", ""),
                family=visual.get("family", ""),
                subsystem=visual.get("subsystem", ""),
                flow=classification["flow"],
                super_class=classification["super_class"],
                cell_class=classification["class"],
                sub_class=classification["sub_class"],
                reason=f"classification super_class={superclass}",
            )
        )
    records.sort(key=lambda record: record.root_id)
    return records


def write_population_csv(path: Path, records: list[PopulationRecord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(asdict(records[0]).keys()) if records else [field.name for field in PopulationRecord.__dataclass_fields__.values()]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(asdict(record) for record in records)
