# HESPERIA — Contradiction release gating (v0.5.8 task9).

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def _base_session(sid: str) -> dict[str, object]:
    return {
        "session_id": sid,
        "contradiction_load": 0.25,
        "dlcr_contradiction_alignment": {"spread_vs_contradiction_consistent": True},
        "crossplane_contradiction_package": {
            "global_contradiction_load": 0.25,
            "raw_contradiction_load": 0.28,
            "effective_contradiction_load": 0.25,
            "contradiction_confidence_mean": 0.65,
            "activation_conflict_load": 0.24,
            "latent_conflict_load": 0.26,
            "contradiction_mode_summary": {
                "negated_opposition_share": 0.1,
                "inhibited_opposition_share": 0.1,
            },
            "runtime_vs_calibration_conflict_split": {
                "likely_runtime_real": 0.55,
                "likely_calibration_pathology": 0.2,
            },
            "feedback_summary": {"note": "ok"},
            "family_fragmentation_summary": {"global_family_fragmentation": 0.12},
            "family_conflict_concentration": 0.2,
            "family_cross_area_bridge_mass": 0.1,
            "dominant_conflict_families": ["F1"],
        },
    }


def test_coherent_contradiction_handling_passes_or_qualified(tmp_path: Path) -> None:
    from tools.inspect_tfp_bundle_output import inspect_bundle

    d = tmp_path / "b_ok"
    d.mkdir()
    sid = "s_ok"
    s04 = _base_session(sid)
    (d / "04_dlcr_full.json").write_text(json.dumps({"sessions": [s04]}), encoding="utf-8")
    (d / "05_sealed_multiscale.json").write_text(
        json.dumps(
            {
                "sessions": [
                    {
                        "session_id": sid,
                        "sealed_conflict_trace": {
                            "persistent_conflict": False,
                            "conflict_collapses_under_aggregation": False,
                        },
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
                            "session_contradiction_mode": "conflict_bearing_interpretable",
                            "verdict_conflict_alignment": {"verdict_underreports_conflict": False},
                            "semantic_conflict_reliability": 0.55,
                            "conflict_source_balance": {"concept_ambiguity_component": 0.2},
                            "latent_vs_overt_conflict": {
                                "overt_conflict_load": 0.24,
                                "latent_conflict_load": 0.26,
                            },
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
                                "contradiction_summary": {"max_segment_contradiction_load": 0.22}
                            }
                        },
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    r = inspect_bundle(d)
    assert r["promotion_conflict_verdict"] in ("PASS", "QUALIFIED_PASS")
    agg = (r.get("release_conflict_gates") or {}).get("aggregate") or {}
    assert not any((g or {}).get("status") == "FAIL" for g in agg.values())


def test_disappearing_contradiction_fails_visibility(tmp_path: Path) -> None:
    from tools.inspect_tfp_bundle_output import inspect_bundle

    d = tmp_path / "b_vis"
    d.mkdir()
    sid = "s_vis"
    (d / "04_dlcr_full.json").write_text(
        json.dumps(
            {
                "sessions": [
                    {
                        "session_id": sid,
                        "contradiction_load": 0.75,
                        "dlcr_contradiction_alignment": {"spread_vs_contradiction_consistent": True},
                        "crossplane_contradiction_package": {
                            "effective_contradiction_load": 0.75,
                            "raw_contradiction_load": 0.76,
                            "contradiction_confidence_mean": 0.7,
                        },
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (d / "05_sealed_multiscale.json").write_text(json.dumps({"sessions": [{"session_id": sid}]}), encoding="utf-8")
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
                                "contradiction_summary": {"max_segment_contradiction_load": 0.82}
                            }
                        },
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    r = inspect_bundle(d)
    gates = r["sessions"][0]["release_conflict_gates"]["contradiction_visibility_gate"]
    assert gates["status"] == "FAIL"
    assert r["promotion_conflict_verdict"] == "FAIL"


def test_family_concealment_fails_family_gate() -> None:
    from hesperia.extensions.triz.conflict_release_gating import build_release_conflict_gates

    flags = {
        "session_id": "x",
        "topology_max_segment_contradiction_load": 0.1,
        "product_session_mode": "coherent",
        "effective_contradiction_load": 0.15,
        "raw_contradiction_load": 0.2,
        "semantic_conflict_reliability": 0.6,
        "verdict_underreports_conflict_reported": False,
        "product_underreports_conflict": False,
        "dlcr_conflict_misalignment": False,
        "multiscale_conflict_collapse": False,
        "likely_lexical_contamination": False,
        "latent_conflict_underreported": False,
        "suppressed_conflict_disappearance": False,
        "family_fragmentation_hidden": True,
        "family_conflict_underreported": True,
        "cross_area_bridge_underreported": False,
        "concentrated_family_conflict_omitted": False,
        "family_matrix_collapse": False,
        "calibration_pathology_masquerading_runtime": False,
        "feedback_trace_missing": False,
        "negation_conflict_misalignment": False,
        "coactive_conflict_overclaimed": False,
        "conflict_confidence_consistency": True,
        "family_area_alignment_score": 0.3,
        "likely_calibration_pathology": 0.1,
        "session_crossplane_ok": True,
        "latent_vs_overt_mismatch_warn": False,
    }
    g = build_release_conflict_gates(flags)
    assert g["family_conflict_gate"]["status"] == "FAIL"


def test_contamination_dishonesty_fails_contamination_gate() -> None:
    from hesperia.extensions.triz.conflict_release_gating import build_release_conflict_gates

    flags = {
        "session_id": "x",
        "topology_max_segment_contradiction_load": 0.2,
        "product_session_mode": "coherent",
        "effective_contradiction_load": 0.55,
        "raw_contradiction_load": 0.92,
        "semantic_conflict_reliability": 0.8,
        "verdict_underreports_conflict_reported": False,
        "product_underreports_conflict": False,
        "dlcr_conflict_misalignment": False,
        "multiscale_conflict_collapse": False,
        "likely_lexical_contamination": True,
        "latent_conflict_underreported": False,
        "suppressed_conflict_disappearance": False,
        "family_fragmentation_hidden": False,
        "family_conflict_underreported": False,
        "cross_area_bridge_underreported": False,
        "concentrated_family_conflict_omitted": False,
        "family_matrix_collapse": False,
        "calibration_pathology_masquerading_runtime": False,
        "feedback_trace_missing": False,
        "negation_conflict_misalignment": False,
        "coactive_conflict_overclaimed": False,
        "conflict_confidence_consistency": False,
        "family_area_alignment_score": 0.8,
        "likely_calibration_pathology": 0.1,
        "session_crossplane_ok": True,
        "latent_vs_overt_mismatch_warn": False,
    }
    g = build_release_conflict_gates(flags)
    assert g["contamination_honesty_gate"]["status"] == "FAIL"


def test_calibration_pathology_without_feedback_fails_split_gate() -> None:
    from hesperia.extensions.triz.conflict_release_gating import build_release_conflict_gates

    flags = {
        "session_id": "x",
        "topology_max_segment_contradiction_load": 0.2,
        "product_session_mode": "conflict_dominant",
        "effective_contradiction_load": 0.5,
        "raw_contradiction_load": 0.55,
        "semantic_conflict_reliability": 0.5,
        "verdict_underreports_conflict_reported": False,
        "product_underreports_conflict": False,
        "dlcr_conflict_misalignment": False,
        "multiscale_conflict_collapse": False,
        "likely_lexical_contamination": False,
        "latent_conflict_underreported": False,
        "suppressed_conflict_disappearance": False,
        "family_fragmentation_hidden": False,
        "family_conflict_underreported": False,
        "cross_area_bridge_underreported": False,
        "concentrated_family_conflict_omitted": False,
        "family_matrix_collapse": False,
        "calibration_pathology_masquerading_runtime": True,
        "feedback_trace_missing": True,
        "negation_conflict_misalignment": False,
        "coactive_conflict_overclaimed": False,
        "conflict_confidence_consistency": True,
        "family_area_alignment_score": 0.7,
        "likely_calibration_pathology": 0.75,
        "session_crossplane_ok": True,
        "latent_vs_overt_mismatch_warn": False,
    }
    g = build_release_conflict_gates(flags)
    assert g["runtime_vs_calibration_split_gate"]["status"] == "FAIL"


def test_cli_fail_on_conflict_gate_nonzero(tmp_path: Path) -> None:
    d = tmp_path / "b_fail_cli"
    d.mkdir()
    sid = "s_cli"
    (d / "04_dlcr_full.json").write_text(
        json.dumps(
            {
                "sessions": [
                    {
                        "session_id": sid,
                        "contradiction_load": 0.75,
                        "dlcr_contradiction_alignment": {"spread_vs_contradiction_consistent": True},
                        "crossplane_contradiction_package": {
                            "effective_contradiction_load": 0.75,
                            "raw_contradiction_load": 0.76,
                            "contradiction_confidence_mean": 0.7,
                        },
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (d / "05_sealed_multiscale.json").write_text(json.dumps({"sessions": [{"session_id": sid}]}), encoding="utf-8")
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
                                "contradiction_summary": {"max_segment_contradiction_load": 0.85}
                            }
                        },
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    r = subprocess.run(
        [
            sys.executable,
            str(_REPO / "tools" / "tfp_pipeline_standard_run.py"),
            "--inspect-bundle-dir",
            str(d),
            "--fail-on-conflict-gate",
        ],
        cwd=str(_REPO),
        env={**dict(**__import__("os").environ), "PYTHONPATH": str(_REPO)},
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 5


def test_check_conflict_gate_exit_helper() -> None:
    from tools.tfp_pipeline_standard_run import check_conflict_gate_exit

    assert check_conflict_gate_exit({"promotion_conflict_verdict": "FAIL"}, fail_on_conflict_gate=True, min_conflict_integrity_score=None) == 5
    assert (
        check_conflict_gate_exit(
            {"promotion_conflict_verdict": "PASS", "conflict_integrity_score": 0.5},
            fail_on_conflict_gate=False,
            min_conflict_integrity_score=0.9,
        )
        == 6
    )
