# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

from __future__ import annotations

import json
from pathlib import Path

from tools.dict_calibration.ru_tfp_corpus_align import (
    _load_best_from_dict_a,
    _merge_links,
    _to_dict_a_rows,
    load_zero_link_ids_from_coverage_report,
    write_ru_tfp_cold_artifacts,
)


def test_merge_links_keeps_higher_confidence() -> None:
    best: dict[str, tuple[str, float]] = {}
    _merge_links(best, [{"phrase": "a b", "concept_id": "X", "confidence": 0.5}])
    _merge_links(best, [{"phrase": "a b", "concept_id": "Y", "confidence": 0.9}])
    assert best["a b"] == ("Y", 0.9)


def test_to_dict_a_rows_merges_normalized_form() -> None:
    best = {"Foo Bar": ("C1", 0.8), "foo bar": ("C2", 0.7)}
    rows = _to_dict_a_rows(best, version="test")
    assert len(rows) == 1
    assert set(rows[0]["candidate_concept_ids"]) >= {"C1", "C2"}


def test_load_zero_link_ids_from_coverage_report(tmp_path: Path) -> None:
    p = tmp_path / "cov.json"
    p.write_text(
        json.dumps({"concepts_with_zero_links": ["a1", "b2"]}),
        encoding="utf-8",
    )
    assert load_zero_link_ids_from_coverage_report(p) == ["a1", "b2"]


def test_load_best_from_dict_a(tmp_path: Path) -> None:
    jl = tmp_path / "a.jsonl"
    jl.write_text(
        '{"surface_form":"x y","candidate_concept_ids":["Z"],"priority":8}\n',
        encoding="utf-8",
    )
    b = _load_best_from_dict_a(jl)
    assert b["x y"] == ("Z", 0.8)


def test_write_ru_tfp_cold_artifacts(tmp_path: Path) -> None:
    cov = tmp_path / "cov.json"
    cov.write_text(
        json.dumps({"concepts_with_zero_links": ["c1", "c2"]}),
        encoding="utf-8",
    )
    db = tmp_path / "b.jsonl"
    db.write_text(
        '{"concept_id":"c1","preferred_label":"One"}\n'
        '{"concept_id":"c2","preferred_label":"Two"}\n',
        encoding="utf-8",
    )
    out = tmp_path / "cold_out"
    info = write_ru_tfp_cold_artifacts(cov, out, dict_b_paths=[db])
    assert info["n_cold"] == 2
    assert (out / "cold_concept_ids.txt").read_text(encoding="utf-8").strip() == "c1\nc2"
    data = json.loads((out / "cold_concepts.json").read_text(encoding="utf-8"))
    assert len(data["rows"]) == 2
    assert data["missing_in_dict_b"] == []
    md = (out / "stayed_cold_readable.md").read_text(encoding="utf-8")
    assert "Stayed cold" in md and "`c1`" in md and "One" in md
