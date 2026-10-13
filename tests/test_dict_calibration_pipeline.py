# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.dict_calibration.anchor_bind import anchor_drafts, load_anchor_registry
from tools.dict_calibration.build_links import build_links, links_to_engine_dict_a
from tools.dict_calibration.extract_lexical import extract_corpus
from tools.dict_calibration.jsonl_util import read_jsonl, write_jsonl


def test_extract_corpus_min_freq(tmp_path: Path) -> None:
    d = tmp_path / "corpus"
    d.mkdir()
    (d / "a.md").write_text(
        "identity diffusion and splitting\n\nidentity diffusion and splitting\n",
        encoding="utf-8",
    )
    rows = extract_corpus(d, min_freq=1)
    texts = {r["text"] for r in rows if r["pattern_type"] == "ngram"}
    assert "identity diffusion" in texts or "identity diffusion and splitting" in texts


def test_anchor_and_links_roundtrip(tmp_path: Path, repo_root: Path) -> None:
    base = repo_root / "assets/data/engine_dynamics_v060"
    seed_b = base / "dict_b/dict_b_seed.jsonl"
    anch = base / "anchors/concept_hex_anchors.json"
    reg = load_anchor_registry(anch)
    rows = [json.loads(line) for line in seed_b.read_text(encoding="utf-8").splitlines() if line.strip()]
    concept_index = {r["concept_id"]: r for r in rows}
    drafts = [
        {
            "concept_id": "novel.unused.id",
            "labels": ["abandonment panic"],
            "from_lexical": ["abandonment panic"],
            "confidence": 0.9,
        }
    ]
    anchored, rejected = anchor_drafts(drafts, concept_index, reg, min_score=0.5)
    assert len(anchored) == 1
    assert anchored[0]["concept_id"] == "C-1004"
    assert len(rejected) == 0

    norm = [
        {
            "text": "abandonment panic",
            "normalized": "abandonment panic",
            "variants": [],
            "pattern_type": "ngram",
            "freq": 3,
            "source_doc": "x",
        }
    ]
    links = build_links(norm, anchored)
    assert any(ln["concept_id"] == "C-1004" for ln in links)
    eng = links_to_engine_dict_a(links)
    assert eng[0]["normalized_form"] == "abandonment panic"
    assert eng[0]["candidate_concept_ids"] == ["C-1004"]


@pytest.fixture()
def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_links_written_jsonl(tmp_path: Path, repo_root: Path) -> None:
    w = tmp_path / "w"
    w.mkdir()
    write_jsonl(
        w / "n.jsonl",
        [
            {
                "normalized": "splitting",
                "text": "splitting",
                "variants": [],
                "pattern_type": "ngram",
                "freq": 1,
                "source_doc": "",
            }
        ],
    )
    base = repo_root / "assets/data/engine_dynamics_v060"
    rows = [
        json.loads(line)
        for line in (base / "dict_b/dict_b_seed.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    reg = load_anchor_registry(base / "anchors/concept_hex_anchors.json")
    concept_index = {r["concept_id"]: r for r in rows}
    drafts = [{"concept_id": "x", "labels": ["splitting"], "from_lexical": ["splitting"], "confidence": 1.0}]
    anchored, _ = anchor_drafts(drafts, concept_index, reg, min_score=0.45)

    norm = read_jsonl(w / "n.jsonl")
    links = build_links(norm, anchored)
    assert links
