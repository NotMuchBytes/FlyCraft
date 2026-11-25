"""Build reproducible Phase 3 populations from downloaded Codex annotations."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from interface.populations import select_phase3_populations, write_population_csv


def describe(path: Path) -> dict[str, object]:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    with gzip.open(path, "rt", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
    ids = [int(row["root_id"]) for row in rows]
    return {
        "filename": path.name,
        "bytes": path.stat().st_size,
        "sha256": digest,
        "schema": reader.fieldnames,
        "rows": len(rows),
        "unique_root_ids": len(set(ids)),
        "duplicate_root_id_rows": len(ids) - len(set(ids)),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    args = parser.parse_args()
    data_dir = args.data_dir
    processed = data_dir / "processed"

    inputs, outputs = select_phase3_populations(data_dir)
    write_population_csv(processed / "phase3_input_population.csv", inputs)
    write_population_csv(processed / "phase3_output_population.csv", outputs)
    np.savez_compressed(
        processed / "phase3_interface_indices.npz",
        input_dense_indices=np.array([r.dense_index for r in inputs], dtype=np.int32),
        output_dense_indices=np.array([r.dense_index for r in outputs], dtype=np.int32),
        output_sides=np.array([r.side for r in outputs], dtype="U8"),
    )

    with np.load(processed / "neuron_index.npz", allow_pickle=False) as mapping:
        universe = set(int(v) for v in mapping["root_ids"])
    metadata = {
        "sources": [
            describe(data_dir / "classification.csv.gz"),
            describe(data_dir / "consolidated_cell_types.csv.gz"),
            describe(data_dir / "visual_neuron_types.csv.gz"),
        ],
        "metadata_universe": len(universe),
        "input_population": {
            "count": len(inputs),
            "left": sum(r.side == "left" for r in inputs),
            "right": sum(r.side == "right" for r in inputs),
            "missing_from_universe": sum(r.root_id not in universe for r in inputs),
            "selection": "visual family=Photo Receptors AND classification sub_class=photo_receptor",
        },
        "output_population": {
            "count": len(outputs),
            "left": sum(r.side == "left" for r in outputs),
            "right": sum(r.side == "right" for r in outputs),
            "other_side": sum(r.side not in {"left", "right"} for r in outputs),
            "missing_from_universe": sum(r.root_id not in universe for r in outputs),
            "selection": "classification super_class=descending",
        },
    }
    (processed / "phase3_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
