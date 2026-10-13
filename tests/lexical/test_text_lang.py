# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

from core.lexical.text_lang import (
    heuristic_document_language,
    match_language,
    retag_language_field_for_phrase,
)


def test_ru_wikipedia_sample():
    t = "Психотерапия — метод лечения больного средствами психического воздействия."
    assert heuristic_document_language(t) == "ru"
    assert match_language(t) == "ru"


def test_en_sample():
    assert heuristic_document_language("already during the session") == "en"


def test_mixed():
    t = "aaaa bbbb cccc " + "абвгдежз " * 6 + "word " * 6
    assert heuristic_document_language(t) == "mixed"


def test_retag_phrase_field():
    assert retag_language_field_for_phrase("одна фраза") == "ru"
    assert retag_language_field_for_phrase("already during") == "en"
    assert retag_language_field_for_phrase("mixed русский latin") == "mixed"
