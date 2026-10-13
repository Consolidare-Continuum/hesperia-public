# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Deterministic dossier artifact (HSD) tests.
Verify canonical JSON, checksum correctness, and verification.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from runtime.dossier.dossier_writer import (
    CHECKSUM_KEY,
    SCHEMA_VERSION_KEY,
    write_dossier_json,
    _canonical_json,
)
from runtime.dossier.validate_schema import validate_dossier_schema
from runtime.dossier.verify_dossier import verify_dossier_checksum


def test_deterministic_json_output() -> None:
    """Same dossier written twice produces identical bytes (sort_keys, no random ordering)."""
    dossier = {"run": "L1_through_L9", "L1": {"DOMINANT_AREA_ID": 0}, "L9": {"BRAND_WORD_TRUST": "FRAGILE"}}
    path1 = _REPO / "tests" / "_dossier_det_1.json"
    path2 = _REPO / "tests" / "_dossier_det_2.json"
    try:
        write_dossier_json(dossier, path1)
        write_dossier_json(dossier, path2)
        b1 = path1.read_bytes()
        b2 = path2.read_bytes()
        assert b1 == b2
    finally:
        path1.unlink(missing_ok=True)
        path2.unlink(missing_ok=True)


def test_checksum_correctness() -> None:
    """Written dossier contains schema_version and dossier_checksum; verify_dossier_checksum passes."""
    dossier = {"run": "test", "L1": {"x": 1}}
    path = _REPO / "tests" / "_dossier_checksum.json"
    try:
        write_dossier_json(dossier, path)
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data.get(SCHEMA_VERSION_KEY) == "HSD_v1.0"
        assert data.get(CHECKSUM_KEY)
        assert len(data[CHECKSUM_KEY]) == 64  # sha256 hex
        assert verify_dossier_checksum(path) is True
    finally:
        path.unlink(missing_ok=True)


def test_verification_passes_for_valid_dossier() -> None:
    """verify_dossier_checksum returns True for a freshly written dossier."""
    dossier = {"a": 1, "b": [2, 3]}
    path = _REPO / "tests" / "_dossier_valid.json"
    try:
        write_dossier_json(dossier, path)
        assert verify_dossier_checksum(path) is True
    finally:
        path.unlink(missing_ok=True)


def test_verification_fails_when_modified() -> None:
    """verify_dossier_checksum returns False when file content is modified after write."""
    dossier = {"run": "L1_through_L9", "L7": {"DECISION_STATUS_CODE": 0}}
    path = _REPO / "tests" / "_dossier_tampered.json"
    try:
        write_dossier_json(dossier, path)
        assert verify_dossier_checksum(path) is True
        text = path.read_text(encoding="utf-8")
        # Tamper: change one digit in payload (e.g. DECISION_STATUS_CODE 0 -> 1)
        text = text.replace('"DECISION_STATUS_CODE": 0', '"DECISION_STATUS_CODE": 1')
        path.write_text(text, encoding="utf-8")
        assert verify_dossier_checksum(path) is False
    finally:
        path.unlink(missing_ok=True)


def test_verification_fails_missing_file() -> None:
    """verify_dossier_checksum returns False for missing path."""
    assert verify_dossier_checksum(_REPO / "nonexistent_dossier_xyz.json") is False


def test_canonical_has_sort_keys() -> None:
    """_canonical_json produces deterministic key order."""
    obj = {"z": 1, "a": 2, "m": 3}
    s = _canonical_json(obj)
    parsed = json.loads(s)
    keys = list(parsed.keys())
    assert keys == sorted(keys)


def test_validate_single_run_dossier() -> None:
    """validate_dossier_schema accepts valid single-run dossier."""
    dossier = {
        "run": "L1_through_L9",
        "text_preview": "abc",
        "diagnostics": {},
    }
    for i in range(1, 10):
        dossier[f"L{i}"] = {}
    assert validate_dossier_schema(dossier) is True


def test_validate_single_run_fails_missing_layer() -> None:
    """validate_dossier_schema raises for single-run missing L5."""
    dossier = {
        "run": "L1_through_L9",
        "text_preview": "abc",
        "diagnostics": {},
    }
    for i in range(1, 10):
        if i != 5:
            dossier[f"L{i}"] = {}
    try:
        validate_dossier_schema(dossier)
        assert False, "expected ValueError"
    except ValueError as e:
        assert "L5" in str(e)


def test_validate_multiscale_dossier() -> None:
    """validate_dossier_schema accepts valid multiscale dossier."""
    segment = {"diagnostics": {}}
    for i in range(1, 10):
        segment[f"L{i}"] = {}
    dossier = {
        "R1": [segment],
        "R2": [segment],
        "R3": [segment],
        "R4": [segment],
        "global_structure": {
            "dominant_area_distribution": {"0": 1.0},
            "stable_family_core": [15],
            "tension_axes": [0],
            "confidence_profile": {"mean_confidence": 0.5, "min_confidence": 0.0, "max_confidence": 1.0, "trust_tag_distribution": {}},
            "document_anomaly": 0.0,
        },
    }
    assert validate_dossier_schema(dossier) is True


def test_validate_multiscale_fails_missing_global_key() -> None:
    """validate_dossier_schema raises for multiscale missing document_anomaly."""
    segment = {"diagnostics": {}}
    for i in range(1, 10):
        segment[f"L{i}"] = {}
    dossier = {
        "R1": [segment],
        "R2": [segment],
        "R3": [segment],
        "R4": [segment],
        "global_structure": {
            "dominant_area_distribution": {},
            "stable_family_core": [],
            "tension_axes": [],
            "confidence_profile": {},
            # missing document_anomaly
        },
    }
    try:
        validate_dossier_schema(dossier)
        assert False, "expected ValueError"
    except ValueError as e:
        assert "document_anomaly" in str(e)
