from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any


def resolve_calibration_version(explicit: str | None = None) -> str | None:
    v = (explicit or os.environ.get("HESPERIA_CALIB_DICT_VERSION") or "").strip()
    return v or None


def resolve_calibration_dir(repo_root: Path, explicit: str | None = None) -> Path | None:
    version = resolve_calibration_version(explicit)
    if not version:
        return None
    d = repo_root / "assets" / "calibration" / "dicts" / version
    return d if d.is_dir() else None


def resolve_dict_file(repo_root: Path, filename: str, explicit_version: str | None = None) -> Path | None:
    d = resolve_calibration_dir(repo_root, explicit=explicit_version)
    if d is None:
        return None
    p = d / filename
    return p if p.is_file() else None


def resolve_metrics_file(repo_root: Path, explicit_version: str | None = None) -> Path | None:
    d = resolve_calibration_dir(repo_root, explicit=explicit_version)
    if d is None:
        return None

    preferred = d / "metrics.json"
    if preferred.is_file():
        return preferred

    fallback = d / "metrics_baseline_v052_2.json"
    if fallback.is_file():
        return fallback

    candidates = sorted(
        (p for p in d.glob("metrics_baseline*.json") if p.is_file()),
        key=lambda p: (p.stat().st_mtime, p.name),
        reverse=True,
    )
    return candidates[0] if candidates else None


def resolve_dict_d_file(repo_root: Path, explicit_version: str | None = None) -> Path | None:
    """Resolve the current calibration version's ``dict_d.jsonl`` (CORE-D2 W8, CORE-D2-080).

    A present file here does not enable Dict D — see ``calibration_manifest``'s
    hardcoded ``dict_d_enabled: False``; activation is a separate W9 gate.
    """
    return resolve_dict_file(repo_root, "dict_d.jsonl", explicit_version)


def calibration_manifest(repo_root: Path, explicit_version: str | None = None) -> dict[str, Any]:
    d = resolve_calibration_dir(repo_root, explicit=explicit_version)
    if d is None:
        return {"enabled": False}
    metrics = resolve_metrics_file(repo_root, explicit_version=explicit_version)
    dict_d = resolve_dict_d_file(repo_root, explicit_version=explicit_version)
    dict_d_hash = hashlib.sha256(dict_d.read_bytes()).hexdigest() if dict_d else None
    return {
        "enabled": True,
        "version": d.name,
        "dict_a": str((d / "dict_a.jsonl")),
        "dict_b": str((d / "dict_b.jsonl")),
        "links": str((d / "links.jsonl")),
        "metrics": str(metrics) if metrics else "",
        "metrics_filename": metrics.name if metrics else None,
        "metrics_exists": metrics is not None,
        # CORE-D2 W8 (CORE-D2-080): path/hash are provenance only. Dict D is never
        # loaded into a live runtime context by this manifest alone -- activation
        # is a separate W9 gate (ETHAN-CORE-D2-REAL-DICT-D-PROGRAM-CONTRACT.md).
        "dict_d": str(dict_d) if dict_d else None,
        "dict_d_hash": dict_d_hash,
        "dict_d_enabled": False,
    }
