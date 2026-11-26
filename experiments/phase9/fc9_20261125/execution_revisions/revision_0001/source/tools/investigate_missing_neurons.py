#!/usr/bin/env python3
"""Report metadata neurons that never appear in the connection graph."""

from __future__ import annotations

import csv
import gzip
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUTPUT = ROOT / "docs" / "graph_missing_neurons.md"


def read_dicts(path: Path):
    with gzip.open(path, "rt", encoding="utf-8-sig", newline="") as handle:
        yield from csv.DictReader(handle)


def main() -> int:
    metadata = {
        int(row["root_id"]): row
        for row in read_dicts(DATA / "neurons.csv.gz")
    }
    visual = {
        int(row["root_id"]): row
        for row in read_dicts(DATA / "visual_neuron_types.csv.gz")
    }
    graph_ids: set[int] = set()
    with gzip.open(
        DATA / "connections_princeton_no_threshold.csv.gz",
        "rt",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)
        for row_number, row in enumerate(reader, start=1):
            graph_ids.add(int(row["pre_root_id"]))
            graph_ids.add(int(row["post_root_id"]))
            if row_number % 5_000_000 == 0:
                print(f"scanned {row_number:,} connection rows", flush=True)

    missing = sorted(set(metadata) - graph_ids)
    extra = sorted(graph_ids - set(metadata))
    groups = Counter(metadata[rid]["group"] or "(blank)" for rid in missing)
    nts = Counter(metadata[rid]["nt_type"] or "(blank)" for rid in missing)
    visual_count = sum(rid in visual for rid in missing)
    lines = [
        "# Metadata Neurons Missing from the Connection Graph",
        "",
        f"- Metadata neuron IDs: {len(metadata):,}",
        f"- Graph neuron IDs: {len(graph_ids):,}",
        f"- Metadata IDs absent from graph: **{len(missing):,}**",
        f"- Graph IDs absent from metadata: **{len(extra):,}**",
        f"- Missing IDs with visual annotations: **{visual_count:,}**",
        "",
        "The simulation keeps all metadata neurons. These 139 entries therefore remain explicit isolated nodes in the initial graph rather than being silently discarded.",
        "",
        "## Shared characteristics visible in the available files",
        "",
        "Group counts:",
        "",
        "| Group | Neurons |",
        "| --- | ---: |",
    ]
    lines += [f"| {group} | {count:,} |" for group, count in groups.most_common()]
    lines += ["", "Categorical neurotransmitter counts:", "", "| NT type | Neurons |", "| --- | ---: |"]
    lines += [f"| {nt} | {count:,} |" for nt, count in nts.most_common()]
    lines += [
        "",
        "These are descriptive correlations only. **The available data does not establish why these neurons have no graph representation.** Possible causes were not inferred.",
        "",
        "## Complete list",
        "",
        "| Root ID | Group | NT type | NT score | Visual annotation | Visual type | Visual family |",
        "| ---: | --- | --- | ---: | --- | --- | --- |",
    ]
    for rid in missing:
        row = metadata[rid]
        vr = visual.get(rid, {})
        lines.append(
            f"| {rid} | {row['group'] or '(blank)'} | {row['nt_type'] or '(blank)'} | "
            f"{row['nt_type_score'] or '(blank)'} | {'yes' if vr else 'no'} | "
            f"{vr.get('type', '') or '—'} | {vr.get('family', '') or '—'} |"
        )
    if extra:
        lines += ["", "## Unexpected graph-only IDs", "", ", ".join(map(str, extra))]
    OUTPUT.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {OUTPUT}")
    print(f"metadata={len(metadata):,} graph={len(graph_ids):,} missing={len(missing):,} extra={len(extra):,}")
    if len(missing) != 139 or extra:
        raise RuntimeError("Observed discrepancy differs from the Phase 1 expectation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
