# HESPERIA — R1–R4 token spans must partition sentences (RU clinical safe).
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

from __future__ import annotations

from core.attribution.attribution_shared import normalize, tokenize, tokenize_with_spans
from core.propagation.r1_r4_segmenters import segment_by_sentences
from runtime.pipeline.r1_r4_pipeline import run_full_pipeline


def test_tokenize_with_spans_matches_tokenize() -> None:
    s = "hello world. justice, order."
    toks, _ = tokenize_with_spans(normalize(s))
    assert toks == tokenize(normalize(s))


def test_punct_fused_word_not_contiguous_substring() -> None:
    """``02.38`` normalizes to token ``0238``; spans must not use find(token)."""
    s = normalize("before. 02.38 after")
    toks, offs = tokenize_with_spans(s)
    assert "0238" in toks
    j = toks.index("0238")
    frag = s[offs[j][0] : offs[j][1]]
    assert frag.replace(".", "") == "0238"


def test_r1_sentence_partition_exhaustive_russian_clinical_snippet() -> None:
    text = normalize(
        "полдня так, полдня так.\n"
        "02.38 **терапевт:** как будто слова и поступок — это одно и то же?"
    )
    toks, offs = tokenize_with_spans(text)
    spans = segment_by_sentences(text)
    total = 0
    for s_start, s_end in spans:
        idxs = [j for j in range(len(toks)) if offs[j][0] < s_end and offs[j][1] > s_start]
        total += len(idxs)
    assert total == len(toks)


def test_run_full_pipeline_russian_session_no_abort() -> None:
    from pathlib import Path

    p = Path(__file__).resolve().parents[1] / "hesperia" / "modules" / "tfp" / "data" / "tfp_v1" / "corpus" / "sessions" / "11-09-2023.md"
    if not p.is_file():
        import pytest

        pytest.skip("session fixture not in tree")
    raw = p.read_text(encoding="utf-8")
    if raw.startswith("---"):
        i = raw.find("\n---\n", 4)
        if i != -1:
            raw = raw[i + 5 :]
    body = raw.strip()
    units, _book = run_full_pipeline(body, book_id="test_ru", levels=["R1", "R2", "R3", "R4"])
    assert len(units) >= 1
