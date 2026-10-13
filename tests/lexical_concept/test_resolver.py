from __future__ import annotations

import json

from core.engine.lexical_concept.pipeline import _classify_span_resolution
from core.lexical.matcher import LexicalHit
from core.resolver.resolver import resolve_hit


def test_resolver_picks_top_specificity() -> None:
    hit = LexicalHit(
        entry_id="A-1",
        matched_text="identity diffusion",
        span_start=0,
        span_end=18,
        match_type="phrase",
        candidate_concept_ids=["C-LOW", "C-HIGH"],
        priority=10
    )
    concept_index = {
        "C-LOW": {"specificity_rank": 2, "preferred_label": "low"},
        "C-HIGH": {"specificity_rank": 7, "preferred_label": "high"},
    }
    out = resolve_hit(hit, concept_index, mode="clinical_speech")
    assert out["winning_concept_id"] == "C-HIGH"
    assert out["candidate_scores"]["C-HIGH"] > out["candidate_scores"]["C-LOW"]


def test_resolver_is_schema_compatible() -> None:
    hit = LexicalHit(
        entry_id="A-2",
        matched_text="split",
        span_start=3,
        span_end=8,
        match_type="exact",
        candidate_concept_ids=["C-A"],
        priority=1
    )
    out = resolve_hit(hit, {"C-A": {"specificity_rank": 1, "preferred_label": "a"}})
    assert "rule_trace" in out
    assert "winning_reason_codes" in out
    assert "rejected_reason_codes" in out
    assert "audit" in out


def test_tiebreak_lexical_id_when_scores_and_specificity_equal() -> None:
    hit = LexicalHit(
        entry_id="x",
        matched_text="tie",
        span_start=0,
        span_end=3,
        match_type="exact",
        candidate_concept_ids=["Z-WING", "A-WING"],
        priority=0,
    )
    concepts = {
        "Z-WING": {"specificity_rank": 3, "preferred_label": "zztop"},
        "A-WING": {"specificity_rank": 3, "preferred_label": "aaalpha"},
    }
    out = resolve_hit(hit, concepts, canonical_text="tie blob")
    assert out["winning_concept_id"] == "A-WING"
    assert any("tiebreak" in x for x in out.get("winning_reason_codes", []))


def test_pipeline_classifies_below_threshold_hit_as_unresolved_evidence() -> None:
    resolution = {
        "candidate_scores": {"C-B": 0.49, "C-A": 0.25},
        "winning_concept_id": "C-B",
        "winning_reason_codes": ["top_score_unique"],
        "rejected_reason_codes": ["candidate_rejected:C-A"],
    }

    classified, is_resolved = _classify_span_resolution(
        resolution,
        min_resolve_score=0.5,
    )

    assert is_resolved is False
    assert classified == {
        "candidate_scores": {"C-B": 0.49, "C-A": 0.25},
        "winning_concept_id": None,
        "winning_reason_codes": [],
        "rejected_reason_codes": [
            "below_threshold",
            "candidate_rejected:C-A",
            "candidate_rejected:C-B",
        ],
    }


def test_pipeline_classifies_empty_scores_as_no_candidates() -> None:
    resolution = {
        "candidate_scores": {},
        "winning_concept_id": None,
        "winning_reason_codes": ["no_candidates"],
        "rejected_reason_codes": ["no_candidate_activation"],
    }

    classified, is_resolved = _classify_span_resolution(
        resolution,
        min_resolve_score=0.5,
    )

    assert is_resolved is False
    assert classified["winning_concept_id"] is None
    assert classified["winning_reason_codes"] == []
    assert classified["rejected_reason_codes"] == ["no_candidates"]


def test_pipeline_preserves_resolved_span_behavior_unchanged() -> None:
    resolution = {
        "candidate_scores": {"C-B": 0.75, "C-A": 0.25},
        "winning_concept_id": "C-B",
        "winning_reason_codes": ["top_score_unique"],
        "rejected_reason_codes": ["candidate_rejected:C-A"],
    }

    before = json.dumps(
        resolution,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    classified, is_resolved = _classify_span_resolution(
        resolution,
        min_resolve_score=0.5,
    )

    assert is_resolved is True
    assert classified is resolution
    assert json.dumps(
        classified,
        sort_keys=True,
        separators=(",", ":"),
    ).encode() == before

