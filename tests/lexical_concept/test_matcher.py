from __future__ import annotations

from core.lexical.matcher import match_dict_a


def test_matcher_prefers_longest_phrase() -> None:
    text = "identity diffusion pattern"
    entries = [
        {
            "entry_id": "A-1",
            "normalized_form": "identity",
            "match_type": "exact",
            "candidate_concept_ids": ["C-1"],
            "priority": 1
        },
        {
            "entry_id": "A-2",
            "normalized_form": "identity diffusion",
            "match_type": "phrase",
            "candidate_concept_ids": ["C-2"],
            "priority": 1
        }
    ]
    accepted, rejected = match_dict_a(text, entries)
    assert accepted[0].entry_id == "A-2"
    assert any(hit.entry_id == "A-1" for hit in rejected)


def test_matcher_keeps_non_overlapping_hits() -> None:
    text = "identity diffusion and primitive defense"
    entries = [
        {
            "entry_id": "A-2",
            "normalized_form": "identity diffusion",
            "match_type": "phrase",
            "candidate_concept_ids": ["C-2"],
            "priority": 1
        },
        {
            "entry_id": "A-3",
            "normalized_form": "primitive defense",
            "match_type": "phrase",
            "candidate_concept_ids": ["C-3"],
            "priority": 1
        }
    ]
    accepted, rejected = match_dict_a(text, entries)
    assert len(accepted) == 2
    assert len(rejected) == 0


def test_matcher_negative_pattern_blocks_overlapping_positive() -> None:
    entries = [
        {
            "entry_id": "NEG-1",
            "normalized_form": "расщепление атома",
            "match_type": "phrase",
            "candidate_concept_ids": [],
            "negative_patterns": ["*"],
            "priority": 999,
        },
        {
            "entry_id": "A-POS",
            "normalized_form": "расщепление",
            "match_type": "exact",
            "candidate_concept_ids": ["TFP_SPLITTING"],
            "priority": 100,
        },
    ]
    acc, _rej = match_dict_a("расщепление атома в тексте", entries)
    assert not any(h.entry_id == "A-POS" for h in acc)
    acc2, _ = match_dict_a("примитивное расщепление в терапии", entries)
    assert any(h.entry_id == "A-POS" for h in acc2)

