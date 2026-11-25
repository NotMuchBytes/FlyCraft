#!/usr/bin/env python3
"""Phase 1: inspect local FlyWire/Codex CSV exports by their real schemas."""

from __future__ import annotations

import argparse
import csv
import gzip
import heapq
import math
import os
import sys
import tempfile
import time
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, TextIO


PRE = {"pre_root_id", "pre", "source", "source_id", "pre_id"}
POST = {"post_root_id", "post", "target", "target_id", "post_id"}
ROOT = {"root_id", "neuron_id", "id", "root"}
WEIGHT = {"syn_count", "synapse_count", "weight", "connection_weight"}
NT = {"nt_type", "neurotransmitter", "transmitter"}
CLASS_FIELDS = {"class", "classification", "super_class", "flow", "hemilineage", "sub_class"}
VISUAL_FIELDS = {"family", "subsystem", "category", "side"}


@dataclass
class Table:
    path: Path
    compression: str
    header: list[str]
    samples: list[list[str]]
    role: str


def open_text(path: Path) -> TextIO:
    with path.open("rb") as raw:
        gzipped = raw.read(2) == b"\x1f\x8b"
    if gzipped:
        return gzip.open(path, "rt", encoding="utf-8-sig", newline="")
    return path.open("rt", encoding="utf-8-sig", newline="")


def normalize(values: Iterable[str]) -> list[str]:
    return [value.strip().lower() for value in values]


def find(header: list[str], aliases: set[str]) -> str | None:
    return next((name for name in header if name in aliases), None)


def role_for(header: list[str]) -> str:
    names = set(header)
    if names & PRE and names & POST:
        return "connections"
    if names & ROOT:
        if VISUAL_FIELDS.issubset(names):
            return "visual_annotations"
        if names & CLASS_FIELDS:
            return "classification"
        if names & NT or any(name.endswith("_avg") for name in names):
            return "neurotransmitter_predictions"
        if names & {"type", "cell_type", "hemibrain_type"}:
            return "cell_types"
        return "neuron_metadata"
    return "unknown"


def inspect(path: Path) -> Table:
    with path.open("rb") as raw:
        compression = "gzip" if raw.read(2) == b"\x1f\x8b" else "none"
    with open_text(path) as handle:
        rows = csv.reader(handle)
        try:
            header = normalize(next(rows))
        except StopIteration:
            header = []
        samples = [row for _, row in zip(range(3), rows)]
    return Table(path, compression, header, samples, role_for(header))


def infer_type(values: Iterable[str]) -> str:
    values = [value.strip() for value in values if value.strip()]
    if not values:
        return "unknown"
    try:
        parsed = [int(value) for value in values]
        return "uint64" if min(parsed) >= 0 and max(parsed) > 2**63 - 1 else "integer"
    except ValueError:
        pass
    try:
        [float(value) for value in values]
        return "floating point"
    except ValueError:
        return "text"


def inferred_schema(table: Table) -> list[tuple[str, str]]:
    columns = list(zip(*table.samples)) if table.samples else []
    return [
        (name, infer_type(columns[index] if index < len(columns) else []))
        for index, name in enumerate(table.header)
    ]


def bytes_label(value: int | float) -> str:
    size = float(value)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if size < 1024 or unit == "TiB":
            return f"{size:,.2f} {unit}"
        size /= 1024
    raise AssertionError


def rss_bytes() -> int | None:
    if os.name != "nt":
        return None
    try:
        import ctypes
        from ctypes import wintypes

        class PMC(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t),
                ("PrivateUsage", ctypes.c_size_t),
            ]

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        kernel32.GetCurrentProcess.restype = wintypes.HANDLE
        psapi.GetProcessMemoryInfo.argtypes = [
            wintypes.HANDLE, ctypes.POINTER(PMC), wintypes.DWORD
        ]
        psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
        counters = PMC()
        counters.cb = ctypes.sizeof(counters)
        process = kernel32.GetCurrentProcess()
        ok = psapi.GetProcessMemoryInfo(process, ctypes.byref(counters), counters.cb)
        return int(counters.PeakWorkingSetSize) if ok else None
    except Exception:
        return None


def percentile(counter: Counter[int], total: int, fraction: float) -> int | None:
    target = max(1, math.ceil(total * fraction)) if total else 0
    seen = 0
    for value, count in sorted(counter.items()):
        seen += count
        if seen >= target:
            return value
    return None


def partition_for(pre: int, post: int, partitions: int) -> int:
    mixed = (pre ^ (post * 0x9E3779B185EBCA87)) & ((1 << 64) - 1)
    mixed ^= mixed >> 33
    return mixed & (partitions - 1)


def scan_metadata(table: Table) -> tuple[dict[str, object], dict[int, dict[str, str]]]:
    started = time.perf_counter()
    id_name = find(table.header, ROOT)
    rows = malformed = duplicate_rows = duplicate_ids = 0
    seen_rows: set[tuple[str, ...]] = set()
    seen_ids: set[int] = set()
    records: dict[int, dict[str, str]] = {}
    counters = {name: Counter() for name in table.header if name != id_name}
    with open_text(table.path) as handle:
        reader = csv.reader(handle)
        actual = normalize(next(reader))
        indices = {name: actual.index(name) for name in actual}
        for row in reader:
            rows += 1
            if len(row) != len(actual):
                malformed += 1
                continue
            cleaned = tuple(value.strip() for value in row)
            if cleaned in seen_rows:
                duplicate_rows += 1
            else:
                seen_rows.add(cleaned)
            try:
                root_id = int(row[indices[id_name]].strip()) if id_name else None
            except ValueError:
                malformed += 1
                continue
            if root_id is not None:
                if root_id in seen_ids:
                    duplicate_ids += 1
                seen_ids.add(root_id)
                records[root_id] = {name: row[index].strip() for name, index in indices.items()}
            for name, counter in counters.items():
                value = row[indices[name]].strip()
                if value:
                    counter[value] += 1
    summary = {
        "rows": rows, "unique_ids": len(seen_ids), "malformed": malformed,
        "duplicate_rows": duplicate_rows, "duplicate_ids": duplicate_ids,
        "distinct": {name: len(values) for name, values in counters.items()},
        "top": {name: values.most_common(12) for name, values in counters.items()},
        "seconds": time.perf_counter() - started,
    }
    return summary, records


def scan_connections(
    table: Table,
    metadata: dict[int, dict[str, str]],
    visual: dict[int, dict[str, str]],
    temp_parent: Path,
) -> dict[str, object]:
    started = time.perf_counter()
    partitions = 128
    rows = valid = malformed = total_weight = sum_squares = 0
    weight_counts: Counter[int] = Counter()
    neurons: set[int] = set()
    strongest: list[tuple[int, int, int, str, str]] = []
    peak_rss = rss_bytes() or 0

    with tempfile.TemporaryDirectory(prefix="flycraft_analysis_", dir=temp_parent) as temp_name:
        temp = Path(temp_name)
        paths = [temp / f"part_{number:03d}.tsv" for number in range(partitions)]
        handles = [path.open("wb", buffering=65536) for path in paths]
        partition_rows = [0] * partitions
        try:
            with open_text(table.path) as source:
                reader = csv.reader(source)
                actual = normalize(next(reader))
                index = {name: actual.index(name) for name in actual}
                pre_name, post_name = find(actual, PRE), find(actual, POST)
                weight_name, nt_name = find(actual, WEIGHT), find(actual, NT)
                if not pre_name or not post_name:
                    raise RuntimeError("No recognized pre/post columns")
                for row in reader:
                    rows += 1
                    if len(row) != len(actual):
                        malformed += 1
                        continue
                    try:
                        pre = int(row[index[pre_name]].strip())
                        post = int(row[index[post_name]].strip())
                        weight = int(row[index[weight_name]].strip()) if weight_name else 1
                        if pre < 0 or post < 0 or weight < 0:
                            raise ValueError
                    except (ValueError, TypeError):
                        malformed += 1
                        continue
                    valid += 1
                    neurons.update((pre, post))
                    total_weight += weight
                    sum_squares += weight * weight
                    weight_counts[weight] += 1
                    neuropil = row[index["neuropil"]].strip() if "neuropil" in index else ""
                    edge_nt = row[index[nt_name]].strip() if nt_name else ""
                    item = (weight, pre, post, neuropil, edge_nt)
                    if len(strongest) < 20:
                        heapq.heappush(strongest, item)
                    elif item > strongest[0]:
                        heapq.heapreplace(strongest, item)
                    bucket = partition_for(pre, post, partitions)
                    canonical = "\t".join(value.strip() for value in row)
                    handles[bucket].write(f"{pre}\t{post}\t{canonical}\n".encode("utf-8"))
                    partition_rows[bucket] += 1
                    if rows % 1_000_000 == 0:
                        peak_rss = max(peak_rss, rss_bytes() or 0)
                        print(f"  parsed {rows:,} rows", flush=True)
        finally:
            for handle in handles:
                handle.close()

        unique_pairs = duplicate_exact_excess = duplicate_exact_keys = 0
        repeated_pair_excess = repeated_pair_keys = 0
        for number, path in enumerate(paths):
            exact_seen: set[bytes] = set()
            exact_repeated: set[bytes] = set()
            pair_seen: set[bytes] = set()
            pair_repeated: set[bytes] = set()
            with path.open("rb") as handle:
                for line in handle:
                    if line in exact_seen:
                        duplicate_exact_excess += 1
                        exact_repeated.add(line)
                    else:
                        exact_seen.add(line)
                    first = line.find(b"\t")
                    second = line.find(b"\t", first + 1)
                    pair = line[:second]
                    if pair in pair_seen:
                        repeated_pair_excess += 1
                        pair_repeated.add(pair)
                    else:
                        pair_seen.add(pair)
            unique_pairs += len(pair_seen)
            duplicate_exact_keys += len(exact_repeated)
            repeated_pair_keys += len(pair_repeated)
            peak_rss = max(peak_rss, rss_bytes() or 0)
            if (number + 1) % 16 == 0:
                print(f"  checked {number + 1}/{partitions} duplicate partitions", flush=True)

    mean = total_weight / valid if valid else 0.0
    variance = sum_squares / valid - mean * mean if valid else 0.0
    strongest_rows = []
    for weight, pre, post, neuropil, edge_nt in sorted(strongest, reverse=True):
        strongest_rows.append({
            "weight": weight, "pre": pre, "post": post, "neuropil": neuropil,
            "edge_nt": edge_nt, "pre_nt": metadata.get(pre, {}).get("nt_type", ""),
            "post_nt": metadata.get(post, {}).get("nt_type", ""),
            "pre_visual": visual.get(pre, {}).get("type", ""),
            "post_visual": visual.get(post, {}).get("type", ""),
        })
    return {
        "rows": rows, "valid": valid, "malformed": malformed,
        "unique_neurons": len(neurons), "unique_pairs": unique_pairs,
        "total_weight": total_weight, "min": min(weight_counts), "max": max(weight_counts),
        "mean": mean, "std": math.sqrt(max(variance, 0.0)),
        "percentiles": {f"p{p}": percentile(weight_counts, valid, p / 100) for p in (50, 90, 95, 99)},
        "common": weight_counts.most_common(12), "strongest": strongest_rows,
        "duplicate_exact_excess": duplicate_exact_excess,
        "duplicate_exact_keys": duplicate_exact_keys,
        "repeated_pair_excess": repeated_pair_excess,
        "repeated_pair_keys": repeated_pair_keys,
        "seconds": time.perf_counter() - started, "peak_rss": peak_rss,
    }


def table_md(headers: list[str], rows: Iterable[Iterable[object]]) -> list[str]:
    result = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for row in rows:
        result.append("| " + " | ".join(str(v).replace("|", "\\|").replace("\n", " ") for v in row) + " |")
    return result


def report_text(
    tables: list[Table], summaries: dict[str, dict[str, object]],
    graph: dict[str, object], elapsed: float,
) -> str:
    total_size = sum(table.path.stat().st_size for table in tables)
    roles = {table.role for table in tables}
    missing = [label for role, label in (
        ("cell_types", "Cell Types"),
        ("classification", "Classification / Hierarchical Annotations"),
    ) if role not in roles]
    lines = [
        "# FlyCraft Initial Data Report", "",
        f"Generated: {datetime.now().astimezone().isoformat(timespec='seconds')}", "",
        "## Scope and scientific status", "",
        "This is an inspection of structural FlyWire/Codex exports, not a functioning digital fly brain. These files do not specify complete neuron dynamics, synaptic dynamics, learning rules, consciousness, or Minecraft knowledge. No simulator, learning, or Minecraft work was done in Phase 1.", "",
        "## Dataset", "",
        "- Declared dataset: FAFB v783, Female Adult Fly Brain (from the project brief; the CSV schemas contain no independent version field).",
        f"- Files loaded: {len(tables)}",
        f"- Total compressed size: {bytes_label(total_size)} ({total_size:,} bytes)",
        f"- Missing expected exports: {', '.join(missing) if missing else 'none'}", "",
    ]
    lines += table_md(["File", "Bytes", "Compression", "Detected role"], [
        (t.path.name, f"{t.path.stat().st_size:,}", t.compression, t.role) for t in tables
    ])
    lines += ["", "## Exact schemas", ""]
    for item in tables:
        lines += [f"### `{item.path.name}`", ""]
        lines += table_md(["Column", "Sample-inferred type"], inferred_schema(item))
        lines += ["", "Sample rows:", "", "```text"] + [repr(r) for r in item.samples] + ["```", ""]
    lines += [
        "## Connectome", "",
        f"- Unique neurons appearing in graph: **{graph['unique_neurons']:,}**",
        f"- Valid directed connection records: **{graph['valid']:,}**",
        f"- Unique directed neuron-to-neuron pairs: **{graph['unique_pairs']:,}**",
        f"- Total `syn_count` / aggregate connection weight: **{graph['total_weight']:,}**",
        f"- Malformed rows: **{graph['malformed']:,}**",
        f"- Exact duplicate rows beyond first: **{graph['duplicate_exact_excess']:,}** across **{graph['duplicate_exact_keys']:,}** duplicated keys",
        f"- Extra rows sharing a pre/post pair: **{graph['repeated_pair_excess']:,}** across **{graph['repeated_pair_keys']:,}** repeated pairs. These can represent separate neuropils/annotations and are not automatically errors.", "",
        "### Weight distribution", "",
        f"- Minimum: {graph['min']}", f"- Maximum: {graph['max']}",
        f"- Mean: {graph['mean']:.6f}", f"- Population standard deviation: {graph['std']:.6f}",
    ]
    lines += [f"- {name.upper()}: {value}" for name, value in graph["percentiles"].items()]
    lines += ["", "Most common weights:", ""]
    lines += table_md(["Weight", "Records"], [(w, f"{n:,}") for w, n in graph["common"]])
    lines += ["", "### Strongest connection records", ""]
    lines += table_md(
        ["Weight", "Pre root ID", "Post root ID", "Neuropil", "Edge NT", "Pre NT", "Post NT", "Pre visual type", "Post visual type"],
        [(r["weight"], r["pre"], r["post"], r["neuropil"], r["edge_nt"], r["pre_nt"], r["post_nt"], r["pre_visual"], r["post_visual"]) for r in graph["strongest"]],
    )
    lines += ["", "## Metadata", ""]
    for item in tables:
        if item.role == "connections":
            continue
        s = summaries[item.path.name]
        lines += [
            f"### `{item.path.name}` ({item.role})", "",
            f"- Rows: {s['rows']:,}", f"- Unique root IDs: {s['unique_ids']:,}",
            f"- Malformed rows: {s['malformed']:,}", f"- Exact duplicate rows: {s['duplicate_rows']:,}",
            f"- Duplicate root IDs: {s['duplicate_ids']:,}", "",
        ]
        for field in ("group", "nt_type", "family", "subsystem", "category", "side"):
            values = s["top"].get(field, [])
            if values:
                lines += [f"Top `{field}` values:", ""]
                lines += table_md([field, "Rows"], [(v, f"{n:,}") for v, n in values]) + [""]
    visual = next((summaries[t.path.name] for t in tables if t.role == "visual_annotations"), None)
    nt = next((summaries[t.path.name] for t in tables if t.role == "neurotransmitter_predictions"), None)
    visual_photo = dict(visual["top"].get("family", [])).get("Photo Receptors", 0) if visual else 0
    assigned_nt = sum(count for _, count in nt["top"].get("nt_type", [])) if nt else 0
    lines += [
        "### Candidate interface populations", "",
        f"- Broad visual candidate pool: {visual['unique_ids']:,} visual-annotated neurons, including {visual_photo:,} rows whose family is labeled `Photo Receptors`." if visual else "- Broad visual candidate pool: unavailable.",
        "- A visual annotation does not prove that every listed cell is a primary sensory input. Final selection requires cell-type/classification evidence and literature review.",
        "- Descending/output candidates: **not reliably identifiable from the available tables**. The missing Cell Types and Classification exports are needed before selection.",
        f"- The neurotransmitter table covers {nt['unique_ids']:,} unique neuron IDs; {assigned_nt:,} have a non-empty categorical `nt_type` and {nt['unique_ids'] - assigned_nt:,} are blank. These are predictions, not exact synaptic physiology." if nt else "- Neurotransmitter predictions: unavailable.", "",
        "## Performance", "",
        f"- Connection analysis: {graph['seconds']:.3f} seconds",
        f"- End-to-end analysis: {elapsed:.3f} seconds",
        f"- Peak observed process working set: {bytes_label(graph['peak_rss'])}",
    ]
    n, e = int(graph["unique_neurons"]), int(graph["unique_pairs"])
    csr = e * 8 + (n + 1) * 4
    state = n * 13
    lines += [
        f"- Estimated minimal future CSR arrays (float32 weights, int32 indices/pointers): {bytes_label(csr)}",
        f"- Estimated minimal neuron state (three float32 arrays + uint8 spike): {bytes_label(state)}",
        f"- Minimal core estimate before mappings, metadata, logs, and temporary buffers: {bytes_label(csr + state)}", "",
        "## Problems and uncertainties", "",
        "- The brief named `C:\\Users\\Hamzah`, which does not exist here. The OS-resolved Desktop for the active profile was used: `C:\\Users\\anass\\OneDrive\\Desktop`.",
        "- Cell Types and Classification / Hierarchical Annotations exports were not present. Nothing was fabricated or downloaded.",
        "- FAFB v783 identity comes from the brief, not a version column in these files.",
        "- `syn_count` is treated as aggregate connection weight based on its actual field name; source aggregation semantics should be verified against official Codex documentation before simulation.", "",
        "## Phase boundary", "",
        "Phase 1 stops here. No simulator, environment, Minecraft integration, learning, or training has started.", "",
    ]
    return "\n".join(lines)


def append_log(root: Path, tables: list[Table], graph: dict[str, object], elapsed: float) -> None:
    moved = [(t.path.name, f"{t.path.stat().st_size:,}", str(Path(r"C:\Users\anass\Downloads") / t.path.name), str(t.path)) for t in tables]
    lines = [
        f"## {datetime.now().astimezone().isoformat(timespec='seconds')} — Phase 1 data inspection", "",
        "**TASK**", "", "Inventory and move available Codex exports, inspect their schemas, and run the initial bounded-memory analysis.", "",
        "**WHAT WE TRIED**", "",
        "- Verified the requested profile path, resolved the actual Desktop, inspected gzip headers and sample rows, and moved only schema-confirmed files.",
        "- Streamed the graph and used 128 temporary disk partitions for exact duplicate and unique-pair counts.", "",
        "**FILES MOVED**", "",
    ]
    lines += table_md(["Filename", "Bytes", "Original location", "New location"], moved)
    lines += [
        "", "**RESULT**", "",
        f"- Neurons: {graph['unique_neurons']:,}; records: {graph['valid']:,}; unique directed pairs: {graph['unique_pairs']:,}; total `syn_count`: {graph['total_weight']:,}.",
        f"- Malformed rows: {graph['malformed']:,}; exact duplicate excess rows: {graph['duplicate_exact_excess']:,}.", "",
        "**ERRORS**", "",
        "- `C:\\Users\\Hamzah` was absent. A first read-only PowerShell path check had a parser error and changed no files.",
        "- Cell Types and Classification / Hierarchical Annotations exports were absent.", "",
        "**WHAT WORKED**", "", "- Three files moved with identical byte sizes; the analyzer completed and wrote the initial report.", "",
        "**WHAT FAILED**", "", "- Classification-based sensory and descending-neuron selection was impossible with the current files.", "",
        "**ASSUMPTIONS**", "",
        "- Dataset identity comes from the brief; `syn_count` is reported as aggregate connection weight; the OS-resolved Desktop substitutes for the nonexistent requested profile path.", "",
        "**PERFORMANCE**", "", f"- End-to-end time: {elapsed:.3f} seconds; peak observed working set: {bytes_label(graph['peak_rss'])}.", "",
        "**NEXT STEP**", "", "Stop after Phase 1. Locate the missing exports, review this report, and wait for explicit Phase 2 approval.", "",
    ]
    with (root / "DEVELOPMENT_LOG.md").open("a", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--no-log", action="store_true", help="Do not append DEVELOPMENT_LOG.md")
    args = parser.parse_args()
    root = args.project_root.resolve()
    data = root / "data"
    paths = sorted(path for path in data.iterdir() if path.is_file() and ".csv" in path.name.lower())
    if not paths:
        print(f"No CSV tables in {data}", file=sys.stderr)
        return 2
    started = time.perf_counter()
    tables = [inspect(path) for path in paths]
    print(f"Detected {len(tables)} tables:", flush=True)
    for item in tables:
        print(f"  {item.path.name}: {item.role} {item.header}", flush=True)
    connections = [table for table in tables if table.role == "connections"]
    if len(connections) != 1:
        raise RuntimeError(f"Expected one connection table, found {len(connections)}")
    summaries: dict[str, dict[str, object]] = {}
    metadata: dict[int, dict[str, str]] = {}
    visual: dict[int, dict[str, str]] = {}
    for item in tables:
        if item.role == "connections":
            continue
        print(f"Scanning {item.path.name}...", flush=True)
        summary, records = scan_metadata(item)
        summaries[item.path.name] = summary
        if item.role == "neurotransmitter_predictions":
            metadata.update(records)
        elif item.role == "visual_annotations":
            visual.update(records)
    print("Scanning connection graph...", flush=True)
    graph = scan_connections(connections[0], metadata, visual, Path(tempfile.gettempdir()))
    elapsed = time.perf_counter() - started
    docs = root / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    report = docs / "initial_data_report.md"
    report.write_text(report_text(tables, summaries, graph, elapsed), encoding="utf-8", newline="\n")
    if not args.no_log:
        append_log(root, tables, graph, elapsed)
    print(f"Report written: {report}", flush=True)
    print(f"RESULT neurons={graph['unique_neurons']:,} records={graph['valid']:,} pairs={graph['unique_pairs']:,} weight={graph['total_weight']:,} seconds={elapsed:.3f}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
