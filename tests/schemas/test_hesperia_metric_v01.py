# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

_REPO = Path(__file__).resolve().parents[2]
_SCHEMA = _REPO / "assets" / "schemas" / "hesperia_metric_v01.json"
_FIXTURE = _REPO / "tests" / "fixtures" / "hesperia_metric_v01_minimal.json"


@pytest.fixture(scope="module")
def validator() -> Draft202012Validator:
    schema = json.loads(_SCHEMA.read_text(encoding="utf-8"))
    return Draft202012Validator(schema)


def test_hesperia_metric_v01_schema_validates_minimal_fixture(validator: Draft202012Validator) -> None:
    payload = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    errors = sorted(validator.iter_errors(payload), key=lambda e: e.path)
    assert not errors, [e.message for e in errors]
