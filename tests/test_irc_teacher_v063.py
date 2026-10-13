"""H063 gold tests — envelope + teacher response v063 (Hesperia product repo)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from runtime.irc_teacher.engine_run_envelope import (
    build_engine_run_envelope,
    build_teacher_request_from_envelope,
)
from runtime.irc_teacher.teacher_v063 import (
    compute_reweight_preview,
    validate_teacher_response_v063,
)

SCHEMAS = Path(__file__).resolve().parents[1] / "assets" / "schemas"


class _FakeHybrid:
    engine_result = {
        "propagation_trace": [{"concept": "FAILURE", "hop": 0}],
        "invariant_activation": {"concepts": {"SHAME": {"observed": 0.3, "expected": 0.8}}},
        "gtp_coherence": {"path_ids": ["p1"]},
    }
    interior_pov = {}
    gtp_coherence = {"path_ids": ["p1"]}
    context_package = {"ksi": {"incidents": [], "missing_bridges": [], "phi_trace": {}}}


def test_envelope_schema_shape():
    env = build_engine_run_envelope(
        text_ru="Научное утверждение TFP.",
        correlation_id="cid-test",
        hybrid_output=_FakeHybrid(),
    )
    assert env["schema"] == "hesperia.engine_run_envelope.v063"
    assert env["lang"] == "ru"
    assert "roads" in env["engine"]
    req = build_teacher_request_from_envelope(env)
    assert "incidents" in req


def test_teacher_response_rejects_justification():
    bad = {
        "schema": "hesperia.teacher_response.v063",
        "lang": "ru",
        "proposals": [{"action": "update_edge_weight", "confidence": 0.9, "justification": "no"}],
    }
    with pytest.raises(ValueError, match="forbidden"):
        validate_teacher_response_v063(bad)


def test_teacher_response_gold():
    good = {
        "schema": "hesperia.teacher_response.v063",
        "lang": "ru",
        "proposals": [
            {
                "action": "update_edge_weight",
                "source": "A",
                "target": "B",
                "W_e_current": 0.1,
                "W_e_proposed": 0.7,
                "confidence": 0.85,
            }
        ],
    }
    validate_teacher_response_v063(good)
    preview = compute_reweight_preview(good["proposals"])
    assert preview[0]["applied"] == 0


def test_schema_files_exist():
    assert (SCHEMAS / "engine_run_envelope_v063.json").is_file()
    assert (SCHEMAS / "teacher_response_v063.json").is_file()
    data = json.loads((SCHEMAS / "teacher_response_v063.json").read_text(encoding="utf-8"))
    props = data["properties"]["proposals"]["items"]["properties"]
    assert "justification" not in props
