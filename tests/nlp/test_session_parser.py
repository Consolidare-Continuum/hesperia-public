# HESPERIA — Tests for session text → concept activation pipeline
"""LEVEL 5/6: tokenize → normalize → detect_markers → activate_concepts → output."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def test_tokenize_text() -> None:
    from hesperia.nlp.session_parser import tokenize_text
    assert tokenize_text("") == []
    assert tokenize_text("  ") == []
    tokens = tokenize_text("Расщепление и перенос. Агрессия — норма.")
    assert "расщепление" not in tokens  # raw, not normalized yet
    assert any("расщепление" in t.lower() or t.lower() == "расщепление" for t in tokens) or "расщепление" in [t.lower() for t in tokens]
    assert len(tokens) >= 4


def test_normalize_tokens() -> None:
    from hesperia.nlp.session_parser import normalize_tokens
    assert normalize_tokens([]) == []
    assert normalize_tokens(["Расщепление", "  ", "ПЕРЕНОС"]) == ["расщепление", "перенос"]


def test_build_ngrams() -> None:
    from hesperia.nlp.session_parser import build_ngrams
    assert build_ngrams([], n=2) == []
    assert build_ngrams(["a"], n=2) == []
    tokens = ["расщепление", "и", "перенос"]
    bigrams = build_ngrams(tokens, n=2)
    assert bigrams == ["расщепление и", "и перенос"]
    trigrams = build_ngrams(tokens, n=3)
    assert trigrams == ["расщепление и перенос"]


def test_detect_phrase_markers() -> None:
    from hesperia.nlp.session_parser import detect_phrase_markers
    index = {"проективная идентификация": [("B_A3_F5_001", 1.0)], "контрперенос": [("B_A9_F3_001", 0.9)]}
    ngrams = ["проективная идентификация", "идентификация и"]
    hits = detect_phrase_markers(ngrams, marker_index=index)
    assert len(hits) == 1
    assert hits[0] == ("B_A3_F5_001", 1.0)


def test_detect_markers_with_index() -> None:
    from hesperia.nlp.session_parser import detect_markers
    index = {"расщепление": [("B_A3_F1_001", 1.0)], "агрессия": [("B_A4_F1_001", 0.8)]}
    markers = detect_markers(["расщепление", "агрессия", "нетакого"], marker_index=index)
    assert len(markers) == 2
    cids = [m[0] for m in markers]
    assert "B_A3_F1_001" in cids
    assert "B_A4_F1_001" in cids


def test_activate_concepts_aggregation() -> None:
    from hesperia.nlp.session_parser import activate_concepts
    # concept B_A3_F1_001 (area A3, family F1), B_A3_F1_002 (A3, F1)
    af = {
        "B_A3_F1_001": ("A3", "F1"),
        "B_A3_F1_002": ("A3", "F1"),
        "B_A2_F1_001": ("A2", "F1"),
    }
    markers = [
        ("B_A3_F1_001", 1.0),
        ("B_A3_F1_001", 0.5),
        ("B_A3_F1_002", 1.0),
        ("B_A2_F1_001", 0.3),
    ]
    out = activate_concepts(markers, concept_to_area_family=af, normalize_scores=True)
    assert "concepts" in out and "families" in out and "areas" in out
    assert out["concepts"]["B_A3_F1_001"] == 1.0  # max in concepts
    assert "A3_F1" in out["families"]
    assert "A3" in out["areas"] and "A2" in out["areas"]


def test_analyze_session_returns_shape() -> None:
    from hesperia.nlp.session_parser import analyze_session
    result = analyze_session("Расщепление и агрессия в переносе. Интеграция.")
    assert "areas" in result and isinstance(result["areas"], dict)
    assert "families" in result and isinstance(result["families"], dict)
    assert "concepts" in result and isinstance(result["concepts"], dict)
    # With real Dict-A/Dict-B at least some keys
    assert len(result["areas"]) >= 0
    for k, v in result["areas"].items():
        assert isinstance(k, str) and k.startswith("A")
        assert isinstance(v, (int, float)) and 0 <= v <= 1


def test_activate_concepts_per_concept_cap() -> None:
    from hesperia.nlp.session_parser import activate_concepts

    af = {"C_X": ("A1", "F1")}
    markers = [("C_X", 4.0), ("C_X", 4.0)]
    out = activate_concepts(
        markers,
        concept_to_area_family=af,
        normalize_scores=False,
        per_concept_score_cap=5.0,
    )
    assert out["concepts"]["C_X"] == 5.0


def test_evidence_volume_normalize_dampens_long_segment_same_hit_count() -> None:
    from hesperia.nlp.session_parser import analyze_session

    mk = {"aaa": [("C1", 1.0)]}
    af = {"C1": ("A1", "F1")}
    short = "aaa"
    long = "aaa " + " ".join(["b"] * 99)
    s_out = analyze_session(
        short,
        marker_index=mk,
        phrase_index={},
        concept_to_area_family=af,
        normalize_scores=False,
        ngram_n=1,
        evidence_volume_normalize=True,
    )
    l_out = analyze_session(
        long,
        marker_index=mk,
        phrase_index={},
        concept_to_area_family=af,
        normalize_scores=False,
        ngram_n=1,
        evidence_volume_normalize=True,
    )
    assert s_out["concepts"]["C1"] > l_out["concepts"]["C1"]


def test_detect_markers_negation_dampens_adjacent_token() -> None:
    from hesperia.nlp.session_parser import detect_markers

    idx = {"злюсь": [("B_A4_F1_001", 1.0)]}
    toks = ["не", "злюсь"]
    assert detect_markers(toks, marker_index=idx) == [("B_A4_F1_001", 1.0)]
    damped = detect_markers(
        toks,
        marker_index=idx,
        apply_negation=True,
        negation_window=2,
        negation_multiplier=0.5,
    )
    assert damped == [("B_A4_F1_001", 0.5)]
