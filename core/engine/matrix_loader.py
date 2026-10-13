# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# See LEGAL_NOTICE.md for full terms.

"""
Authoritative production interaction matrices (L_F, C_F, R_F).

Loads versioned ``.npy`` bundles from ``assets/matrices/production/`` (or
``HESPERIA_PRODUCTION_MATRICES_DIR``). No stub fallback — missing or invalid matrices raise
``RuntimeError``.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import numpy as np

NUM_FAMILIES_CANON = 288


def _assert_matrix_bundle_matches_version_yaml(manifest: dict[str, Any]) -> None:
    try:
        from hesperia.system.version import production_matrix_bundle_id
    except Exception:
        return
    expected = production_matrix_bundle_id()
    got = str(manifest.get("version", ""))
    if got != expected:
        raise RuntimeError(
            f"matrix_manifest.json version {got!r} must match VERSION.yaml matrices.production_bundle "
            f"{expected!r}"
        )


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_production_matrix_dir() -> Path:
    return _repo_root() / "assets" / "matrices" / "production"


def resolve_production_matrix_dir(explicit: Path | str | None = None) -> Path:
    if explicit is not None:
        return Path(explicit)
    env = os.environ.get("HESPERIA_PRODUCTION_MATRICES_DIR", "").strip()
    if env:
        return Path(env)
    return default_production_matrix_dir()


def _validate_l_f(l_f: np.ndarray, *, n: int) -> None:
    if l_f.shape != (n, n):
        raise RuntimeError(f"L_F shape must be ({n},{n}), got {l_f.shape}")
    if not np.all(np.isfinite(l_f)):
        raise RuntimeError("L_F contains NaN or inf")
    sym = np.max(np.abs(l_f - l_f.T))
    if sym > 1e-5 * max(1.0, np.max(np.abs(l_f))):
        raise RuntimeError(f"L_F not symmetric within tolerance (max skew {sym})")
    row_sums = np.abs(l_f.sum(axis=1))
    if float(np.max(row_sums)) > 1e-4:
        raise RuntimeError("L_F row sums must be ~0 (Laplacian property)")
    if float(np.max(np.abs(l_f))) < 1e-15:
        raise RuntimeError("L_F is all zeros — forbidden")
    w = np.linalg.eigvalsh(0.5 * (l_f + l_f.T))
    if w[0] < -1e-5:
        raise RuntimeError("L_F has unexpected negative eigenvalues")
    if w[-1] < 1e-12:
        raise RuntimeError("L_F trivial (max eigenvalue ~0)")


def _validate_c_f(c_f: np.ndarray, *, n: int) -> None:
    if c_f.shape != (n, n):
        raise RuntimeError(f"C_F shape must be ({n},{n}), got {c_f.shape}")
    if not np.all(np.isfinite(c_f)):
        raise RuntimeError("C_F contains NaN or inf")
    if np.any(c_f < -1e-12):
        raise RuntimeError("C_F must be non-negative (within numerical tolerance)")
    sym = np.max(np.abs(c_f - c_f.T))
    if sym > 1e-5 * max(1.0, np.max(np.abs(c_f))):
        raise RuntimeError(f"C_F not symmetric within tolerance (max skew {sym})")
    off = c_f.copy()
    np.fill_diagonal(off, 0.0)
    if float(np.max(np.abs(off))) < 1e-12:
        raise RuntimeError("C_F has no non-zero off-diagonal entries — contradiction inactive")


def _validate_r_f(r_f: np.ndarray, *, n: int) -> None:
    if r_f.shape != (n, n):
        raise RuntimeError(f"R_F shape must be ({n},{n}), got {r_f.shape}")
    if not np.all(np.isfinite(r_f)):
        raise RuntimeError("R_F contains NaN or inf")
    diag = np.diag(r_f)
    if np.any(diag < -1e-12):
        raise RuntimeError("R_F diagonal must be non-negative")
    off = r_f - np.diag(diag)
    if float(np.max(np.abs(off))) > 1e-8 * max(1.0, float(np.max(np.abs(diag))) or 1.0):
        raise RuntimeError("R_F must be diagonal (structured damping)")
    if float(np.min(diag)) < 1e-12:
        raise RuntimeError("R_F diagonal must be strictly positive in production")


def load_production_matrices(
    directory: Path | str | None = None,
    *,
    families: int = NUM_FAMILIES_CANON,
) -> dict[str, Any]:
    """
    Load and validate production matrices from ``matrix_manifest.json`` + companion ``.npy`` files.

    Returns:
        dict with keys ``L_F``, ``R_F``, ``C_F``, ``C`` (alias of ``C_F`` for legacy callers),
        ``W_F`` optional if present in manifest,
        ``bundle_version``, ``manifest``, ``matrix_directory``.
    """
    d = resolve_production_matrix_dir(directory)
    manifest_path = d / "matrix_manifest.json"
    if not manifest_path.is_file():
        raise RuntimeError(
            f"Missing production matrix manifest: {manifest_path}. "
            "Run: python3 tools/matrices/build_production_matrices_v1.py"
        )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    _assert_matrix_bundle_matches_version_yaml(manifest)
    files = manifest.get("files") or {}
    if not isinstance(files, dict):
        raise RuntimeError("matrix_manifest.json: 'files' must be an object")

    def _load_key(key: str) -> np.ndarray:
        name = files.get(key)
        if not name:
            raise RuntimeError(f"matrix_manifest.json missing files.{key}")
        path = d / str(name)
        if not path.is_file():
            raise RuntimeError(f"Missing production matrix file: {path}")
        arr = np.load(path, allow_pickle=False)
        if not isinstance(arr, np.ndarray):
            raise RuntimeError(f"{path} did not load as ndarray")
        return np.asarray(arr, dtype=np.float64)

    l_f = _load_key("L_F")
    c_f = _load_key("C_F")
    r_f = _load_key("R_F")

    mf = int(manifest.get("families", families))
    if mf != families:
        raise RuntimeError(f"Manifest families={mf} != expected {families}")

    _validate_l_f(l_f, n=families)
    _validate_c_f(c_f, n=families)
    _validate_r_f(r_f, n=families)

    out: dict[str, Any] = {
        "L_F": l_f,
        "R_F": r_f,
        "C_F": c_f,
        "C": c_f,
        "bundle_version": str(manifest.get("version", "v1")),
        "manifest": manifest,
        "matrix_directory": d.resolve(),
    }

    if "W_F" in files and files["W_F"]:
        out["W_F"] = _load_key("W_F")

    opt = manifest.get("optional_files") or {}
    if isinstance(opt, dict):
        for hex_key in ("L_H", "C_H"):
            fn = opt.get(hex_key)
            if fn:
                p = d / str(fn)
                if p.is_file():
                    out[hex_key] = np.load(p, allow_pickle=False)

    return out
