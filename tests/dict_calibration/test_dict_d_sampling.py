# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""CORE-D2 W7 — sampling and stability tests."""

from __future__ import annotations

from typing import Any

import pytest

from tools.dict_calibration import dict_d_sampling as sampling
from tools.dict_calibration import dict_d_stability as stability
from tools.dict_calibration.dict_d_builder import build_dict_d
from tools.dict_calibration.resolved_export import _paragraph_identity

_HEX = "0123456789abcdef"
SHA_BOOK = {f"book-{i:03d}": _HEX[i % 16] * 64 for i in range(1, 12)}


def _provenance() -> dict[str, Any]:
    return {
        "candidate_bundle_id": "1" * 64,
        "candidate_manifest_sha256": "2" * 64,
        "corpus_snapshot_sha256": "3" * 64,
        "resolver_version": "lexical-concept-resolver-v1",
        "resolver_implementation_sha256": "1" * 64,
        "resolver_authority": "canonical-run-dlcr-pipeline",
        "resolver_configuration_sha256": "4" * 64,
        "segmentation_rule": "frozen-paragraph-segmentation-v1",
        "export_rule": "resolved-corpus-export-v1",
        "dict_d_enabled": False,
        "dict_d_effective_weight": 0.0,
    }


def _span(position: int, end: int, surface: str, winner: str) -> dict[str, Any]:
    return {
        "span_position": position,
        "span_end": end,
        "surface": surface,
        "winning_concept_id": winner,
        "candidate_scores": [{"concept_id": winner, "score": 1.0}],
    }


def _paragraph_for_concepts(book_sha: str, ordinal: int, concepts: list[str]) -> dict[str, Any]:
    words = [f"w{c}" for c in concepts] or ["none"]
    text = " ".join(words)
    spans = []
    pos = 0
    for c, w in zip(concepts, words):
        spans.append(_span(pos, pos + len(w), w, c))
        pos += len(w) + 1
    return {
        "paragraph_id": _paragraph_identity(book_sha, ordinal, text),
        "source_ordinal": ordinal,
        "text": text,
        "resolved_spans": spans,
    }


def _book(book_id: str, per_paragraph_concepts: list[list[str]]) -> dict[str, Any]:
    sha = SHA_BOOK[book_id]
    paragraphs = [_paragraph_for_concepts(sha, i, cs) for i, cs in enumerate(per_paragraph_concepts)]
    return {"book_id": book_id, "source_path": f"{book_id}.md", "source_sha256": sha, "paragraphs": paragraphs}


def _export(books: list[dict[str, Any]]) -> dict[str, Any]:
    return {"schema": "hesperia.dict_d.resolved_corpus.v1", "provenance": _provenance(), "books": books, "unresolved": []}


def _mixed_corpus() -> dict[str, Any]:
    """N=10 paragraphs. (F,G): n_F=n_G=n_FG=6 -> npmi=1.0, novel (high-NPMI stratum).
    (D,E): n_D=n_E=6, n_DE=1 -> negative npmi; authored-related -> agrees (disagreement stratum)."""
    books = [
        _book("book-001", [["D", "E"], ["D"], ["D"], ["F", "G"]]),
        _book("book-002", [["D"], ["E"], ["E"], ["F", "G"]]),
        _book("book-003", [["D"], ["E"], ["F", "G"]]),
        _book("book-004", [["D", "E"], ["F", "G"]]),
    ]
    return _export(books)


def _dict_b_with_relation(a: str, b: str) -> list[dict[str, Any]]:
    return [{"concept_id": a, "related_concept_ids": [b]}, {"concept_id": b, "related_concept_ids": [a]}]


def test_mixed_corpus_produces_expected_strata_membership() -> None:
    export = _mixed_corpus()
    built = build_dict_d(resolved_export=export, candidate_dict_b=_dict_b_with_relation("D", "E"), evidence_floor=0)
    by_pair = {(r["concept_id_a"], r["concept_id_b"]): r for r in built["rows"]}
    assert by_pair[("D", "E")]["agreement_with_b"] == "agrees"
    assert by_pair[("D", "E")]["npmi"] < 0
    assert by_pair[("F", "G")]["agreement_with_b"] == "novel"
    assert by_pair[("F", "G")]["npmi"] == pytest.approx(1.0)


def test_select_high_npmi_novel_finds_the_novel_pair() -> None:
    export = _mixed_corpus()
    built = build_dict_d(resolved_export=export, candidate_dict_b=_dict_b_with_relation("D", "E"), evidence_floor=0)
    selected = sampling.select_high_npmi_novel(built["rows"])
    pairs = {(r["concept_id_a"], r["concept_id_b"]) for r in selected}
    assert ("F", "G") in pairs
    assert ("D", "E") not in pairs


def test_select_authored_edge_disagreement_finds_the_agrees_pair() -> None:
    export = _mixed_corpus()
    built = build_dict_d(resolved_export=export, candidate_dict_b=_dict_b_with_relation("D", "E"), evidence_floor=0)
    selected = sampling.select_authored_edge_disagreement(built["rows"])
    pairs = {(r["concept_id_a"], r["concept_id_b"]) for r in selected}
    assert ("D", "E") in pairs
    assert ("F", "G") not in pairs


def test_sampling_is_deterministic_across_runs() -> None:
    export = _mixed_corpus()
    built = build_dict_d(resolved_export=export, candidate_dict_b=_dict_b_with_relation("D", "E"), evidence_floor=0)
    first = sampling.select_high_npmi_novel(built["rows"])
    second = sampling.select_high_npmi_novel(built["rows"])
    assert first == second


def test_attach_excerpts_finds_cooccurring_paragraph() -> None:
    export = _mixed_corpus()
    built = build_dict_d(resolved_export=export, candidate_dict_b=_dict_b_with_relation("D", "E"), evidence_floor=0)
    pair_row = next(r for r in built["rows"] if (r["concept_id_a"], r["concept_id_b"]) == ("F", "G"))
    excerpts = sampling.attach_excerpts([pair_row], export)
    assert len(excerpts) == 1
    assert excerpts[0]["book_id"] == "book-001"
    assert "wF" in excerpts[0]["text"] and "wG" in excerpts[0]["text"]


def test_attach_excerpts_fails_closed_when_no_paragraph_matches() -> None:
    export = _mixed_corpus()
    fabricated_row = {"concept_id_a": "C-GHOST-A", "concept_id_b": "C-GHOST-B"}
    with pytest.raises(sampling.ExcerptNotFoundError):
        sampling.attach_excerpts([fabricated_row], export)


def test_build_review_records_has_no_prejudged_disposition() -> None:
    export = _mixed_corpus()
    built = build_dict_d(resolved_export=export, candidate_dict_b=_dict_b_with_relation("D", "E"), evidence_floor=0)
    selected = sampling.select_high_npmi_novel(built["rows"])
    records = sampling.build_review_records(selected, export, stratum=sampling.STRATUM_HIGH_NPMI_NOVEL)
    assert all(r["disposition"] is None for r in records)
    assert all(r["stratum"] == sampling.STRATUM_HIGH_NPMI_NOVEL for r in records)


# --- stability ---


def _redundant_corpus() -> dict[str, Any]:
    """10 books; (F,G) co-occurs once per book, (D,E) co-occurs in 2 of 10 books —
    every pair's evidence is spread across multiple books, so no single removal
    should wreck the graph."""
    de_pattern = [
        ["D", "E"], ["D"], ["E"], ["D"], ["E"],
        ["D", "E"], ["E"], ["D"], ["E"], ["D"],
    ]
    books = [_book(f"book-{i:03d}", [["F", "G"], de_pattern[i - 1]]) for i in range(1, 11)]
    return _export(books)


def test_stable_corpus_passes_leave_one_book_out() -> None:
    """Every pair's evidence is spread across multiple books; removing one shouldn't wreck the graph."""
    export = _redundant_corpus()
    result = stability.leave_one_book_out(export, _dict_b_with_relation("D", "E"), evidence_floor=0)
    for book_id, cmp in result["removed_book_results"].items():
        assert cmp["passed"], f"{book_id}: {cmp}"
    assert result["all_passed"] is True


def test_fragile_pair_disappears_when_its_sole_book_is_removed() -> None:
    """A pair with all its evidence concentrated in one book must vanish under that book's removal."""
    books = [
        _book("book-001", [["X", "Y"], ["X", "Y"], ["X", "Y"]]),  # sole evidence for (X,Y)
        _book("book-002", [["D", "E"], ["D"], ["E"]]),
        _book("book-003", [["D", "E"], ["D"], ["E"]]),
    ]
    export = _export(books)
    result = stability.leave_one_book_out(export, [], evidence_floor=0)
    removal_of_book1 = result["removed_book_results"]["book-001"]
    assert removal_of_book1["n_disappeared"] >= 1


def test_corpus_growth_adds_new_pairs_without_breaking_baseline() -> None:
    export = _mixed_corpus()
    added = _book("book-005", [["H", "I"], ["H", "I"]])
    result = stability.corpus_growth(export, added, _dict_b_with_relation("D", "E"), evidence_floor=0)
    assert result["growth_result"]["n_appeared"] >= 1


def test_leave_one_book_out_requires_at_least_two_books() -> None:
    export = _export([_book("book-001", [["D", "E"]])])
    with pytest.raises(ValueError, match="at least 2 books"):
        stability.leave_one_book_out(export, [], evidence_floor=0)


def test_compare_rebuilds_identical_inputs_scores_perfectly() -> None:
    rows = [
        {"concept_id_a": "C-A", "concept_id_b": "C-B", "cooc_count": 5, "npmi": 0.4, "g2": 10.0, "agreement_with_b": "novel", "source_books": ["book-001"]},
    ]
    result = stability.compare_rebuilds(rows, rows)
    assert result["rank_correlation"] == pytest.approx(1.0)
    assert result["npmi_drift"] == 0.0
    assert result["top_k_jaccard"] == 1.0
    assert result["passed"] is True
