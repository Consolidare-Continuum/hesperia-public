# HESPERIA — Testing-params envelope tests (HES-TEST-B03).
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). See LEGAL_NOTICE.md.

from __future__ import annotations

import pytest

from runtime.services.testing_params_emit import (
    attach_testing_params_meta,
    attach_testing_params_to_interpret,
    build_testing_params_block,
    testing_params_enabled,
)


def test_testing_params_flag_defaults_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HESPERIA_TESTING_PARAMS", raising=False)
    assert testing_params_enabled() is False
    payload = {"meta": {}}
    assert "testing_params" not in attach_testing_params_meta(payload)["meta"]
    out = attach_testing_params_to_interpret({"router_envelope": {}})
    assert "testing_params" not in out


def test_testing_params_on_emits_labeled_block(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HESPERIA_TESTING_PARAMS", "1")
    assert testing_params_enabled() is True
    block = build_testing_params_block({"governance": "ok", "meta": {}})
    assert block["calibrated_product_claim"] is False
    assert block["freeze"] is False
    assert block["parameter_count"] > 0
    statuses = {row["status"] for row in block["parameters"]}
    assert "live" in statuses
    assert "uncalibrated" in statuses or "stub" in statuses
    payload = attach_testing_params_meta({"governance": "ok", "meta": {}})
    assert "testing_params" in payload["meta"]
    assert payload["meta"]["testing_params"]["books_areas_inventory"]["freeze"] is False


def test_interpret_attach_adds_retrieval_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HESPERIA_TESTING_PARAMS", "1")
    out = attach_testing_params_to_interpret(
        {"router_envelope": {"engine_trace": {"loopability": 0.1}, "corpus_snapshot_id": "corpus-unset"}}
    )
    assert out["testing_params"]["calibrated_product_claim"] is False
    assert out["router_envelope"]["retrieval_context"]["freeze"] is False
    assert out["router_envelope"]["corpus_snapshot_id"] == "testing-default-pack-mutable"


def test_env_guard_allows_testing_params_flag() -> None:
    from runtime.shipping.env_guard import ALLOWED_HESPERIA_ENV

    assert "HESPERIA_TESTING_PARAMS" in ALLOWED_HESPERIA_ENV
