# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

from __future__ import annotations

import os

import pytest


@pytest.fixture
def mock_openai() -> None:
    prev = os.environ.get("HESPERIA_CALIB_MOCK_OPENAI")
    os.environ["HESPERIA_CALIB_MOCK_OPENAI"] = "1"
    yield
    if prev is None:
        os.environ.pop("HESPERIA_CALIB_MOCK_OPENAI", None)
    else:
        os.environ["HESPERIA_CALIB_MOCK_OPENAI"] = prev


def test_chat_json_mock_normalize_echo(mock_openai: None) -> None:
    from tools.dict_calibration.openai_json import chat_json

    user = """Given items.
Input:
[{"text": "  Abc X ", "freq": 1}]

Return JSON: {"items": [...]}"""
    raw = chat_json(system="s", user=user)
    assert raw["items"][0]["source_text"] == "  Abc X "
    assert raw["items"][0]["normalized"] == "abc x"


def test_chat_json_mock_ru_tfp_links_empty(mock_openai: None) -> None:
    from tools.dict_calibration.openai_json import chat_json

    raw = chat_json(
        system="s",
        user='Corpus phrases (verbatim JSON array):\n[]\nReturn JSON: {"links":[]}',
    )
    assert raw == {"links": []}


def test_chat_json_mock_yaml_markers_entries_empty(mock_openai: None) -> None:
    from tools.dict_calibration.openai_json import chat_json

    raw = chat_json(
        system="s",
        user='Return JSON: {"entries": [{"marker": "x", "concept_id": "B_A1_F1_001", "confidence": 0.9}]}\nmarker proposals',
    )
    assert raw == {"entries": []}
