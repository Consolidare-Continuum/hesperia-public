# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""CORE-D2 W8 (CORE-D2-086/087) — shadow comparison and weight-sweep tests.

Uses the real default production dict_a/dict_b (HESPERIA_CALIB_DICT_VERSION
unset -> falls back to assets/data/engine_dynamics_v060/), monkeypatching
only Dict D resolution so these tests exercise the actual wired pipeline,
not a synthetic stand-in.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import core.engine.lexical_concept.pipeline as pipeline_module
from core.engine.lexical_concept.pipeline import run_dlcr_pipeline
from core.resolver.resolver import resolve_hit
from core.lexical.matcher import LexicalHit

SAMPLE_TEXT = "The patient described feelings of shame and disgust after the session."


def _write_dict_d(path: Path) -> None:
    rows = [
        {
            "concept_id_a": "C-AAA",
            "concept_id_b": "C-BBB",
            "cooc_count": 9,
            "npmi": 0.7,
            "g2": 20.0,
            "agreement_with_b": "novel",
            "source_books": ["book-001"],
        }
    ]
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")


def test_dict_d_present_at_weight_zero_is_a_pure_shadow_no_behavior_change(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CORE-D2-086: wiring Dict D in must not change output while weight stays 0."""
    without_dict_d = run_dlcr_pipeline(SAMPLE_TEXT, empirical_weight_override=0.0)

    dict_d_path = tmp_path / "dict_d.jsonl"
    _write_dict_d(dict_d_path)
    monkeypatch.setattr(pipeline_module, "resolve_dict_d_file", lambda repo: dict_d_path)
    with_dict_d = run_dlcr_pipeline(SAMPLE_TEXT, empirical_weight_override=0.0)

    assert with_dict_d["resolver_trace"]["dict_d_pairs_loaded"] == 1
    assert without_dict_d["resolver_trace"]["dict_d_pairs_loaded"] == 0

    for field in ("span_resolutions", "unresolved_span_resolutions", "family_activation", "area_activation"):
        assert with_dict_d[field] == without_dict_d[field], field


def test_dict_d_resolved_path_that_vanished_is_handled_gracefully(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """load_dict_d_pairs treats a missing file as "no pairs" (fail-open, by design —
    this is the runtime lookup path, not dict_d_io.py's fail-closed calibration-time
    validator), so a resolved-but-vanished path must not crash the pipeline."""
    monkeypatch.setattr(pipeline_module, "resolve_dict_d_file", lambda repo: tmp_path / "does_not_exist.jsonl")
    result = run_dlcr_pipeline(SAMPLE_TEXT, empirical_weight_override=0.0)
    assert result["resolver_trace"]["dict_d_pairs_loaded"] == 0


# --- CORE-D2-087: controlled non-zero weight sweep, test-only -----------------------


def _concept_index() -> dict[str, dict]:
    return {"C-A": {"preferred_label": "Alpha", "specificity_rank": 5}, "C-B": {"preferred_label": "Beta", "specificity_rank": 5}}


def weight_sweep(hits: list[LexicalHit], dict_d_pairs: dict, weights: list[float]) -> list[dict[str, float]]:
    """Test-only diagnostic: resolve a fixed two-hit paragraph at each weight, no production config touched."""
    from core.resolver.resolver import resolve_paragraph_hits

    out = []
    for w in weights:
        results = resolve_paragraph_hits(
            hits, _concept_index(), canonical_text="alpha beta", dict_d_pairs=dict_d_pairs, empirical_weight_override=w
        )
        out.append({r["source_text_span"]: r["candidate_scores"][r["winning_concept_id"]] for r in results})
    return out


def test_weight_sweep_is_deterministic() -> None:
    hits = [
        LexicalHit("e1", "alpha", 0, 5, "exact", ["C-A"], 0),
        LexicalHit("e2", "beta", 6, 10, "exact", ["C-B"], 0),
    ]
    pairs = {("C-A", "C-B"): 0.8}
    first = weight_sweep(hits, pairs, [0.0, 0.3, 0.7, 1.0])
    second = weight_sweep(hits, pairs, [0.0, 0.3, 0.7, 1.0])
    assert first == second


def test_weight_sweep_score_nondecreasing_for_positive_empirical_signal() -> None:
    """score_candidate's w4*empirical_signal term is additive and empirical_signal>=0
    for a positive npmi pair, so the winning candidate's score must never decrease
    as weight increases (until saturate's [0,1] clamp holds it flat at the top)."""
    hits = [
        LexicalHit("e1", "alpha", 0, 5, "exact", ["C-A"], 0),
        LexicalHit("e2", "beta", 6, 10, "exact", ["C-B"], 0),
    ]
    pairs = {("C-A", "C-B"): 0.8}
    weights = [0.0, 0.1, 0.25, 0.5, 0.75, 1.0]
    sweep = weight_sweep(hits, pairs, weights)
    alpha_scores = [s["alpha"] for s in sweep]
    assert all(b >= a - 1e-9 for a, b in zip(alpha_scores, alpha_scores[1:]))
    assert alpha_scores[-1] >= alpha_scores[0]


def test_weight_sweep_at_zero_matches_no_dict_d() -> None:
    hits = [
        LexicalHit("e1", "alpha", 0, 5, "exact", ["C-A"], 0),
        LexicalHit("e2", "beta", 6, 10, "exact", ["C-B"], 0),
    ]
    with_pairs_zero_weight = weight_sweep(hits, {("C-A", "C-B"): 0.8}, [0.0])[0]
    no_pairs_zero_weight = weight_sweep(hits, {}, [0.0])[0]
    assert with_pairs_zero_weight == no_pairs_zero_weight
