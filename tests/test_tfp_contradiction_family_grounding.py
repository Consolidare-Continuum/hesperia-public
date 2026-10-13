# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""Family/area grounding for topology-derived contradiction pairs.

Coactivation pairs are expanded at family/area granularity. A pair of never-hit
family members is still family-grounded when a sibling in that family was
lexically hit. Concept-level zero-lex is diagnostic only.
"""

from __future__ import annotations

from runtime.pipeline.run_tfp_file_pipeline import (
    _build_contradiction_reconciliation,
    _filter_canonical_contradictions_for_activation,
)


def _pair(a: str, b: str, score: float = 1.0) -> dict:
    return {"pair": [a, b], "raw_contradiction_score": score, "coactivation": 1.0}


def test_same_family_unhit_pair_is_family_grounded_when_sibling_was_hit() -> None:
    """Chiron example class: [B_A10_F10_003, B_A10_F10_006] while only 002 was lexically hit."""
    rec = _build_contradiction_reconciliation(
        session_id="s",
        direct_rows=[],
        topology_rows=[_pair("B_A10_F10_003", "B_A10_F10_006")],
        lexical_hits_accepted=1,
        lexical_concept_counts={"B_A10_F10_002": 3},
    )
    support = rec["lexical_support"]
    assert support["grounding_granularity"] == "family"
    assert support["zero_lexical_evidence_share"] == 0.0
    assert support["inferred_share"] == 0.0
    assert support["zero_lexical_evidence_share_concept"] == 1.0
    assert support["zero_area_lexical_evidence_share"] == 0.0
    audit = rec["per_contradiction_audit"][0]
    assert audit["direct_vs_inferred"] == "direct"
    assert audit["lexical_evidence"]["left_family_hits"] >= 1
    assert audit["lexical_evidence"]["right_family_hits"] >= 1
    assert audit["lexical_evidence"]["total_hits"] == 0


def test_cross_family_pair_is_ungrounded_when_one_family_never_hit() -> None:
    rec = _build_contradiction_reconciliation(
        session_id="s",
        direct_rows=[],
        topology_rows=[_pair("B_A10_F10_002", "B_A2_F5_001")],
        lexical_hits_accepted=1,
        lexical_concept_counts={"B_A10_F10_002": 2},
    )
    support = rec["lexical_support"]
    assert support["zero_lexical_evidence_share"] == 1.0
    assert support["inferred_share"] == 0.0
    assert rec["per_contradiction_audit"][0]["direct_vs_inferred"] == "inferred"


def test_both_families_never_hit_counts_as_inferred() -> None:
    rec = _build_contradiction_reconciliation(
        session_id="s",
        direct_rows=[],
        topology_rows=[_pair("B_A11_F3_001", "B_A11_F3_002")],
        lexical_hits_accepted=2,
        lexical_concept_counts={"B_A10_F10_002": 2},
    )
    support = rec["lexical_support"]
    assert support["zero_lexical_evidence_share"] == 1.0
    assert support["inferred_share"] == 1.0
    assert support["zero_area_lexical_evidence_share"] == 1.0


def test_named_concept_without_b_id_requires_direct_hit() -> None:
    rec = _build_contradiction_reconciliation(
        session_id="s",
        direct_rows=[],
        topology_rows=[_pair("TFP_DENIAL", "B_A10_F10_006")],
        lexical_hits_accepted=1,
        lexical_concept_counts={"B_A10_F10_002": 1},
    )
    support = rec["lexical_support"]
    assert support["zero_lexical_evidence_share"] == 1.0
    assert support["inferred_share"] == 0.0


def test_activation_filter_keeps_family_grounded_low_score_pair() -> None:
    rows = [_pair("B_A10_F10_003", "B_A10_F10_006", score=0.05)]
    kept, stats = _filter_canonical_contradictions_for_activation(
        rows,
        lexical_concept_counts={"B_A10_F10_002": 1},
    )
    assert len(kept) == 1
    assert stats["dropped_count"] == 0
