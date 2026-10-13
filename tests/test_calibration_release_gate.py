# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

from __future__ import annotations

import json
from pathlib import Path

from hesperia.engine.calibration_release_gate import evaluate_bundle, write_gate_report
from core.engine.output_anomalies import default_operational_envelope


def test_release_gate_research_profile_passes_without_manifest(tmp_path: Path) -> None:
    d = tmp_path / "bare"
    d.mkdir()
    body = evaluate_bundle(d, profile="research_allow_degraded")
    assert body.get("pass") is True
    assert body.get("operational_envelope")


def test_release_gate_research_profile_passes_empty_checks(tmp_path: Path) -> None:
    d = tmp_path / "b"
    d.mkdir()
    (d / "00_manifest.json").write_text(
        json.dumps(
            {
                "run": "x",
                "flags": {"with_topology": False},
                "tfp_signal_calibration": {
                    "config_version": "tfp_signal_calibration_v2",
                    "invariant_path_id": "tfp_invariant_activation_v2",
                    "loaded_config": {"version": "tfp_signal_calibration_v2", "hex_feedback_required": True},
                    "inhibition_matrix": {"version": "area_inhibition_matrix_tfp_v1", "area_ids": list(range(12))},
                },
            }
        ),
        encoding="utf-8",
    )
    body = evaluate_bundle(d, profile="research_allow_degraded")
    assert body.get("pass") is True
    assert "operational_envelope" in body


def test_release_gate_writes_11(tmp_path: Path) -> None:
    d = tmp_path / "b2"
    d.mkdir()
    (d / "00_manifest.json").write_text(
        json.dumps(
            {
                "run": "x",
                "flags": {"with_topology": False},
                "tfp_signal_calibration": {
                    "config_version": "tfp_signal_calibration_v2",
                    "invariant_path_id": "tfp_invariant_activation_v2",
                    "loaded_config": {"version": "tfp_signal_calibration_v2", "hex_feedback_required": True},
                    "inhibition_matrix": {"version": "area_inhibition_matrix_tfp_v1", "area_ids": list(range(12))},
                },
            }
        ),
        encoding="utf-8",
    )
    for fn in ("01_structural_batch.json", "05_sealed_multiscale.json", "06_product_analyze.json"):
        (d / fn).write_text(
            json.dumps({"run": "t", "operational_envelope": default_operational_envelope()}),
            encoding="utf-8",
        )
    body = evaluate_bundle(d, profile="internal_review", schema_ok=True, gold_failed=0)
    p = write_gate_report(d, body)
    assert p.is_file()


def test_release_gate_checks_all_sessions_not_only_first(tmp_path: Path) -> None:
    d = tmp_path / "b3"
    d.mkdir()
    (d / "00_manifest.json").write_text(
        json.dumps(
            {
                "run": "x",
                "flags": {"with_topology": False},
                "tfp_signal_calibration": {
                    "config_version": "tfp_signal_calibration_v2",
                    "invariant_path_id": "tfp_invariant_activation_v2",
                    "loaded_config": {"version": "tfp_signal_calibration_v2", "hex_feedback_required": True},
                    "inhibition_matrix": {"version": "area_inhibition_matrix_tfp_v1", "area_ids": list(range(12))},
                },
            }
        ),
        encoding="utf-8",
    )
    for fn in ("01_structural_batch.json", "05_sealed_multiscale.json", "06_product_analyze.json"):
        (d / fn).write_text(
            json.dumps({"run": "t", "operational_envelope": default_operational_envelope()}),
            encoding="utf-8",
        )
    # session_id "good" is healthy; "bad" (second in the list) overproduces and is
    # ungrounded — a gate that only inspects sessions[0] would miss it entirely.
    (d / "13_contradiction_reconciliation.json").write_text(
        json.dumps(
            {
                "run": "tfp_file_pipeline_contradiction_reconciliation_v1",
                "canonical_source": "12_topology_derived_contradictions",
                "sessions": [
                    {
                        "session_id": "good",
                        "canonical_source": "12_topology_derived_contradictions",
                        "lexical_support": {
                            "contradictions_per_accepted_lexical_hit": 1.0,
                            "zero_lexical_evidence_share": 0.1,
                            "inferred_share": 0.1,
                        },
                    },
                    {
                        "session_id": "bad",
                        "canonical_source": "12_topology_derived_contradictions",
                        "lexical_support": {
                            "contradictions_per_accepted_lexical_hit": 9.0,
                            "zero_lexical_evidence_share": 0.95,
                            "inferred_share": 0.95,
                        },
                    },
                ],
                "operational_envelope": default_operational_envelope(),
            }
        ),
        encoding="utf-8",
    )
    body = evaluate_bundle(d, profile="internal_review", schema_ok=True, gold_failed=0)
    assert body.get("pass") is False
    by_check = {c["check"]: c for c in body["checks"]}
    assert by_check["contradiction_overproduction_guard"]["pass"] is False
    assert by_check["contradiction_grounding_zero_lex_share"]["pass"] is False
    assert by_check["contradiction_grounding_inferred_share"]["pass"] is False
    assert by_check["contradiction_grounding_zero_lex_share"]["value"]["bad"] == 0.95
