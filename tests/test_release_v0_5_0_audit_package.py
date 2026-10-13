# HESPERIA — Task 5: release/v0.5.0 audit package structure (when present).
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

from __future__ import annotations

import json
from pathlib import Path

import pytest

_RELEASE = Path(__file__).resolve().parents[1] / "release" / "v0.5.0"


@pytest.mark.skipif(not (_RELEASE / "manifest.json").is_file(), reason="run tools/release/build_release_audit_v0_5_0.py first")
def test_manifest_has_required_task5_fields() -> None:
    m = json.loads((_RELEASE / "manifest.json").read_text(encoding="utf-8"))
    assert m.get("system_version") == "0.5.0"
    assert m.get("determinism_expected") is True
    assert m.get("determinism_verified") is True
    assert m.get("determinism_e2e_sha256")
    assert m.get("calibration_profile_default")
    aa = m.get("audit_artifacts") or {}
    assert aa.get("system_seal") == "system_seal.json"
    assert "modules" in m
    assert m["modules"].get("research") == "excluded"
    routes = m.get("shipping_api_routes") or []
    assert any("POST /analyze" in r for r in routes)
    assert any("POST /compare" in r for r in routes)
    assert any("POST /batch" in r for r in routes)
    assert not any("/docs" in r for r in routes)
    assert not any("openapi" in r.lower() for r in routes)


@pytest.mark.skipif(not (_RELEASE / "checksums.txt").is_file(), reason="audit package missing")
def test_checksums_lists_files() -> None:
    txt = (_RELEASE / "checksums.txt").read_text(encoding="utf-8")
    assert "manifest.json" in txt
    assert "  manifest.json" in txt or txt.count("manifest.json") >= 1


@pytest.mark.skipif(not (_RELEASE / "e2e_reference_output.json").is_file(), reason="audit package missing")
def test_e2e_reference_has_version_envelope() -> None:
    d = json.loads((_RELEASE / "e2e_reference_output.json").read_text(encoding="utf-8"))
    assert d.get("system_version") == "0.5.0"
    assert "build_id" in d
    assert d.get("schema_version")


@pytest.mark.skipif(not (_RELEASE / "audit_report.json").is_file(), reason="audit package missing")
def test_audit_report_has_seal_decision() -> None:
    a = json.loads((_RELEASE / "audit_report.json").read_text(encoding="utf-8"))
    assert "seal_decision" in a
    assert "may_tag_v0_5_0" in a["seal_decision"]
    assert "reasons_fail" in a["seal_decision"]


@pytest.mark.skipif(not (_RELEASE / "determinism_report.json").is_file(), reason="audit package missing")
def test_determinism_report_pass() -> None:
    d = json.loads((_RELEASE / "determinism_report.json").read_text(encoding="utf-8"))
    assert d.get("pass") is True
    assert d.get("hash_match") is True


@pytest.mark.skipif(not (_RELEASE / "schema_validation_report.json").is_file(), reason="audit package missing")
def test_schema_validation_overall_pass() -> None:
    s = json.loads((_RELEASE / "schema_validation_report.json").read_text(encoding="utf-8"))
    assert s.get("overall_pass") is True


@pytest.mark.skipif(not (_RELEASE / "final_gate_status.json").is_file(), reason="audit package missing")
def test_final_gate_status_shape() -> None:
    fg = json.loads((_RELEASE / "final_gate_status.json").read_text(encoding="utf-8"))
    assert fg.get("system_version") == "0.5.0"
    assert "sealed" in fg
    assert "critical_checks" in fg
    for k in (
        "version_authority",
        "repo_topology",
        "spec_consolidation",
        "product_boundary",
        "determinism",
        "schema_validation",
        "release_audit",
        "system_seal",
    ):
        assert k in fg["critical_checks"]
