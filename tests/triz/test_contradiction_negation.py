# HESPERIA — Contradiction × negation × inhibition (v0.5.8 task6).

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def test_negated_opposition_classified_separately() -> None:
    from hesperia.extensions.triz.contradiction_coupling import enrich_contradiction_rows
    from hesperia.extensions.triz.contradiction_uncertainty import build_uncertainty_package

    rows = [{"pair": ["C1", "C2"], "raw_contradiction_score": 0.8}]
    unc = build_uncertainty_package({}, {})
    # Strong lexical negation signal + hex pullback, but little mass suppression (post ≈ stab).
    post = {"C1": 0.86, "C2": 0.49}
    stab = {"C1": 0.9, "C2": 0.5}
    hd = {"C1": -0.42, "C2": 0.0}
    lex = {"negated_marker_ratio": 0.78, "negated_concept_ratio": 0.0}
    out = enrich_contradiction_rows(
        rows,
        unc,
        post,
        concept_weights_stabilized=stab,
        hex_feedback_delta=hd,
        lexical_negation_summary=lex,
    )
    assert out[0]["mode"] == "negated_opposition"
    assert out[0]["mode"] != "coactive_opposition"


def test_inhibited_opposition_latent_exceeds_activation() -> None:
    from hesperia.extensions.triz.contradiction_coupling import enrich_contradiction_rows
    from hesperia.extensions.triz.contradiction_uncertainty import build_uncertainty_package

    rows = [{"pair": ["C1", "C2"], "raw_contradiction_score": 0.9}]
    unc = build_uncertainty_package({}, {})
    post = {"C1": 0.08, "C2": 0.6}
    stab = {"C1": 0.95, "C2": 0.62}
    hd = {"C1": -0.2, "C2": 0.0}
    out = enrich_contradiction_rows(
        rows,
        unc,
        post,
        concept_weights_stabilized=stab,
        hex_feedback_delta=hd,
        lexical_negation_summary=None,
    )
    assert out[0]["mode"] == "inhibited_opposition"
    assert float(out[0]["effective_activation_score"]) < float(out[0]["effective_latent_conflict_score"])


def test_coactive_opposition_high_overt() -> None:
    from hesperia.extensions.triz.contradiction_coupling import enrich_contradiction_rows
    from hesperia.extensions.triz.contradiction_uncertainty import build_uncertainty_package

    rows = [{"pair": ["C1", "C2"], "raw_contradiction_score": 0.85}]
    unc = build_uncertainty_package({}, {})
    post = {"C1": 0.55, "C2": 0.52}
    stab = {"C1": 0.56, "C2": 0.53}
    hd = {"C1": 0.0, "C2": 0.0}
    out = enrich_contradiction_rows(
        rows,
        unc,
        post,
        concept_weights_stabilized=stab,
        hex_feedback_delta=hd,
        lexical_negation_summary={"negated_marker_ratio": 0.02},
    )
    assert out[0]["mode"] == "coactive_opposition"
    assert float(out[0]["effective_activation_score"]) > 0.35


def test_product_suppressed_conflict_flag() -> None:
    from runtime.pipeline.analyze import _product_contradiction_extensions

    minimal = {"governance": 0.5, "constraint_status": 0.5}
    extended = {"dict_b": {"coherence_index": 0.5}}
    pkg = {
        "global_contradiction_load": 0.5,
        "raw_contradiction_load": 0.5,
        "effective_contradiction_load": 0.5,
        "cross_area_contradiction_mass": 0.2,
        "contradiction_stability_index": 0.5,
        "contradiction_coupling_active": True,
        "contradiction_coherence_flag": True,
        "contradiction_confidence_mean": 0.7,
        "uncertainty_adjusted_conflict_index": 0.45,
        "lexical_semantic_conflict_split": {
            "likely_lexical": 0.2,
            "likely_conceptual_ambiguity": 0.2,
            "likely_semantic_real": 0.6,
        },
        "activation_conflict_load": 0.15,
        "latent_conflict_load": 0.62,
        "contradiction_mode_summary": {"inhibited_opposition_share": 0.55},
        "negation_conflict_component": 0.1,
        "inhibition_conflict_component": 0.42,
    }
    out = _product_contradiction_extensions(minimal, extended, pkg)
    assert out["latent_vs_overt_conflict"]["conflict_is_partly_suppressed"] is True


def test_inspector_flags_suppressed_disappearance(tmp_path: Path) -> None:
    import json

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
                        "contradiction_load": 0.5,
                        "negation_summary": {"negated_marker_ratio": 0.1},
                        "crossplane_contradiction_package": {
                            "effective_contradiction_load": 0.5,
                            "raw_contradiction_load": 0.5,
                            "contradiction_confidence_mean": 0.7,
                            "activation_conflict_load": 0.1,
                            "latent_conflict_load": 0.1,
                            "contradiction_mode_summary": {},
                            "negation_conflict_component": 0.05,
                            "inhibition_conflict_component": 0.4,
                        },
                        "dlcr_contradiction_alignment": {"spread_vs_contradiction_consistent": True},
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
        json.dumps(
            {
                "sessions": [
                    {
                        "session_id": sid,
                        "extended": {
                            "session_contradiction_mode": "coherent",
                            "latent_vs_overt_conflict": {
                                "overt_conflict_load": 0.1,
                                "latent_conflict_load": 0.1,
                            },
                        },
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (d / "09_session_topology.json").write_text(
        json.dumps({"sessions": [{"session_id": sid, "session_topology": {}}]}),
        encoding="utf-8",
    )
    report = inspect_bundle(d)
    sess = report["sessions"][0]
    assert sess.get("suppressed_conflict_disappearance") is True
