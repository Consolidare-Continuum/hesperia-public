from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def test_family_contradiction_pressure_builds() -> None:
    from hesperia.extensions.triz.family_contradiction import build_family_contradiction_pressure

    af = {
        "c1": ("A1", "A1_F1"),
        "c2": ("A2", "A2_F2"),
        "c3": ("A3", "A3_F3"),
    }
    rows = [
        {"pair": ["c1", "c2"], "raw_contradiction_score": 0.9, "effective_activation_score": 0.6},
        {"pair": ["c1", "c2"], "raw_contradiction_score": 0.4, "effective_activation_score": 0.2},
    ]
    out = build_family_contradiction_pressure(rows, af)
    assert float(out["raw"].get("A1_A1_F1", 0.0)) > 0.0
    assert float(out["effective"].get("A2_A2_F2", 0.0)) > 0.0
    assert out["raw"].get("A3_A3_F3", 0.0) == 0.0


def test_family_contradiction_changes_family_activation() -> None:
    from hesperia.nlp.tfp_activation import build_invariant_tfp_activation

    af = {
        "c1": ("A1", "A1_F1"),
        "c2": ("A2", "A2_F2"),
    }
    markers = [("c1", 2.0), ("c2", 2.0)]
    rows = [{"pair": ["c1", "c2"], "raw_contradiction_score": 0.95}]
    base = build_invariant_tfp_activation(markers, token_count=4, concept_to_area_family=af, contradictions=None)
    coupled = build_invariant_tfp_activation(markers, token_count=4, concept_to_area_family=af, contradictions=rows)
    assert base["family_scores_post_contradiction"] != coupled["family_scores_post_contradiction"]


def test_family_bridge_conflict_separation() -> None:
    from hesperia.extensions.triz.family_contradiction import (
        build_family_contradiction_matrix,
        compute_family_bridge_conflict,
    )

    af = {
        "c1": ("A1", "A1_F1"),
        "c2": ("A2", "A2_F2"),
        "c3": ("A1", "A1_F3"),
    }
    rows = [
        {"pair": ["c1", "c2"], "raw_contradiction_score": 0.8, "effective_activation_score": 0.7},
        {"pair": ["c1", "c3"], "raw_contradiction_score": 0.8, "effective_activation_score": 0.7},
    ]
    matrix = build_family_contradiction_matrix(rows, af)
    bridge = compute_family_bridge_conflict(
        matrix,
        {"A1_A1_F1": "A1", "A2_A2_F2": "A2", "A1_A1_F3": "A1"},
    )
    assert float(bridge["family_cross_area_bridge_mass"]) > 0.0
    assert float(bridge["family_intra_area_conflict_mass"]) > 0.0


def test_inspector_flags_hidden_family_conflict(tmp_path: Path) -> None:
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
                        "contradiction_load": 0.15,
                        "dlcr_contradiction_alignment": {"spread_vs_contradiction_consistent": True},
                        "crossplane_contradiction_package": {
                            "effective_contradiction_load": 0.15,
                            "raw_contradiction_load": 0.2,
                            "contradiction_confidence_mean": 0.7,
                            "family_fragmentation_summary": {"global_family_fragmentation": 0.7},
                            "family_conflict_concentration": 0.65,
                            "family_cross_area_bridge_mass": 0.4,
                            "family_contradiction_pressure": {"A1_F1": 1.0},
                        },
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (d / "05_sealed_multiscale.json").write_text(
        json.dumps({"sessions": [{"session_id": sid, "sealed_conflict_trace": {}}]}),
        encoding="utf-8",
    )
    (d / "06_product_analyze.json").write_text(
        json.dumps({"sessions": [{"session_id": sid, "extended": {"session_contradiction_mode": "coherent"}}]}),
        encoding="utf-8",
    )
    (d / "09_session_topology.json").write_text(
        json.dumps({"sessions": [{"session_id": sid, "session_topology": {}}]}),
        encoding="utf-8",
    )
    report = inspect_bundle(d)
    s = report["sessions"][0]
    assert s.get("family_conflict_underreported") is True
    assert s.get("family_fragmentation_hidden") is True
