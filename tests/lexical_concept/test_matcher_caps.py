# HESPERIA — RAD. Ethan PO-03 / PO-04 matcher behavior.
from __future__ import annotations

from core.lexical.matcher import match_dict_a


def test_longest_span_wins_at_same_start() -> None:
    text = "object relations theory"
    entries = [
        {
            "entry_id": "e1",
            "normalized_form": "object",
            "match_type": "phrase",
            "candidate_concept_ids": ["C1"],
            "priority": 0,
        },
        {
            "entry_id": "e2",
            "normalized_form": "object relations",
            "match_type": "phrase",
            "candidate_concept_ids": ["C2"],
            "priority": 0,
        },
    ]
    acc, rej = match_dict_a(text, entries)
    assert len(acc) == 1
    assert acc[0].matched_text == "object relations"
    assert acc[0].entry_id == "e2"


def test_max_accepted_caps_deterministically() -> None:
    text = "a b c d e"
    entries = [
        {
            "entry_id": f"e{i}",
            "normalized_form": tok,
            "match_type": "exact",
            "candidate_concept_ids": [f"C{i}"],
            "priority": 0,
        }
        for i, tok in enumerate(text.split(), start=1)
    ]
    acc, rej = match_dict_a(text, entries, max_accepted=2)
    assert len(acc) == 2
    assert len(rej) >= 1


def test_max_accepted_without_diversity_key_is_position_ordered() -> None:
    """Legacy behavior: no diversity_key -> flat slice by document position."""
    text = "a b c d e"
    entries = [
        {
            "entry_id": f"e{i}",
            "normalized_form": tok,
            "match_type": "exact",
            "candidate_concept_ids": [f"C{i}"],
            "priority": 0,
        }
        for i, tok in enumerate(text.split(), start=1)
    ]
    acc, rej = match_dict_a(text, entries, max_accepted=3)
    assert [h.matched_text for h in acc] == ["a", "b", "c"]
    assert [h.matched_text for h in rej] == ["d", "e"]


def test_diversity_key_spreads_cap_across_groups_instead_of_front_loading() -> None:
    """Without diversity awareness, a group that only appears late in the text
    (group Z here, matched only by the last 6 of 9 tokens) would be starved
    entirely by a flat position cut. diversity_key should still give it a seat.
    """
    text = "a a a a a z z z z"
    entries = [
        {
            "entry_id": "a_entry",
            "normalized_form": "a",
            "match_type": "exact",
            "candidate_concept_ids": ["C_group_a"],
            "priority": 0,
        },
        {
            "entry_id": "z_entry",
            "normalized_form": "z",
            "match_type": "exact",
            "candidate_concept_ids": ["C_group_z"],
            "priority": 0,
        },
    ]
    acc, rej = match_dict_a(
        text,
        entries,
        max_accepted=4,
        diversity_key=lambda hit: str(hit.candidate_concept_ids[0]),
    )
    assert len(acc) == 4
    groups = {h.candidate_concept_ids[0] for h in acc}
    assert groups == {"C_group_a", "C_group_z"}, "both groups should survive the cap"
    # Selected hits must come back in document order (downstream code relies on
    # this for sequential-association / textual-recency features).
    assert [h.span_start for h in acc] == sorted(h.span_start for h in acc)


def test_diversity_key_falls_back_to_flat_cut_when_fewer_groups_than_budget() -> None:
    """A single group with plenty of budget behaves the same as no diversity_key."""
    text = "a b c d e"
    entries = [
        {
            "entry_id": f"e{i}",
            "normalized_form": tok,
            "match_type": "exact",
            "candidate_concept_ids": ["C_only_group"],
            "priority": 0,
        }
        for i, tok in enumerate(text.split(), start=1)
    ]
    acc, rej = match_dict_a(
        text, entries, max_accepted=3, diversity_key=lambda hit: str(hit.candidate_concept_ids[0])
    )
    assert [h.matched_text for h in acc] == ["a", "b", "c"]
