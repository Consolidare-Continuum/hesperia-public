from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator


REPO = Path(__file__).resolve().parents[2]
SCHEMA_PATH = REPO / "assets" / "schemas" / "lexical_concept" / "dict_b.schema.json"


def test_dict_b_schema_accepts_minimal_valid_concept() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    payload = {
        "concept_id": "C-1",
        "preferred_label": "identity diffusion",
        "definition": "Persistent instability in self-definition.",
        "family_ids": ["F1"],
        "area_ids": ["A1"],
        "specificity_rank": 5,
        "status": "active",
        "version": "v0.6.0"
    }
    errors = list(validator.iter_errors(payload))
    assert errors == []


def test_dict_b_schema_rejects_invalid_area() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    payload = {
        "concept_id": "C-2",
        "preferred_label": "invalid area",
        "definition": "test",
        "family_ids": ["F1"],
        "area_ids": ["A11"],
        "specificity_rank": 1,
        "status": "active",
        "version": "v0.6.0"
    }
    errors = list(validator.iter_errors(payload))
    assert errors

