# HESPERIA — Cross-plane contradiction package (v0.5.8 task4–5).

from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def _synthetic_indexes() -> tuple[dict[str, list[tuple[str, float]]], dict[str, tuple[str, str]]]:
    marker_index = {
        "attack": [("B_A10_F10_001", 1.0)],
        "repair": [("B_A1_F10_001", 1.0)],
    }
    af = {
        "B_A10_F10_001": ("A4", "A4_F10"),
        "B_A1_F10_001": ("A7", "A7_F10"),
    }
    return marker_index, af


def test_crossplane_package_required_fields() -> None:
    from hesperia.extensions.triz.crossplane_contradiction import build_crossplane_contradiction_package
    from hesperia.nlp.session_parser import analyze_session
    from research.clinical_tfp.session_topology import run_session_topology

    marker_index, af = _synthetic_indexes()
    text = "attack repair attack repair"
    rows = [{"pair": ["B_A10_F10_001", "B_A1_F10_001"], "raw_contradiction_score": 0.95}]
    act = analyze_session(text, marker_index=marker_index, concept_to_area_family=af, phrase_index={}, contradictions=rows)
    topo = run_session_topology(
        text,
        window_size=2,
        marker_index=marker_index,
        concept_to_area_family=af,
        phrase_index={},
        contradictions=rows,
    )
    pkg = build_crossplane_contradiction_package(act, topo, rows)
    for k in (
        "global_contradiction_load",
        "raw_contradiction_load",
        "effective_contradiction_load",
        "area_contradiction_pressure",
        "cross_area_contradiction_mass",
        "segment_contradiction_loads",
        "transition_pressure",
        "contradiction_stability_index",
        "contradiction_coherence_flag",
        "contradiction_coupling_active",
        "contradiction_confidence_mean",
        "lexical_semantic_conflict_split",
        "activation_conflict_load",
        "latent_conflict_load",
        "contradiction_mode_summary",
        "negation_conflict_component",
        "inhibition_conflict_component",
        "family_contradiction_pressure",
        "family_conflict_concentration",
        "family_fragmentation_summary",
        "family_cross_area_bridge_mass",
        "family_intra_area_conflict_mass",
        "dominant_conflict_families",
        "calibration_contradiction_risk",
        "runtime_vs_calibration_conflict_split",
        "feedback_summary",
        "top_risky_concepts",
        "top_risky_pairs",
        "top_risky_tokens",
    ):
        assert k in pkg
    assert 0.0 <= float(pkg["global_contradiction_load"]) <= 1.0
    assert isinstance(pkg["contradiction_coupling_active"], bool)


def test_dlcr_with_and_without_package() -> None:
    from core.engine.lexical_concept.pipeline import run_dlcr_pipeline

    text = "clinical material for dlcr pipeline test"
    base = run_dlcr_pipeline(text, repo_root=_REPO, mode="clinical_speech")
    assert "contradiction_load" not in base
    pkg = {
        "global_contradiction_load": 0.55,
        "cross_area_contradiction_mass": 0.4,
        "contradiction_stability_index": 0.5,
        "contradiction_coherence_flag": True,
        "contradiction_coupling_active": True,
    }
    with_p = run_dlcr_pipeline(text, repo_root=_REPO, mode="clinical_speech", contradiction_package=pkg)
    assert with_p.get("contradiction_load") == 0.55
    assert "dlcr_contradiction_alignment" in with_p
    assert isinstance(with_p["dlcr_contradiction_alignment"], dict)


def test_multiscale_persistent_contradiction() -> None:
    from core.engine.sealed_multiscale_stack import run_sealed_multiscale_stack

    assets = _REPO / "assets" / "lexicon" / "curated"
    text = "test"
    seg_loads = [
        {"contradiction_load_normalized": 0.9, "contradiction_load": 1.0, "cross_area_contradiction_mass": 0.5},
        {"contradiction_load_normalized": 0.85, "contradiction_load": 0.9, "cross_area_contradiction_mass": 0.4},
    ]
    pkg = {
        "global_contradiction_load": 0.8,
        "area_contradiction_pressure": {"A4": 1.0},
        "cross_area_contradiction_mass": 0.5,
        "segment_contradiction_loads": seg_loads,
        "transition_pressure": [0.2, 0.15],
        "contradiction_stability_index": 0.4,
        "contradiction_coherence_flag": True,
        "contradiction_coupling_active": True,
    }
    out = run_sealed_multiscale_stack(
        text,
        assets,
        use_triz_contradiction=False,
        contradiction_package=pkg,
    )
    trace = out.get("sealed_conflict_trace") or {}
    assert trace.get("persistent_conflict") is True
    assert "multiscale_contradiction_alignment" in out


def test_product_reflects_contradiction() -> None:
    from runtime.pipeline.analyze import analyze

    # Real genesis-taxonomy vocabulary (v06 retired; attribution_shared has no
    # generic-filler fallback, so this must contain words the live dictionary knows).
    text = "trust and compassion and courage build community despite conflict and betrayal"
    pkg = {
        "global_contradiction_load": 0.72,
        "cross_area_contradiction_mass": 0.5,
        "contradiction_stability_index": 0.3,
        "contradiction_coherence_flag": True,
        "contradiction_coupling_active": True,
    }
    minimal, extended = analyze(text, contradiction_package=pkg)
    assert extended.get("session_contradiction_mode") != "coherent"
    assert "product_conflict_consistency" in extended
    assert "verdict_conflict_alignment" in extended


def test_inspector_flags_underreporting(tmp_path: Path) -> None:
    from tools.inspect_tfp_bundle_output import inspect_bundle

    d = tmp_path / "bundle"
    d.mkdir()
    sid = "s1"
    (d / "04_dlcr_full.json").write_text(
        json.dumps(
            {
                "sessions": [
                    {
                        "session_id": sid,
                        "contradiction_load": 0.7,
                        "dlcr_contradiction_alignment": {"spread_vs_contradiction_consistent": True},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (d / "05_sealed_multiscale.json").write_text(
        json.dumps(
            {
                "sessions": [
                    {
                        "session_id": sid,
                        "multiscale_contradiction_alignment": {"global_alignment": 0.5},
                        "sealed_conflict_trace": {"persistent_conflict": True, "conflict_collapses_under_aggregation": True},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (d / "06_product_analyze.json").write_text(
        json.dumps(
            {
                "sessions": [
                    {
                        "session_id": sid,
                        "extended": {
                            "verdict_conflict_alignment": {"verdict_underreports_conflict": False},
                            "session_contradiction_mode": "coherent",
                        },
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (d / "09_session_topology.json").write_text(
        json.dumps(
            {
                "sessions": [
                    {
                        "session_id": sid,
                        "session_topology": {
                            "curve_projection_meta": {
                                "contradiction_summary": {"max_segment_contradiction_load": 0.8}
                            }
                        },
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    report = inspect_bundle(d)
    assert report["sessions"]
    assert any(s.get("product_underreports_conflict") for s in report["sessions"])
    assert "promotion_conflict_verdict" in report
    assert "conflict_integrity_score" in report
    assert "release_conflict_gates" in report
    assert "conflict_release_summary" in report
    assert "contradiction_contract_valid" in report
    assert "missing_required_contradiction_fields" in report
    assert "deprecated_contradiction_fields_found" in report


def test_inspector_flags_feedback_trace_missing(tmp_path: Path) -> None:
    from tools.inspect_tfp_bundle_output import inspect_bundle

    d = tmp_path / "bundle2"
    d.mkdir()
    sid = "s2"
    (d / "04_dlcr_full.json").write_text(
        json.dumps(
            {
                "sessions": [
                    {
                        "session_id": sid,
                        "contradiction_load": 0.6,
                        "crossplane_contradiction_package": {
                            "effective_contradiction_load": 0.6,
                            "raw_contradiction_load": 0.8,
                            "contradiction_confidence_mean": 0.35,
                            "runtime_vs_calibration_conflict_split": {
                                "likely_runtime_real": 0.2,
                                "likely_calibration_pathology": 0.8,
                            },
                        },
                        "dlcr_contradiction_alignment": {"spread_vs_contradiction_consistent": True},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (d / "05_sealed_multiscale.json").write_text(json.dumps({"sessions": [{"session_id": sid}]}), encoding="utf-8")
    (d / "06_product_analyze.json").write_text(
        json.dumps({"sessions": [{"session_id": sid, "extended": {"session_contradiction_mode": "conflict_dominant"}}]}),
        encoding="utf-8",
    )
    (d / "09_session_topology.json").write_text(json.dumps({"sessions": [{"session_id": sid, "session_topology": {}}]}), encoding="utf-8")
    report = inspect_bundle(d)
    s = report["sessions"][0]
    assert s.get("feedback_trace_missing") is True
