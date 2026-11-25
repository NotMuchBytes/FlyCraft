#!/usr/bin/env python3
"""Build a deterministic all-neuron CSR graph from raw Codex CSV exports."""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
import platform
import sys
import threading
import time
from pathlib import Path

import numpy as np
import psutil
import scipy
from scipy import sparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from simulator.graph import NT_NAME_TO_CODE, sparse_nbytes


DATA = ROOT / "data"
OUT = DATA / "processed"
CONNECTIONS = DATA / "connections_princeton_no_threshold.csv.gz"
NEURONS = DATA / "neurons.csv.gz"
EXPECTED_RECORDS = 22_285_323
EXPECTED_PAIRS = 19_773_733
EXPECTED_WEIGHT = 76_944_499
EXPECTED_METADATA_NEURONS = 139_255


class PeakRSS:
    def __init__(self, interval: float = 0.05) -> None:
        self.process = psutil.Process()
        self.interval = interval
        self.peak = self.process.memory_info().rss
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._sample, daemon=True)

    def _sample(self) -> None:
        while not self._stop.wait(self.interval):
            self.peak = max(self.peak, self.process.memory_info().rss)

    def __enter__(self) -> "PeakRSS":
        self._thread.start()
        return self

    def __exit__(self, *_args) -> None:
        self._stop.set()
        self._thread.join()
        self.peak = max(self.peak, self.process.memory_info().rss)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_metadata() -> tuple[np.ndarray, np.ndarray, dict[int, int], dict[int, str]]:
    rows: list[tuple[int, str]] = []
    with gzip.open(NEURONS, "rt", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            rows.append((int(row["root_id"]), row["nt_type"].strip().upper()))
    rows.sort(key=lambda item: item[0])
    root_ids = np.fromiter((rid for rid, _ in rows), dtype=np.uint64, count=len(rows))
    if root_ids.size != EXPECTED_METADATA_NEURONS or np.any(root_ids[1:] <= root_ids[:-1]):
        raise RuntimeError("metadata root IDs are not the expected unique population")
    nt_codes = np.fromiter(
        (NT_NAME_TO_CODE.get(nt or "UNKNOWN", 0) for _, nt in rows),
        dtype=np.uint8,
        count=len(rows),
    )
    rid_to_index = {int(rid): index for index, rid in enumerate(root_ids)}
    rid_to_nt = {rid: nt for rid, nt in rows}
    return root_ids, nt_codes, rid_to_index, rid_to_nt


def count_records() -> int:
    with gzip.open(CONNECTIONS, "rb") as handle:
        return sum(1 for _ in handle) - 1


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    with PeakRSS() as memory:
        root_ids, nt_codes, rid_to_index, rid_to_nt = load_metadata()
        print(f"loaded deterministic index for {root_ids.size:,} metadata neurons", flush=True)
        record_count = count_records()
        print(f"counted {record_count:,} connection records", flush=True)
        if record_count != EXPECTED_RECORDS:
            raise RuntimeError(f"expected {EXPECTED_RECORDS:,} records, found {record_count:,}")

        pre = np.empty(record_count, dtype=np.int32)
        post = np.empty(record_count, dtype=np.int32)
        weights = np.empty(record_count, dtype=np.uint32)
        edge_nt_matches = edge_nt_mismatches = edge_nt_blank_pre = 0
        with gzip.open(CONNECTIONS, "rt", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            for index, row in enumerate(reader):
                pre_rid = int(row["pre_root_id"])
                post_rid = int(row["post_root_id"])
                try:
                    pre[index] = rid_to_index[pre_rid]
                    post[index] = rid_to_index[post_rid]
                except KeyError as error:
                    raise RuntimeError(f"graph ID absent from metadata: {error.args[0]}") from error
                weights[index] = int(row["syn_count"])
                metadata_nt = rid_to_nt[pre_rid]
                edge_nt = row["nt_type"].strip().upper()
                if not metadata_nt:
                    edge_nt_blank_pre += 1
                elif metadata_nt == edge_nt:
                    edge_nt_matches += 1
                else:
                    edge_nt_mismatches += 1
                if (index + 1) % 1_000_000 == 0:
                    print(f"  parsed {index + 1:,} records", flush=True)

        coo = sparse.coo_matrix(
            (weights, (post, pre)),
            shape=(root_ids.size, root_ids.size),
            dtype=np.uint32,
        )
        del pre, post, weights
        print("aggregating repeated pre/post records into CSR...", flush=True)
        csr = coo.tocsr()
        del coo
        csr.sum_duplicates()
        csr.sort_indices()
        total_weight = int(csr.sum(dtype=np.uint64))
        if csr.nnz != EXPECTED_PAIRS:
            raise RuntimeError(f"expected {EXPECTED_PAIRS:,} pairs, found {csr.nnz:,}")
        if total_weight != EXPECTED_WEIGHT:
            raise RuntimeError(f"expected total weight {EXPECTED_WEIGHT:,}, found {total_weight:,}")

        graph_path = OUT / "connectome_raw_csr.npz"
        index_path = OUT / "neuron_index.npz"
        sparse.save_npz(graph_path, csr, compressed=True)
        np.savez_compressed(index_path, root_ids=root_ids, nt_codes=nt_codes)
        disconnected = int(np.count_nonzero((np.diff(csr.indptr) + np.bincount(csr.indices, minlength=root_ids.size)) == 0))
        elapsed = time.perf_counter() - started
        metadata = {
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "source_files": {
                CONNECTIONS.name: {"bytes": CONNECTIONS.stat().st_size, "sha256": sha256(CONNECTIONS)},
                NEURONS.name: {"bytes": NEURONS.stat().st_size, "sha256": sha256(NEURONS)},
            },
            "index_rule": "all metadata root_ids sorted ascending",
            "matrix_orientation": "CSR row=postsynaptic dense index, column=presynaptic dense index",
            "aggregation": "sum syn_count across all neuropils for each directed pre/post pair",
            "neuron_count": int(root_ids.size),
            "connection_records": record_count,
            "unique_directed_pairs": int(csr.nnz),
            "aggregate_syn_count": total_weight,
            "disconnected_neurons": disconnected,
            "csr": {
                "shape": list(csr.shape), "data_dtype": str(csr.data.dtype),
                "index_dtype": str(csr.indices.dtype), "memory_bytes": sparse_nbytes(csr),
                "saved_bytes": graph_path.stat().st_size,
            },
            "index_saved_bytes": index_path.stat().st_size,
            "edge_nt_vs_presynaptic_metadata": {
                "matches_when_metadata_nonblank": edge_nt_matches,
                "mismatches_when_metadata_nonblank": edge_nt_mismatches,
                "records_with_blank_presynaptic_metadata_nt": edge_nt_blank_pre,
            },
            "build_seconds": elapsed,
            "peak_process_rss_bytes": memory.peak,
        }
        (OUT / "build_metadata.json").write_text(
            json.dumps(metadata, indent=2) + "\n", encoding="utf-8", newline="\n"
        )
    print(json.dumps(metadata, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
