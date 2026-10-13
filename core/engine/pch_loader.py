# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# See LEGAL_NOTICE.md for full terms.

"""
Load governed **P_CH** from ``assets/matrices/pch/P_CH_v1.npz`` (+ manifest).

Uniform family→hex spreading is **not** a runtime fallback; missing or invalid **P_CH** raises
``RuntimeError``.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import numpy as np
from scipy.sparse import csr_matrix, issparse, load_npz

__all__ = ["default_pch_dir", "resolve_pch_dir", "load_pch"]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_pch_dir() -> Path:
    return _repo_root() / "assets" / "matrices" / "pch"


def resolve_pch_dir(explicit: Path | str | None = None) -> Path:
    if explicit is not None:
        return Path(explicit)
    env = os.environ.get("HESPERIA_PCH_DIR", "").strip()
    if env:
        return Path(env)
    return default_pch_dir()


def _assert_pch_manifest_matches_version_yaml(manifest: dict[str, Any]) -> None:
    try:
        from hesperia.system.version import pch_bundle_id
    except Exception:
        return
    expected = pch_bundle_id()
    got = str(manifest.get("version", ""))
    if got != expected:
        raise RuntimeError(
            f"P_CH manifest version {got!r} must match VERSION.yaml matrices.pch_bundle {expected!r}"
        )


def load_pch(directory: Path | str | None = None) -> csr_matrix:
    """
    Load **P_CH** CSR matrix and validate column normalization + sparsity.

    Raises:
        RuntimeError: missing files, shape mismatch, empty columns, column sums not ≈ 1,
        sparsity ≥ 1%, or VERSION binding failure.
    """
    d = resolve_pch_dir(directory)
    manifest_path = d / "P_CH_manifest.json"
    if not manifest_path.is_file():
        raise RuntimeError(
            f"Missing P_CH manifest: {manifest_path}. Run: python3 tools/matrices/build_pch_v1.py"
        )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    _assert_pch_manifest_matches_version_yaml(manifest)

    fname = manifest.get("file") or "P_CH_v1.npz"
    npz_path = d / str(fname)
    if not npz_path.is_file():
        raise RuntimeError(f"Missing P_CH sparse file: {npz_path}")

    mat = load_npz(npz_path)
    if not issparse(mat):
        raise RuntimeError("P_CH file must contain a scipy sparse matrix")
    mat = mat.tocsr()
    mat.sort_indices()
    mat.eliminate_zeros()

    n_hex = int(manifest.get("n_hex", 0))
    n_concepts = int(manifest.get("n_concepts", 0))
    if mat.shape != (n_hex, n_concepts):
        raise RuntimeError(f"P_CH shape {mat.shape} != manifest ({n_hex}, {n_concepts})")

    if not np.all(np.isfinite(mat.data)):
        raise RuntimeError("P_CH contains NaN or inf")

    col_sums = np.asarray(mat.sum(axis=0)).ravel()
    if col_sums.shape[0] != n_concepts:
        raise RuntimeError("P_CH column sum vector mismatch")
    if not np.all(col_sums > 1e-10):
        raise RuntimeError("P_CH has empty or near-zero columns")
    if not np.allclose(col_sums, 1.0, atol=1e-5, rtol=1e-8):
        raise RuntimeError("P_CH columns must sum to 1 (L1 normalization)")

    nnz = mat.nnz
    sparsity = float(nnz) / float(max(1, n_hex * n_concepts))
    if sparsity >= 0.01:
        raise RuntimeError(f"P_CH sparsity {sparsity} must be < 1% (nnz={nnz})")

    return mat
