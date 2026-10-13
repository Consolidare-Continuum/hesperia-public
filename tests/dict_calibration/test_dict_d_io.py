# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""CORE-D2 W6 — Dict D schema/integrity hardening tests."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from tools.dict_calibration import dict_d_io


def _row(**overrides) -> dict:
    base = {
        "concept_id_a": "C-A",
        "concept_id_b": "C-B",
        "cooc_count": 5,
        "npmi": 0.5,
        "g2": 12.3,
        "agreement_with_b": "novel",
        "source_books": ["book-001"],
    }
    base.update(overrides)
    return base


def test_valid_row_has_no_violations() -> None:
    assert dict_d_io.validate_dict_d_row(_row()) == []


def test_undeclared_field_rejected() -> None:
    row = _row(version="v0_core_syzif_001_d_mock")
    errs = dict_d_io.validate_dict_d_row(row)
    assert any("undeclared_fields" in e for e in errs)


def test_contradicts_no_longer_a_valid_runtime_label() -> None:
    row = _row(agreement_with_b="contradicts")
    errs = dict_d_io.validate_dict_d_row(row)
    assert "bad_agreement_with_b" in errs


def test_missing_source_books_rejected() -> None:
    row = _row()
    del row["source_books"]
    errs = dict_d_io.validate_dict_d_row(row)
    assert any(e.startswith("missing:source_books") for e in errs)


def test_empty_source_books_rejected() -> None:
    errs = dict_d_io.validate_dict_d_row(_row(source_books=[]))
    assert "source_books_invalid" in errs


def test_duplicate_source_books_rejected() -> None:
    errs = dict_d_io.validate_dict_d_row(_row(source_books=["book-001", "book-001"]))
    assert "source_books_invalid" in errs


def test_negative_g2_rejected() -> None:
    errs = dict_d_io.validate_dict_d_row(_row(g2=-0.1))
    assert "g2_negative" in errs


def test_non_finite_npmi_rejected() -> None:
    errs = dict_d_io.validate_dict_d_row(_row(npmi=float("nan")))
    assert "npmi_not_finite" in errs


def test_cooc_count_must_be_int_not_float() -> None:
    errs = dict_d_io.validate_dict_d_row(_row(cooc_count=5.0))
    assert "cooc_count_invalid" in errs


def test_self_pair_rejected() -> None:
    errs = dict_d_io.validate_dict_d_row(_row(concept_id_a="C-A", concept_id_b="C-A"))
    assert "concept_id_a_equals_concept_id_b" in errs


def test_non_canonical_order_rejected() -> None:
    errs = dict_d_io.validate_dict_d_row(_row(concept_id_a="C-B", concept_id_b="C-A"))
    assert "pair_not_canonically_sorted" in errs


def test_unknown_concept_ids_rejected_against_candidate_dict_b() -> None:
    known = frozenset({"C-A"})
    errs = dict_d_io.validate_dict_d_row(_row(), known_concept_ids=known)
    assert "concept_id_b_unknown" in errs


def test_known_concept_ids_pass_when_both_present() -> None:
    known = frozenset({"C-A", "C-B"})
    assert dict_d_io.validate_dict_d_row(_row(), known_concept_ids=known) == []


def test_agrees_without_authored_relation_rejected() -> None:
    relations = {"C-A": frozenset(), "C-B": frozenset()}
    errs = dict_d_io.validate_dict_d_row(_row(agreement_with_b="agrees"), known_relations=relations)
    assert "agreement_agrees_without_authored_relation" in errs


def test_novel_with_authored_relation_rejected() -> None:
    relations = {"C-A": frozenset({"C-B"}), "C-B": frozenset({"C-A"})}
    errs = dict_d_io.validate_dict_d_row(_row(agreement_with_b="novel"), known_relations=relations)
    assert "agreement_novel_with_authored_relation" in errs


def test_agrees_with_authored_relation_passes() -> None:
    relations = {"C-A": frozenset({"C-B"}), "C-B": frozenset({"C-A"})}
    errs = dict_d_io.validate_dict_d_row(_row(agreement_with_b="agrees"), known_relations=relations)
    assert errs == []


def test_load_jsonl_rejects_duplicate_unordered_pair(tmp_path: Path) -> None:
    path = tmp_path / "dict_d.jsonl"
    path.write_text(json.dumps(_row()) + "\n" + json.dumps(_row(cooc_count=9)) + "\n", encoding="utf-8")
    with pytest.raises(dict_d_io.DictDValidationError, match="duplicate unordered pair"):
        dict_d_io.load_dict_d_jsonl(path)


def test_load_jsonl_rejects_malformed_json(tmp_path: Path) -> None:
    path = tmp_path / "dict_d.jsonl"
    path.write_text("{not json\n", encoding="utf-8")
    with pytest.raises(dict_d_io.DictDValidationError, match="malformed JSON"):
        dict_d_io.load_dict_d_jsonl(path)


def test_load_jsonl_rejects_symlink(tmp_path: Path) -> None:
    real = tmp_path / "real.jsonl"
    real.write_text(json.dumps(_row()) + "\n", encoding="utf-8")
    link = tmp_path / "link.jsonl"
    os.symlink(real, link)
    with pytest.raises(dict_d_io.DictDValidationError, match="symlink"):
        dict_d_io.load_dict_d_jsonl(link)


def test_load_jsonl_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(dict_d_io.DictDValidationError, match="not a regular file"):
        dict_d_io.load_dict_d_jsonl(tmp_path / "nope.jsonl")


def test_load_jsonl_accepts_valid_rows(tmp_path: Path) -> None:
    path = tmp_path / "dict_d.jsonl"
    path.write_text(
        json.dumps(_row()) + "\n" + json.dumps(_row(concept_id_a="C-C", concept_id_b="C-D")) + "\n",
        encoding="utf-8",
    )
    rows = dict_d_io.load_dict_d_jsonl(path)
    assert len(rows) == 2


def test_load_jsonl_propagates_known_concept_ids_check(tmp_path: Path) -> None:
    path = tmp_path / "dict_d.jsonl"
    path.write_text(json.dumps(_row()) + "\n", encoding="utf-8")
    with pytest.raises(dict_d_io.DictDValidationError, match="concept_id_b_unknown"):
        dict_d_io.load_dict_d_jsonl(path, known_concept_ids=frozenset({"C-A"}))


def test_builder_output_round_trips_through_strict_loader(tmp_path: Path) -> None:
    """Integration: dict_d_builder's own output must satisfy W6's strict loader."""
    from tools.dict_calibration import dict_d_builder as ddb
    from tools.dict_calibration.resolved_export import _paragraph_identity

    sha = "a" * 64
    text = "alpha beta"
    paragraph = {
        "paragraph_id": _paragraph_identity(sha, 0, text),
        "source_ordinal": 0,
        "text": text,
        "resolved_spans": [
            {
                "span_position": 0,
                "span_end": 5,
                "surface": "alpha",
                "winning_concept_id": "C-A",
                "candidate_scores": [{"concept_id": "C-A", "score": 1.0}],
            },
            {
                "span_position": 6,
                "span_end": 10,
                "surface": "beta",
                "winning_concept_id": "C-B",
                "candidate_scores": [{"concept_id": "C-B", "score": 1.0}],
            },
        ],
    }
    export = {
        "schema": "hesperia.dict_d.resolved_corpus.v1",
        "provenance": {
            "candidate_bundle_id": "b" * 64,
            "candidate_manifest_sha256": "c" * 64,
            "corpus_snapshot_sha256": "d" * 64,
            "resolver_version": "lexical-concept-resolver-v1",
            "resolver_implementation_sha256": "b" * 64,
            "resolver_authority": "canonical-run-dlcr-pipeline",
            "resolver_configuration_sha256": "0" * 64,
            "segmentation_rule": "frozen-paragraph-segmentation-v1",
            "export_rule": "resolved-corpus-export-v1",
            "dict_d_enabled": False,
            "dict_d_effective_weight": 0.0,
        },
        "books": [{"book_id": "book-001", "source_path": "001.md", "source_sha256": sha, "paragraphs": [paragraph]}],
        "unresolved": [],
    }
    dict_b = [{"concept_id": "C-A", "related_concept_ids": []}, {"concept_id": "C-B", "related_concept_ids": []}]
    built = ddb.build_dict_d(resolved_export=export, candidate_dict_b=dict_b, evidence_floor=0)
    rows_path = tmp_path / "dict_d.jsonl"
    summary_path = tmp_path / "dict_d.jsonl.meta.json"
    ddb.write_dict_d(built, rows_path=rows_path, summary_path=summary_path)

    loaded = dict_d_io.load_dict_d_jsonl(
        rows_path,
        known_concept_ids=frozenset({"C-A", "C-B"}),
        known_relations={"C-A": frozenset(), "C-B": frozenset()},
    )
    assert loaded == built["rows"]
