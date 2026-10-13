# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Dossier index tests.
Verify index creation, append, duplicate avoidance, and metadata extraction.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from runtime.dossier.index_manager import (
    _load_index,
    _extract_entry,
    update_dossier_index,
)


def test_index_file_creation() -> None:
    """Index is created with dossiers array when first dossier is added."""
    import tempfile
    tmp = Path(tempfile.mkdtemp())
    idx = tmp / "dossier_index.json"
    dossier_path = tmp / "dossier.json"
    dossier_path.write_text(
        json.dumps({
            "dossier_checksum": "ff" * 32,
            "meta": {"engine_version": "0.1", "generation_timestamp": "2026-01-01T00:00:00Z"},
        }, indent=2),
        encoding="utf-8",
    )
    assert not idx.exists()
    update_dossier_index(dossier_path, idx)
    assert idx.exists()
    parsed = json.loads(idx.read_text(encoding="utf-8"))
    assert "dossiers" in parsed and len(parsed["dossiers"]) == 1


def test_new_entries_appended() -> None:
    """update_dossier_index appends a new entry to the index."""
    import tempfile
    tmp = Path(tempfile.mkdtemp())
    index_path = tmp / "index.json"
    dossier_path = tmp / "d1.json"
    dossier = {
        "dossier_checksum": "aa" * 32,
        "meta": {
            "engine_version": "1.0.0",
            "generation_timestamp": "2026-03-11T12:00:00Z",
            "run_manifest": {"policy_mode": "STRUCTURE_ONLY"},
        },
    }
    dossier_path.write_text(json.dumps(dossier, indent=2), encoding="utf-8")
    update_dossier_index(dossier_path, index_path)
    data = _load_index(index_path)
    assert len(data["dossiers"]) == 1
    assert data["dossiers"][0]["checksum"] == "aa" * 32
    assert data["dossiers"][0]["engine_version"] == "1.0.0"
    assert data["dossiers"][0]["policy_mode"] == "STRUCTURE_ONLY"
    # Second dossier appends
    d2 = tmp / "d2.json"
    dossier2 = {
        "dossier_checksum": "bb" * 32,
        "meta": {
            "engine_version": "1.0.1",
            "generation_timestamp": "2026-03-11T13:00:00Z",
            "run_manifest": {"policy_mode": "FULL_INTERPRETATION"},
        },
    }
    d2.write_text(json.dumps(dossier2, indent=2), encoding="utf-8")
    update_dossier_index(d2, index_path)
    data = _load_index(index_path)
    assert len(data["dossiers"]) == 2


def test_duplicates_avoided() -> None:
    """Entries with the same checksum are not added twice."""
    import tempfile
    tmp = Path(tempfile.mkdtemp())
    index_path = tmp / "index.json"
    dossier_path = tmp / "dup.json"
    dossier = {
        "dossier_checksum": "cc" * 32,
        "meta": {
            "engine_version": "2.0.0",
            "generation_timestamp": "2026-03-11T14:00:00Z",
            "run_manifest": {"policy_mode": "STRUCTURE_PLUS_CONTEXT"},
        },
    }
    dossier_path.write_text(json.dumps(dossier, indent=2), encoding="utf-8")
    update_dossier_index(dossier_path, index_path)
    update_dossier_index(dossier_path, index_path)
    data = _load_index(index_path)
    assert len(data["dossiers"]) == 1
    # Same checksum, different path (e.g. copy) still should not add
    d2 = tmp / "dup_copy.json"
    d2.write_text(json.dumps(dossier, indent=2), encoding="utf-8")
    update_dossier_index(d2, index_path)
    data = _load_index(index_path)
    assert len(data["dossiers"]) == 1


def test_metadata_extracted_correctly() -> None:
    """_extract_entry and index entries have path, checksum, engine_version, policy_mode, timestamp, document_anomaly."""
    dossier = {
        "dossier_checksum": "dd" * 32,
        "meta": {
            "engine_version": "3.0.0",
            "generation_timestamp": "2026-03-11T15:00:00Z",
            "run_manifest": {"policy_mode": "FULL_INTERPRETATION"},
        },
        "global_structure": {"document_anomaly": 0.42},
    }
    entry = _extract_entry(dossier, "/path/to/dossier.json")
    assert entry["path"] == "/path/to/dossier.json"
    assert entry["checksum"] == "dd" * 32
    assert entry["engine_version"] == "3.0.0"
    assert entry["policy_mode"] == "FULL_INTERPRETATION"
    assert entry["generation_timestamp"] == "2026-03-11T15:00:00Z"
    assert entry["document_anomaly"] == 0.42

    # Without global_structure / run_manifest still works
    dossier2 = {"dossier_checksum": "ee" * 32, "meta": {"engine_version": "x", "generation_timestamp": "2026-01-01T00:00:00Z"}}
    entry2 = _extract_entry(dossier2, "/other.json")
    assert entry2["policy_mode"] == ""
    assert entry2["document_anomaly"] is None
