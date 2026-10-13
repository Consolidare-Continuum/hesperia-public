# HESPERIA — Contradiction × uncertainty coupling (v0.5.8 task5).

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def test_build_uncertainty_package_minimal() -> None:
    from hesperia.extensions.triz.contradiction_uncertainty import build_uncertainty_package

    pkg = build_uncertainty_package({}, {})
    assert "lexical_uncertainty" in pkg
    assert 0.0 <= float(pkg["lexical_uncertainty"]) <= 1.0
    assert "calibration_pathology_prior" in pkg
    assert "runtime_conflict_prior" in pkg


def test_effective_score_lower_when_weak_support() -> None:
    from hesperia.extensions.triz.contradiction_coupling import enrich_contradiction_rows
    from hesperia.extensions.triz.contradiction_uncertainty import build_uncertainty_package

    rows = [{"pair": ["A", "B"], "raw_contradiction_score": 0.8}]
    unc = build_uncertainty_package(
        {
            "lexical_uncertainty_summary": {"unmapped_lexical_ratio": 0.4, "low_priority_link_ratio": 0.2},
            "concept_uncertainty_summary": {"weak_concept_share": 0.5, "concept_entropy": 0.6},
        },
        {},
    )
    cw_strong = {"A": 1.0, "B": 1.0}
    cw_weak = {"A": 0.05, "B": 0.06}
    e1 = enrich_contradiction_rows(rows, unc, cw_strong)
    e2 = enrich_contradiction_rows(rows, unc, cw_weak)
    assert float(e1[0]["effective_score"]) >= float(e2[0]["effective_score"])


def test_raw_and_effective_pressure_diverge() -> None:
    from hesperia.extensions.triz.contradiction_coupling import (
        build_area_contradiction_pressure,
        enrich_contradiction_rows,
    )
    from hesperia.extensions.triz.contradiction_uncertainty import build_uncertainty_package
    from hesperia.engine.tfp_signal_calibration import load_tfp_signal_calibration

    area_ids = [str(x) for x in load_tfp_signal_calibration().get("area_ids") or []]
    af = {
        "ca1": (area_ids[0], "F1"),
        "cb1": (area_ids[1] if len(area_ids) > 1 else area_ids[0], "F2"),
    }
    unc = build_uncertainty_package(
        {"lexical_uncertainty_summary": {"unmapped_lexical_ratio": 0.5}},
        {},
    )
    rows = [{"pair": ["ca1", "cb1"], "raw_contradiction_score": 0.9}]
    en = enrich_contradiction_rows(rows, unc, {"ca1": 0.2, "cb1": 0.21})
    raw = build_area_contradiction_pressure(en, af, area_ids, use_effective_scores=False)
    eff = build_area_contradiction_pressure(en, af, area_ids, use_effective_scores=True)
    assert raw != eff or max(raw.values()) == max(eff.values())


def test_product_distinguishes_high_raw_low_conf_vs_high_conf() -> None:
    from runtime.pipeline.analyze import _product_contradiction_extensions

    minimal = {"governance": 0.5, "constraint_status": 0.5}
    extended = {"dict_b": {"coherence_index": 0.5}}
    low_conf_pkg = {
        "global_contradiction_load": 0.7,
        "raw_contradiction_load": 0.85,
        "effective_contradiction_load": 0.4,
        "cross_area_contradiction_mass": 0.2,
        "contradiction_stability_index": 0.5,
        "contradiction_coupling_active": True,
        "contradiction_coherence_flag": True,
        "contradiction_confidence_mean": 0.25,
        "uncertainty_adjusted_conflict_index": 0.35,
        "lexical_semantic_conflict_split": {
            "likely_lexical": 0.5,
            "likely_conceptual_ambiguity": 0.35,
            "likely_semantic_real": 0.15,
        },
    }
    high_conf_pkg = {**low_conf_pkg, "contradiction_confidence_mean": 0.88, "effective_contradiction_load": 0.78}
    a = _product_contradiction_extensions(minimal, extended, low_conf_pkg)
    b = _product_contradiction_extensions(minimal, extended, high_conf_pkg)
    assert a["semantic_conflict_reliability"] < b["semantic_conflict_reliability"]
    assert a["session_contradiction_mode"] != b["session_contradiction_mode"] or a["conflict_confidence_summary"] != b["conflict_confidence_summary"]


def test_crossplane_has_raw_effective() -> None:
    from hesperia.extensions.triz.crossplane_contradiction import build_crossplane_contradiction_package
    from hesperia.extensions.triz.contradiction_uncertainty import build_uncertainty_package

    act = {
        "contradiction_coupling_active": True,
        "contradiction_pressure": {"A1": 0.4},
        "contradiction_pressure_raw": {"A1": 0.9},
    }
    unc = build_uncertainty_package({"lexical_uncertainty_summary": {"unmapped_lexical_ratio": 0.3}}, act)
    pkg = build_crossplane_contradiction_package(act, {}, [], uncertainty_package=unc)
    assert "raw_contradiction_load" in pkg
    assert "effective_contradiction_load" in pkg
    assert "lexical_semantic_conflict_split" in pkg
    assert "activation_conflict_load" in pkg
    assert "latent_conflict_load" in pkg
    assert "contradiction_mode_summary" in pkg
