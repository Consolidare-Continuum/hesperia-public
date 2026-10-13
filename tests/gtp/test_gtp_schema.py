# GTP-02 — gtp_v0_1 JSON Schema validates fixture and live pipeline output.

from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from sphere.topology.gtp.neighbors import HexCell
from sphere.topology.gtp.pipeline import gtp_step_to_dict, run_gtp_step

_SCHEMA_PATH = (
    Path(__file__).resolve().parents[2] / "assets" / "schemas" / "gtp" / "gtp_v0_1.schema.json"
)
_FIXTURE_PATH = (
    Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "gtp" / "gtp_v0_1_fixture.json"
)


def _load_schema() -> dict:
    return json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))


def test_fixture_validates_against_schema() -> None:
    schema = _load_schema()
    fixture = json.loads(_FIXTURE_PATH.read_text(encoding="utf-8"))
    payload = {k: v for k, v in fixture.items() if not k.startswith("_")}
    Draft202012Validator(schema).validate(payload)


def test_fixture_reproduces_live_pipeline_output() -> None:
    fixture = json.loads(_FIXTURE_PATH.read_text(encoding="utf-8"))
    fixture_input = fixture["_fixture_input"]
    h = HexCell(**fixture_input["current_hex"])
    result = run_gtp_step(
        fixture_input["text"], h, powv_position=tuple(fixture_input["powv_position"])
    )
    actual = gtp_step_to_dict(result)
    expected = {k: v for k, v in fixture.items() if not k.startswith("_")}
    assert actual == expected


def test_live_pipeline_output_validates_against_schema() -> None:
    schema = _load_schema()
    h = HexCell(area_id=2, global_id=50, hex_index=100)
    result = run_gtp_step("this covers and implies broad coverage", h)
    Draft202012Validator(schema).validate(gtp_step_to_dict(result))
