# HESPERIA — Text normalization, negation, n-gram markers, segmentation
"""Tests for text_normalization, negation, ngram_markers, session_segmentation."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def test_remove_fillers() -> None:
    from hesperia.nlp.text_normalization import remove_fillers

    t = "ну типа я... эээ... меня это бесит"
    out = remove_fillers(t)
    assert "ну" not in out or "типа" not in out
    assert "бесит" in out


def test_normalize_transcript_text() -> None:
    from hesperia.nlp.text_normalization import normalize_transcript_text

    t = "ну   типа   я   эээ   меня  это  бесит  .  .  ."
    out = normalize_transcript_text(t)
    assert len(out) >= 1
    assert "бесит" in out


def test_find_negation_scopes() -> None:
    from hesperia.nlp.negation import find_negation_scopes

    scopes = find_negation_scopes("я не злюсь")
    assert isinstance(scopes, list)
    assert len(scopes) >= 1


def test_get_negated_token_indices() -> None:
    from hesperia.nlp.negation import get_negated_token_indices

    text = "я не злюсь на вас"
    tokens = ["я", "не", "злюсь", "на", "вас"]
    neg = get_negated_token_indices(text, tokens)
    assert isinstance(neg, set)


def test_build_ngram_marker_index() -> None:
    from hesperia.nlp.ngram_markers import build_ngram_marker_index, detect_ngram_markers

    idx = build_ngram_marker_index(min_n=2, max_n=3)
    assert isinstance(idx, dict)
    markers = detect_ngram_markers(["вы", "специально", "это"], index=idx)
    assert isinstance(markers, list)


def test_segment_session_by_utterances() -> None:
    from hesperia.nlp.session_segmentation import segment_session_by_utterances

    text = "Patient: A.\nTherapist: B.\nPatient: C.\nTherapist: D.\nPatient: E."
    segs = segment_session_by_utterances(text, window_utterances=2)
    assert isinstance(segs, list)
    assert len(segs) >= 1
    assert "text" in segs[0] and "utterances" in segs[0]
