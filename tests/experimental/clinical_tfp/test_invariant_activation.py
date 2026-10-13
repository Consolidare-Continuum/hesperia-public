from __future__ import annotations

import json
from pathlib import Path

import pytest

from hesperia.engine.calibration_release_gate import evaluate_bundle
from hesperia.engine.tfp_signal_calibration import load_area_inhibition_matrix, load_tfp_signal_calibration
from hesperia.nlp.session_parser import analyze_session
from research.clinical_tfp.session_topology import run_session_topology


FIXTURES = json.loads(
    (Path(__file__).resolve().parents[2] / "gold" / "tfp_invariant_fixtures.json").read_text(
        encoding="utf-8"
    )
)


def _synthetic_indexes() -> tuple[dict[str, list[tuple[str, float]]], dict[str, tuple[str, str]]]:
    marker_index = {
        "attack": [("B_A10_F10_001", 1.0)],
        "blame": [("B_A10_F10_002", 1.0)],
        "repair": [("B_A1_F10_001", 1.0)],
        "trust": [("B_A1_F10_002", 1.0)],
        "control": [("B_A10_F10_003", 1.0)],
        "hold": [("B_A10_F10_004", 1.0)],
        "shame": [("B_A1_F10_003", 1.0)],
        "tension": [("B_A1_F10_004", 1.0)],
        "rupture": [("B_A10_F10_001", 1.1)],
        "calm": [("B_A1_F10_001", 0.7)],
        "steady": [("B_A1_F10_002", 0.7)],
        "now": [("B_A10_F10_002", 0.5)],
    }
    af = {
        "B_A10_F10_001": ("A4", "F1"),
        "B_A10_F10_002": ("A4", "F1"),
        "B_A1_F10_001": ("A7", "F1"),
        "B_A1_F10_002": ("A7", "F1"),
        "B_A10_F10_003": ("A5", "F1"),
        "B_A10_F10_004": ("A5", "F1"),
        "B_A1_F10_003": ("A2", "F1"),
        "B_A1_F10_004": ("A2", "F1"),
    }
    return marker_index, af


def _analyze(text: str) -> dict[str, object]:
    marker_index, af = _synthetic_indexes()
    return analyze_session(
        text,
        marker_index=marker_index,
        phrase_index={},
        concept_to_area_family=af,
        ngram_n=1,
    )


def test_inhibition_matrix_loads_and_validates() -> None:
    matrix = load_area_inhibition_matrix()
    assert len(matrix["area_ids"]) == 12
    assert len(matrix["matrix"]) == 12
    assert all(len(row) == 12 for row in matrix["matrix"])
    assert all(row[i] == 0.0 for i, row in enumerate(matrix["matrix"]))


def test_invariant_activation_is_deterministic_and_normalized() -> None:
    text = FIXTURES["short_aggression_burst"]["text"]
    first = _analyze(text)
    second = _analyze(text)
    assert first == second
    final = first["areas"]
    assert final == first["areas_final"]
    assert pytest.approx(sum(float(v) for v in final.values()), abs=1e-6) == 1.0


def test_competing_areas_are_constrained() -> None:
    result = _analyze(FIXTURES["mixed_shame_control_segment"]["text"])
    items = sorted(result["areas"].items(), key=lambda x: x[1], reverse=True)
    fx = FIXTURES["mixed_shame_control_segment"]
    assert items[0][0] == fx["expected_dominant_area"]
    assert items[1][1] <= fx["second_area_max"]
    assert items[0][1] - items[1][1] >= fx["min_top_gap"]


def test_same_trigger_density_does_not_run_away_with_length() -> None:
    short = _analyze("attack filler attack filler")
    long = _analyze("attack filler attack filler attack filler attack filler attack filler attack filler")
    assert long["areas"]["A4"] <= short["areas"]["A4"] + 0.02
    assert long["concept_weights_post_hex"]["B_A10_F10_001"] <= short["concept_weights_post_hex"][
        "B_A10_F10_001"
    ] + 0.2


def test_hex_feedback_materially_changes_supported_fixture() -> None:
    result = _analyze("attack blame repair trust")
    delta = result["hex_feedback_delta"]
    assert any(abs(float(v)) > 1e-9 for v in delta.values())
    assert result["concept_weights_post_hex"] != result["concept_weights_stabilized"]


def test_temporal_momentum_stabilizes_aggression_curve() -> None:
    marker_index, af = _synthetic_indexes()
    topo = run_session_topology(
        FIXTURES["escalation_over_3_segments_session"]["text"],
        window_size=4,
        marker_index=marker_index,
        phrase_index={},
        concept_to_area_family=af,
    )
    raw = topo["area_curves_raw"]["aggression"]
    stable = topo["area_curves_stable"]["aggression"]
    assert len(raw) == 3
    assert len(stable) == 3
    assert stable[0] <= stable[1] <= stable[2] if FIXTURES["escalation_over_3_segments_session"][
        "momentum_aggression_monotonic"
    ] else True
    assert stable != raw


def test_rupture_then_repair_reduces_aggression() -> None:
    marker_index, af = _synthetic_indexes()
    topo = run_session_topology(
        FIXTURES["rupture_then_repair_segment"]["text"],
        window_size=4,
        marker_index=marker_index,
        phrase_index={},
        concept_to_area_family=af,
    )
    fx = FIXTURES["rupture_then_repair_segment"]
    agg = topo["area_curves_stable"]["aggression"]
    final = _analyze(fx["text"])
    ranked = sorted(final["areas"].items(), key=lambda x: x[1], reverse=True)
    assert ranked[0][0] == fx["expected_dominant_area"]
    assert ranked[1][1] <= fx["second_area_max"]
    assert ranked[0][1] - ranked[1][1] >= fx["min_top_gap"]
    assert agg[1] < agg[0]


def test_release_gate_fails_when_invariant_path_is_bypassed(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    manifest = {
        "run": "tfp_file_pipeline_manifest",
        "flags": {"with_topology": False},
        "tfp_signal_calibration": {
            "config_version": "missing",
            "invariant_path_id": "legacy_path",
            "loaded_config": {"hex_feedback_required": False},
            "inhibition_matrix": {},
        },
    }
    (bundle / "00_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    core_env = {
        "status": "ok",
        "anomaly_codes": [],
        "severity": "info",
        "blocking": False,
        "operator_message": "",
        "recommended_next_check": "",
        "taxonomy_version": "v1"
    }
    for name in ("01_structural_batch.json", "05_sealed_multiscale.json", "06_product_analyze.json"):
        (bundle / name).write_text(json.dumps({"operational_envelope": core_env}), encoding="utf-8")
    gate = evaluate_bundle(bundle, profile="internal_review", schema_ok=True, gold_failed=0)
    assert gate["pass"] is False
    checks = {row["check"]: row["pass"] for row in gate["checks"]}
    # Renamed in e1217ab6 "v0.5.2 technical terminology propagation" (invariant/hex/inhibition -> operator/coupling).
    assert checks["operator_path_used"] is False
    assert checks["post_operator_feedback_active"] is False
    assert checks["coupling_matrix_present"] is False


def test_signal_calibration_declares_invariant_defaults() -> None:
    cfg = load_tfp_signal_calibration()
    assert cfg["invariant_path_id"] == "tfp_invariant_activation_v2"
    assert cfg["hex_feedback_required"] is True
    assert cfg["segment_length_normalization"] == "inverse_sqrt_token_count"
