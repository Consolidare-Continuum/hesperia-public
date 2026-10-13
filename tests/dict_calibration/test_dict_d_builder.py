# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""CORE-D2 W5 — deterministic Dict D builder tests."""

from __future__ import annotations

import hashlib
import math
from pathlib import Path
from typing import Any

import pytest

from tools.dict_calibration import dict_d_builder as ddb
from tools.dict_calibration.resolved_export import _paragraph_identity

SHA_BOOK1 = "a" * 64
SHA_BOOK2 = "b" * 64
SHA_BOOK3 = "c" * 64
SHA_CANDIDATE = "d" * 64
SHA_MANIFEST = "e" * 64
SHA_CORPUS = "f" * 64
SHA_CONFIG = "0" * 64


def _provenance() -> dict[str, Any]:
    return {
        "candidate_bundle_id": SHA_CANDIDATE,
        "candidate_manifest_sha256": SHA_MANIFEST,
        "corpus_snapshot_sha256": SHA_CORPUS,
        "resolver_version": "lexical-concept-resolver-v1",
        "resolver_implementation_sha256": SHA_CANDIDATE,
        "resolver_authority": "canonical-run-dlcr-pipeline",
        "resolver_configuration_sha256": SHA_CONFIG,
        "segmentation_rule": "frozen-paragraph-segmentation-v1",
        "export_rule": "resolved-corpus-export-v1",
        "dict_d_enabled": False,
        "dict_d_effective_weight": 0.0,
    }


def _span(position: int, end: int, surface: str, winner: str, *, extra_score: float | None = None) -> dict[str, Any]:
    scores = [{"concept_id": winner, "score": 1.0}]
    if extra_score is not None:
        scores.append({"concept_id": "C-ZZZ", "score": extra_score})
        scores.sort(key=lambda c: c["concept_id"])
    return {
        "span_position": position,
        "span_end": end,
        "surface": surface,
        "winning_concept_id": winner,
        "candidate_scores": scores,
    }


def _paragraph(book_sha: str, ordinal: int, text: str, spans: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "paragraph_id": _paragraph_identity(book_sha, ordinal, text),
        "source_ordinal": ordinal,
        "text": text,
        "resolved_spans": spans,
    }


def _book(book_id: str, source_path: str, sha: str, paragraphs: list[dict[str, Any]]) -> dict[str, Any]:
    return {"book_id": book_id, "source_path": source_path, "source_sha256": sha, "paragraphs": paragraphs}


def _three_book_export() -> dict[str, Any]:
    """Hand-computable fixture: 5 paragraphs, N=5, n_A=3, n_B=3, n_AB=2."""
    book1 = _book(
        "book-001",
        "001.md",
        SHA_BOOK1,
        [
            _paragraph(SHA_BOOK1, 0, "alpha beta", [_span(0, 5, "alpha", "C-A"), _span(6, 10, "beta", "C-B")]),
            _paragraph(SHA_BOOK1, 1, "gamma", []),
        ],
    )
    book2 = _book(
        "book-002",
        "002.md",
        SHA_BOOK2,
        [
            _paragraph(SHA_BOOK2, 0, "alpha beta", [_span(0, 5, "alpha", "C-A"), _span(6, 10, "beta", "C-B")]),
            _paragraph(SHA_BOOK2, 1, "alpha", [_span(0, 5, "alpha", "C-A")]),
        ],
    )
    book3 = _book(
        "book-003",
        "003.md",
        SHA_BOOK3,
        [_paragraph(SHA_BOOK3, 0, "beta", [_span(0, 4, "beta", "C-B")])],
    )
    return {
        "schema": "hesperia.dict_d.resolved_corpus.v1",
        "provenance": _provenance(),
        "books": [book1, book2, book3],
        "unresolved": [],
    }


def _dict_b(relations: dict[str, list[str]]) -> list[dict[str, Any]]:
    return [{"concept_id": cid, "related_concept_ids": sorted(rel)} for cid, rel in sorted(relations.items())]


def test_pair_counts_and_marginals_match_hand_computation() -> None:
    export = _three_book_export()
    built = ddb.build_dict_d(resolved_export=export, candidate_dict_b=_dict_b({}), evidence_floor=0)
    rows = {(r["concept_id_a"], r["concept_id_b"]): r for r in built["rows"]}
    assert len(rows) == 1
    row = rows[("C-A", "C-B")]
    assert row["cooc_count"] == 2
    assert row["source_books"] == ["book-001", "book-002"]
    assert built["summary"]["n_paragraphs"] == 5


def test_npmi_and_g2_match_independent_reference_computation() -> None:
    export = _three_book_export()
    built = ddb.build_dict_d(resolved_export=export, candidate_dict_b=_dict_b({}), evidence_floor=0)
    row = built["rows"][0]

    n, n_ij, n_i, n_j = 5, 2, 3, 3
    pmi = math.log((n_ij * n) / (n_i * n_j))
    expected_npmi = pmi / -math.log(n_ij / n)
    assert row["npmi"] == pytest.approx(expected_npmi, rel=1e-12)

    o11, o10, o01, o00 = n_ij, n_i - n_ij, n_j - n_ij, n - n_i - n_j + n_ij
    r1, r0, c1, c0 = n_i, n - n_i, n_j, n - n_j
    expected_g2 = 2.0 * sum(
        o * math.log(o / e)
        for o, e in ((o11, r1 * c1 / n), (o10, r1 * c0 / n), (o01, r0 * c1 / n), (o00, r0 * c0 / n))
        if o > 0
    )
    assert row["g2"] == pytest.approx(expected_g2, rel=1e-12)
    assert row["g2"] >= 0.0


def test_perfect_cooccurrence_npmi_is_exactly_one() -> None:
    book = _book(
        "book-001",
        "001.md",
        SHA_BOOK1,
        [
            _paragraph(SHA_BOOK1, 0, "alpha beta", [_span(0, 5, "alpha", "C-A"), _span(6, 10, "beta", "C-B")]),
            _paragraph(SHA_BOOK1, 1, "alpha beta", [_span(0, 5, "alpha", "C-A"), _span(6, 10, "beta", "C-B")]),
        ],
    )
    export = {"schema": "hesperia.dict_d.resolved_corpus.v1", "provenance": _provenance(), "books": [book], "unresolved": []}
    built = ddb.build_dict_d(resolved_export=export, candidate_dict_b=_dict_b({}), evidence_floor=0)
    assert built["rows"][0]["npmi"] == 1.0


def test_repeated_concept_in_one_paragraph_counts_once() -> None:
    """A concept resolved via two spans in the same paragraph must not double the marginal."""
    book = _book(
        "book-001",
        "001.md",
        SHA_BOOK1,
        [
            _paragraph(
                SHA_BOOK1,
                0,
                "alpha alpha beta",
                [_span(0, 5, "alpha", "C-A"), _span(6, 11, "alpha", "C-A"), _span(12, 16, "beta", "C-B")],
            )
        ],
    )
    export = {"schema": "hesperia.dict_d.resolved_corpus.v1", "provenance": _provenance(), "books": [book], "unresolved": []}
    built = ddb.build_dict_d(resolved_export=export, candidate_dict_b=_dict_b({}), evidence_floor=0)
    assert built["summary"]["n_pairs_observed"] == 1
    assert built["rows"][0]["cooc_count"] == 1


def test_evidence_floor_excludes_row_without_altering_other_marginals() -> None:
    export = _three_book_export()
    below = ddb.build_dict_d(resolved_export=export, candidate_dict_b=_dict_b({}), evidence_floor=3)
    above = ddb.build_dict_d(resolved_export=export, candidate_dict_b=_dict_b({}), evidence_floor=0)
    assert below["rows"] == []
    assert below["summary"]["n_pairs_observed"] == above["summary"]["n_pairs_observed"] == 1
    assert below["summary"]["n_pairs_released"] == 0
    assert above["summary"]["n_pairs_released"] == 1


def test_agreement_label_agrees_when_related_either_direction() -> None:
    export = _three_book_export()
    built_a_to_b = ddb.build_dict_d(resolved_export=export, candidate_dict_b=_dict_b({"C-A": ["C-B"]}), evidence_floor=0)
    built_b_to_a = ddb.build_dict_d(resolved_export=export, candidate_dict_b=_dict_b({"C-B": ["C-A"]}), evidence_floor=0)
    built_none = ddb.build_dict_d(resolved_export=export, candidate_dict_b=_dict_b({}), evidence_floor=0)
    assert built_a_to_b["rows"][0]["agreement_with_b"] == "agrees"
    assert built_b_to_a["rows"][0]["agreement_with_b"] == "agrees"
    assert built_none["rows"][0]["agreement_with_b"] == "novel"


def test_agreement_label_never_emits_contradicts() -> None:
    export = _three_book_export()
    built = ddb.build_dict_d(resolved_export=export, candidate_dict_b=_dict_b({}), evidence_floor=0)
    labels = {r["agreement_with_b"] for r in built["rows"]}
    assert labels <= {"agrees", "novel"}
    assert "contradicts" not in labels


def test_zero_paragraph_export_rejected() -> None:
    export = {
        "schema": "hesperia.dict_d.resolved_corpus.v1",
        "provenance": _provenance(),
        "books": [_book("book-001", "001.md", SHA_BOOK1, [])],
        "unresolved": [],
    }
    with pytest.raises(ValueError):
        ddb.build_dict_d(resolved_export=export, candidate_dict_b=_dict_b({}))


def test_malformed_resolved_export_rejected_before_counting() -> None:
    export = _three_book_export()
    del export["schema"]
    with pytest.raises(ValueError):
        ddb.build_dict_d(resolved_export=export, candidate_dict_b=_dict_b({}))


def test_negative_evidence_floor_rejected() -> None:
    export = _three_book_export()
    with pytest.raises(ddb.DictDBuildError):
        ddb.build_dict_d(resolved_export=export, candidate_dict_b=_dict_b({}), evidence_floor=-1)


def test_two_builds_from_identical_input_are_byte_identical() -> None:
    export = _three_book_export()
    built_1 = ddb.build_dict_d(resolved_export=export, candidate_dict_b=_dict_b({"C-A": ["C-B"]}), evidence_floor=0)
    built_2 = ddb.build_dict_d(resolved_export=export, candidate_dict_b=_dict_b({"C-A": ["C-B"]}), evidence_floor=0)
    rows_1 = ddb.canonical_jsonl(built_1["rows"])
    rows_2 = ddb.canonical_jsonl(built_2["rows"])
    assert rows_1 == rows_2
    summary_1 = ddb.canonical_summary_bytes(built_1["summary"], rows_sha256=hashlib.sha256(rows_1).hexdigest())
    summary_2 = ddb.canonical_summary_bytes(built_2["summary"], rows_sha256=hashlib.sha256(rows_2).hexdigest())
    assert summary_1 == summary_2


def test_row_order_is_canonical_lexicographic() -> None:
    book = _book(
        "book-001",
        "001.md",
        SHA_BOOK1,
        [
            _paragraph(
                SHA_BOOK1,
                0,
                "alpha beta gamma",
                [
                    _span(0, 5, "alpha", "C-B"),
                    _span(6, 10, "beta", "C-A"),
                    _span(11, 16, "gamma", "C-C"),
                ],
            )
        ],
    )
    export = {"schema": "hesperia.dict_d.resolved_corpus.v1", "provenance": _provenance(), "books": [book], "unresolved": []}
    built = ddb.build_dict_d(resolved_export=export, candidate_dict_b=_dict_b({}), evidence_floor=0)
    pairs = [(r["concept_id_a"], r["concept_id_b"]) for r in built["rows"]]
    assert pairs == sorted(pairs)
    assert all(a < b for a, b in pairs)


def test_write_dict_d_refuses_to_overwrite(tmp_path: Path) -> None:
    export = _three_book_export()
    built = ddb.build_dict_d(resolved_export=export, candidate_dict_b=_dict_b({}), evidence_floor=0)
    rows_path = tmp_path / "dict_d.jsonl"
    summary_path = tmp_path / "dict_d.jsonl.meta.json"
    ddb.write_dict_d(built, rows_path=rows_path, summary_path=summary_path)
    assert rows_path.exists()
    assert summary_path.exists()
    with pytest.raises(ddb.DictDBuildError):
        ddb.write_dict_d(built, rows_path=rows_path, summary_path=summary_path)
