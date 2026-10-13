from __future__ import annotations

import json
from pathlib import Path

from core.lexical.normalization import normalize_text

REPO = Path(__file__).resolve().parents[2]


def test_normalization_is_deterministic() -> None:
    text = "I’m  SPLIT... identity."
    first = normalize_text(text)
    second = normalize_text(text)
    assert first == second
    assert first["canonical_text"] == "i'm split... identity."


def test_normalization_extracts_tokens_and_spans() -> None:
    payload = normalize_text("Identity diffusion and split defenses")
    assert payload["tokens"] == ["identity", "diffusion", "and", "split", "defenses"]
    assert payload["token_spans"]
    assert payload["phrase_spans"]


def test_normalization_matches_golden_baseline() -> None:
    golden_path = REPO / "assets" / "data" / "engine_dynamics_v060" / "baselines" / "normalization_golden.json"
    cases = json.loads(golden_path.read_text(encoding="utf-8"))
    for case in cases:
        payload = normalize_text(case["input"])
        assert payload["canonical_text"] == case["canonical_text"]
        assert payload["tokens"] == case["tokens"]

