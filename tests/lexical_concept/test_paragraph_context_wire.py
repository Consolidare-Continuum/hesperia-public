# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""CORE-D2 W8 — paragraph-scoped runtime context wiring tests."""

from __future__ import annotations

from core.lexical.matcher import LexicalHit
from core.resolver.context import paragraph_index_for_span, paragraph_spans
from core.resolver.resolver import resolve_hit, resolve_paragraph_hits


def test_paragraph_spans_splits_on_blank_lines() -> None:
    text = "alpha beta\n\ngamma\n\n\ndelta epsilon"
    spans = paragraph_spans(text)
    assert len(spans) == 3
    assert text[spans[0][0] : spans[0][1]] == "alpha beta"
    assert text[spans[1][0] : spans[1][1]] == "gamma"
    assert text[spans[2][0] : spans[2][1]] == "delta epsilon"


def test_paragraph_spans_empty_text_returns_empty() -> None:
    assert paragraph_spans("") == []
    assert paragraph_spans("\n\n\n") == []


def test_paragraph_index_for_span_matches_containing_paragraph() -> None:
    text = "alpha beta\n\ngamma delta"
    spans = paragraph_spans(text)
    assert paragraph_index_for_span(spans, 0) == 0
    assert paragraph_index_for_span(spans, spans[1][0]) == 1
    assert paragraph_index_for_span(spans, spans[1][0] + 2) == 1


def test_paragraph_index_for_span_empty_spans_returns_zero() -> None:
    assert paragraph_index_for_span([], 5) == 0


def _hit(entry_id: str, text: str, start: int, candidates: list[str]) -> LexicalHit:
    return LexicalHit(
        entry_id=entry_id,
        matched_text=text,
        span_start=start,
        span_end=start + len(text),
        match_type="exact",
        candidate_concept_ids=candidates,
        priority=0,
    )


def _concept_index() -> dict[str, dict]:
    return {
        "C-A": {"preferred_label": "Alpha", "specificity_rank": 5},
        "C-B": {"preferred_label": "Beta", "specificity_rank": 5},
        "C-C": {"preferred_label": "Gamma", "specificity_rank": 5},
    }


def test_resolve_paragraph_hits_weight_zero_identical_to_single_pass_baseline() -> None:
    """CORE-D2-088 core invariant: at weight 0.0, two-pass output == plain baseline."""
    hits = [
        _hit("e1", "alpha", 0, ["C-A"]),
        _hit("e2", "beta", 6, ["C-B"]),
    ]
    dict_d_pairs = {("C-A", "C-B"): 0.9}  # would matter a lot if weight were nonzero
    two_pass = resolve_paragraph_hits(
        hits, _concept_index(), canonical_text="alpha beta", dict_d_pairs=dict_d_pairs, empirical_weight_override=0.0
    )
    single_pass_baseline = [
        resolve_hit(
            h, _concept_index(), canonical_text="alpha beta", dict_d_pairs=None,
            empirical_context_ids=frozenset(), empirical_weight_override=0.0,
        )
        for h in hits
    ]
    for two, base in zip(two_pass, single_pass_baseline):
        assert two["winning_concept_id"] == base["winning_concept_id"]
        assert two["candidate_scores"] == base["candidate_scores"]


def test_resolve_paragraph_hits_context_excludes_own_baseline_winner() -> None:
    """A hit must never see its own baseline winner as empirical context."""
    hits = [_hit("e1", "alpha", 0, ["C-A"])]
    # A single-hit paragraph: no OTHER hits exist, so context must be empty
    # regardless of what this hit's own baseline winner was.
    results = resolve_paragraph_hits(
        hits, _concept_index(), canonical_text="alpha",
        dict_d_pairs={("C-A", "C-A"): 0.9}, empirical_weight_override=1.0,
    )
    assert results[0]["audit"]["empirical_context_size"] == 0


def test_resolve_paragraph_hits_nonzero_weight_uses_cross_hit_context() -> None:
    """At nonzero weight, a hit's score DOES change based on another hit's baseline winner."""
    hits = [
        _hit("e1", "alpha", 0, ["C-A"]),
        _hit("e2", "beta", 6, ["C-B"]),
    ]
    dict_d_pairs = {("C-A", "C-B"): 0.9}
    with_dict_d = resolve_paragraph_hits(
        hits, _concept_index(), canonical_text="alpha beta", dict_d_pairs=dict_d_pairs, empirical_weight_override=1.0
    )
    without_dict_d = resolve_paragraph_hits(
        hits, _concept_index(), canonical_text="alpha beta", dict_d_pairs=None, empirical_weight_override=1.0
    )
    # C-A's score should be higher with a positive empirical pair to C-B (the other hit's winner)
    assert with_dict_d[0]["candidate_scores"]["C-A"] > without_dict_d[0]["candidate_scores"]["C-A"]
    assert with_dict_d[0]["audit"]["candidates_detail"][0]["empirical_pair_concept_id"] == "C-B"


def test_resolve_hit_empirical_context_defaults_to_empty_not_same_hit_siblings() -> None:
    """Forbidden per W0: same-hit candidate siblings must never leak into empirical context by default."""
    hit = _hit("e1", "alpha", 0, ["C-A", "C-B"])
    dict_d_pairs = {("C-A", "C-B"): 0.9}
    # No empirical_context_ids passed -> must be inert (empty context), not use hit's own siblings.
    result = resolve_hit(hit, _concept_index(), canonical_text="alpha", dict_d_pairs=dict_d_pairs, empirical_weight_override=1.0)
    for detail in result["audit"]["candidates_detail"]:
        assert detail["empirical_boost"] == 0.0
        assert detail["empirical_pair_concept_id"] is None
    assert result["audit"]["empirical_context_size"] == 0


def test_resolve_paragraph_hits_empty_hit_list_returns_empty() -> None:
    assert resolve_paragraph_hits([], _concept_index()) == []
