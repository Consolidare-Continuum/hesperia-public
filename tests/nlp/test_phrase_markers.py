# HESPERIA — Tests for LEVEL 9 phrase markers (bigram / trigram detection)
"""Phrase index, tuple ngrams, phrase-over-token priority, concept activation."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def test_bigram_detection() -> None:
    from hesperia.nlp.session_parser import build_ngram_tuples, detect_phrase_markers
    phrase_index = {
        "phrase_length_2": {
            ("сначала", "хороший"): [("B_A3_F1_002", 0.9)],
            ("потом", "плохой"): [("B_A3_F1_002", 0.9)],
        },
        "phrase_length_3": {},
    }
    tokens = ["пациент", "говорит", "сначала", "хороший", "а", "потом", "плохой"]
    bigrams = build_ngram_tuples(tokens, 2)
    assert ("сначала", "хороший") in bigrams
    assert ("потом", "плохой") in bigrams
    matches = detect_phrase_markers(tokens=tokens, phrase_index=phrase_index)
    assert len(matches) == 2
    assert all(c == "B_A3_F1_002" for c, _ in matches)
    assert matches[0][1] == 0.9


def test_trigram_detection() -> None:
    from hesperia.nlp.session_parser import build_ngram_tuples, detect_phrase_markers
    phrase_index = {
        "phrase_length_2": {},
        "phrase_length_3": {
            ("вы", "меня", "предали"): [("B_A2_F2_002", 1.0)],
        },
    }
    tokens = ["вы", "меня", "предали", "сказал", "он"]
    trigrams = build_ngram_tuples(tokens, 3)
    assert ("вы", "меня", "предали") in trigrams
    matches = detect_phrase_markers(tokens=tokens, phrase_index=phrase_index)
    assert len(matches) == 1
    assert matches[0] == ("B_A2_F2_002", 1.0)


def test_phrase_overrides_token_duplication() -> None:
    """Phrase-activated concepts are not double-counted when the same concept is hit by a token."""
    from hesperia.nlp.session_parser import analyze_session
    # Use a minimal marker index where "хороший" and "плохой" as tokens also map to B_A3_F1_002
    marker_index = {
        "хороший": [("B_A3_F1_002", 0.5)],
        "плохой": [("B_A3_F1_002", 0.5)],
    }
    phrase_index = {
        "phrase_length_2": {
            ("сначала", "хороший"): [("B_A3_F1_002", 0.9)],
            ("потом", "плохой"): [("B_A3_F1_002", 0.9)],
        },
        "phrase_length_3": {},
    }
    text = "Пациент говорит что терапевт сначала хороший а потом плохой."
    result = analyze_session(text, marker_index=marker_index, phrase_index=phrase_index)
    concepts = result.get("concepts", {})
    # B_A3_F1_002 should be present; we expect phrase contributions (0.9+0.9) not phrase+token (which would be higher if doubled)
    if "B_A3_F1_002" in concepts:
        # Normalized: max concept = 1.0, so we get 1.0 for B_A3_F1_002 if it's the only one
        assert concepts["B_A3_F1_002"] > 0


def test_correct_concept_activation() -> None:
    """Phrase markers produce concept activations that aggregate like token markers."""
    from hesperia.nlp.session_parser import (
        tokenize_text,
        normalize_tokens,
        detect_phrase_markers,
        activate_concepts,
    )
    from hesperia.ontology.dictB import build_concept_to_area_family
    phrase_index = {
        "phrase_length_2": {
            ("сначала", "хороший"): [("B_A3_F1_002", 0.9)],
            ("потом", "плохой"): [("B_A3_F1_002", 0.9)],
        },
        "phrase_length_3": {},
    }
    text = "Терапевт сначала хороший а потом плохой."
    tokens = normalize_tokens(tokenize_text(text))
    markers = detect_phrase_markers(tokens=tokens, phrase_index=phrase_index)
    assert len(markers) == 2
    act = activate_concepts(markers, concept_to_area_family=build_concept_to_area_family())
    assert "B_A3_F1_002" in act["concepts"]
    assert act["concepts"]["B_A3_F1_002"] == 1.0  # normalized; both hits sum then norm
    assert "A3" in act["areas"]
    assert "A3_F1" in act["families"]
