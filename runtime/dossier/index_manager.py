# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""
HESPERIA dossier index manager.
Maintains a machine-readable index of generated dossiers for discovery and comparison.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

DEFAULT_INDEX_PATH = Path(__file__).resolve().parent / "dossier_index.json"


def _load_index(index_path: Path) -> Dict[str, Any]:
    """Load index from path; return {dossiers: []} if missing or invalid."""
    if not index_path.exists():
        return {"dossiers": []}
    try:
        data = json.loads(index_path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and "dossiers" in data and isinstance(data["dossiers"], list):
            return data
    except (json.JSONDecodeError, OSError):
        pass
    return {"dossiers": []}


def _save_index(index_path: Path, data: Dict[str, Any]) -> None:
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(
        json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _extract_entry(dossier: Dict[str, Any], path_str: str) -> Dict[str, Any]:
    """Build index entry from dossier dict and dossier file path."""
    checksum = dossier.get("dossier_checksum") or dossier.get("meta", {}).get("dossier_checksum")
    meta = dossier.get("meta") or {}
    dossier_id = meta.get("dossier_id", "")
    engine_version = meta.get("engine_version", "")
    generation_timestamp = meta.get("generation_timestamp", "")
    policy_mode = (meta.get("run_manifest") or {}).get("policy_mode", "")
    gs = dossier.get("global_structure") or {}
    document_anomaly = gs.get("document_anomaly")
    return {
        "path": path_str,
        "checksum": checksum or "",
        "dossier_id": dossier_id,
        "engine_version": engine_version,
        "policy_mode": policy_mode,
        "generation_timestamp": generation_timestamp,
        "document_anomaly": document_anomaly,
    }


def update_dossier_index(
    dossier_path: Path | str,
    index_path: Path | str | None = None,
) -> None:
    """
    Read the dossier at dossier_path, extract metadata, append to index.
    Skips appending if an entry with the same checksum already exists.
    """
    index_path = Path(index_path) if index_path is not None else DEFAULT_INDEX_PATH
    dossier_path = Path(dossier_path)
    if not dossier_path.exists():
        return
    try:
        dossier = json.loads(dossier_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return
    path_str = str(dossier_path.resolve())
    entry = _extract_entry(dossier, path_str)
    checksum = entry.get("checksum") or ""
    data = _load_index(index_path)
    dossiers: List[Dict[str, Any]] = data["dossiers"]
    if checksum and any(e.get("checksum") == checksum for e in dossiers):
        return
    dossiers.append(entry)
    _save_index(index_path, data)


def list_dossiers(index_path: Path | str | None = None) -> None:
    """Print table: timestamp | engine | policy | anomaly | file."""
    index_path = Path(index_path) if index_path is not None else DEFAULT_INDEX_PATH
    data = _load_index(index_path)
    dossiers = data.get("dossiers") or []
    if not dossiers:
        print("No dossiers in index.", file=sys.stderr)
        return
    # Header
    fmt = "{:<24} {:<12} {:<22} {:>10} {}"
    print(fmt.format("timestamp", "engine", "policy", "anomaly", "file"))
    for e in dossiers:
        ts = (e.get("generation_timestamp") or "")[:24]
        eng = (e.get("engine_version") or "")[:12]
        pol = (e.get("policy_mode") or "")[:22]
        anom = e.get("document_anomaly")
        anom_str = f"{anom:.4f}" if isinstance(anom, (int, float)) else ""
        path = e.get("path") or ""
        print(fmt.format(ts, eng, pol, anom_str, path))


def main() -> None:
    import argparse
    p = argparse.ArgumentParser(prog="python -m runtime.dossier.index_manager")
    p.add_argument("command", choices=["list"], help="list: print index table")
    p.add_argument("--index", type=Path, default=None, help="Index file path (default: runtime/dossier/dossier_index.json)")
    args = p.parse_args()
    if args.command == "list":
        list_dossiers(args.index)


if __name__ == "__main__":
    main()
