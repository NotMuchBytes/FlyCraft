"""Sparse connectome representation and explicit model-layer transforms."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

import numpy as np
from scipy import sparse

from .config import WeightTransformConfig


NT_CODE_TO_NAME = {
    0: "UNKNOWN",
    1: "ACH",
    2: "GABA",
    3: "GLUT",
    4: "DA",
    5: "SER",
    6: "OCT",
}
NT_NAME_TO_CODE = {name: code for code, name in NT_CODE_TO_NAME.items()}


def sparse_nbytes(matrix: sparse.spmatrix) -> int:
    csr = matrix.tocsr(copy=False)
    return int(csr.data.nbytes + csr.indices.nbytes + csr.indptr.nbytes)


def transform_weights(
    raw: sparse.spmatrix, config: WeightTransformConfig
) -> sparse.csr_matrix:
    """Return a float32 CSR matrix after a documented engineering transform."""

    if config.scale < 0:
        raise ValueError("weight scale must be non-negative")
    if config.cap <= 0:
        raise ValueError("weight cap must be positive")
    result = raw.astype(np.float32, copy=True).tocsr()
    data = result.data
    if config.name == "raw":
        pass
    elif config.name == "sqrt":
        np.sqrt(data, out=data)
    elif config.name in {"log", "log1p"}:
        np.log1p(data, out=data)
    elif config.name == "clipped":
        np.minimum(data, np.float32(config.cap), out=data)
    elif config.name == "normalized_clipped":
        np.minimum(data, np.float32(config.cap), out=data)
        data /= np.float32(config.cap)
    else:
        raise ValueError(f"unknown weight transform: {config.name}")
    data *= np.float32(config.scale)
    return result


def build_source_gain(
    nt_codes: np.ndarray,
    *,
    mode: str = "unsigned",
    sign_map: Mapping[str, float] | None = None,
    unknown_policy: str = "positive",
) -> np.ndarray:
    """Build per-presynaptic-neuron gains for a configurable NT model layer.

    ``unsigned`` returns +1 for every source, including unknown values. The
    optional ``simplified_signed`` mode requires the caller to provide every
    transmitter sign explicitly; this project supplies no default sign map.
    Unknown values can be positive, zeroed, or rejected.
    """

    codes = np.asarray(nt_codes, dtype=np.uint8)
    if mode == "unsigned":
        if unknown_policy not in {"positive", "zero", "error"}:
            raise ValueError(f"unknown unknown_policy: {unknown_policy}")
        if unknown_policy == "error" and np.any(codes == 0):
            raise ValueError("unknown neurotransmitter codes are present")
        gains = np.ones(codes.shape, dtype=np.float32)
        if unknown_policy == "zero":
            gains[codes == 0] = 0.0
        return gains
    if mode != "simplified_signed":
        raise ValueError(f"unknown neurotransmitter mode: {mode}")
    if sign_map is None:
        raise ValueError("simplified_signed requires an explicit sign_map")
    gains = np.empty(codes.shape, dtype=np.float32)
    for code, name in NT_CODE_TO_NAME.items():
        mask = codes == code
        if not np.any(mask):
            continue
        if code == 0:
            if unknown_policy == "positive":
                gains[mask] = 1.0
            elif unknown_policy == "zero":
                gains[mask] = 0.0
            elif unknown_policy == "error":
                raise ValueError("unknown neurotransmitter codes are present")
            else:
                raise ValueError(f"unknown unknown_policy: {unknown_policy}")
        elif name in sign_map:
            gains[mask] = np.float32(sign_map[name])
        else:
            raise ValueError(f"sign_map has no value for {name}")
    return gains


@dataclass
class ConnectomeGraph:
    """Raw aggregate-count adjacency plus deterministic neuron metadata."""

    adjacency_raw: sparse.csr_matrix
    root_ids: np.ndarray
    nt_codes: np.ndarray

    @classmethod
    def load(cls, processed_dir: Path) -> "ConnectomeGraph":
        adjacency = sparse.load_npz(processed_dir / "connectome_raw_csr.npz").tocsr()
        with np.load(processed_dir / "neuron_index.npz", allow_pickle=False) as mapping:
            root_ids = mapping["root_ids"].astype(np.uint64, copy=False)
            nt_codes = mapping["nt_codes"].astype(np.uint8, copy=False)
        if adjacency.shape != (root_ids.size, root_ids.size):
            raise ValueError("adjacency shape does not match neuron index")
        if nt_codes.size != root_ids.size:
            raise ValueError("nt_codes length does not match neuron index")
        return cls(adjacency, root_ids, nt_codes)

    def dense_index(self, root_id: int) -> int:
        position = int(np.searchsorted(self.root_ids, np.uint64(root_id)))
        if position >= self.root_ids.size or int(self.root_ids[position]) != root_id:
            raise KeyError(root_id)
        return position

    @property
    def neuron_count(self) -> int:
        return int(self.root_ids.size)

    @property
    def edge_count(self) -> int:
        return int(self.adjacency_raw.nnz)

    @property
    def raw_memory_bytes(self) -> int:
        return sparse_nbytes(self.adjacency_raw)
