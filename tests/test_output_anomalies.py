# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

from __future__ import annotations

from core.engine.output_anomalies import (
    apply_session_envelopes,
    assess_structural_row,
    cross_plane_codes,
    default_operational_envelope,
)


def test_default_envelope_has_required_keys() -> None:
    e = default_operational_envelope()
    for k in (
        "status",
        "anomaly_codes",
        "severity",
        "blocking",
        "operator_message",
        "recommended_next_check",
        "taxonomy_version",
    ):
        assert k in e


def test_cross_plane_detects_split_brain() -> None:
    struct = {
        "payload": {
            "L1": {"ATTRIBUTED_TOKENS": 0, "COVERAGE_RATIO": 0.0},
            "diagnostics": {"calibration_status": {}},
        }
    }
    an = {"extended": {"attribution_coverage": 1.0}}
    assert "A007_CROSS_PLANE_INCONSISTENCY" in cross_plane_codes(struct, None, an)


def test_apply_session_envelopes_marks_rows() -> None:
    struct = [
        {
            "session_id": "s1",
            "payload": {
                "L1": {"ATTRIBUTED_TOKENS": 10, "COVERAGE_RATIO": 1.0},
                "diagnostics": {"calibration_status": {}},
            },
        }
    ]
    sealed = [{"session_id": "s1", "hex_activation_map": {"total_mass": 0.5}}]
    an = [{"session_id": "s1", "extended": {"attribution_coverage": 1.0}}]
    apply_session_envelopes(structural_batch=struct, session_sealed=sealed, session_analyze=an)
    assert "operational_envelope" in struct[0]
    assert struct[0]["operational_envelope"]["status"] == "ok"
    assert assess_structural_row(struct[0]) == []
