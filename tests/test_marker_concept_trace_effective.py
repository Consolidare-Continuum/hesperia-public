# HESPERIA — RAD. marker_concept_trace.effective_landing_source under concept guard.
from __future__ import annotations

from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]


def test_trace_b0_fallback_annotation_under_strict(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HESPERIA_CONCEPT_EVIDENCE_GUARD", "strict")

    def _stub_dict_a(assets_root=None):
        return {"tok": {"familyGlobal": 5, "altitude": 0.2}}

    def _stub_dict_b():
        return {"tok": 7}

    monkeypatch.setattr("core.attribution.structural.load_dict_a", _stub_dict_a)
    monkeypatch.setattr("core.attribution.structural.load_dict_b", _stub_dict_b)

    from hesperia.extensions.dynamics.e2e_bridge import markers_to_concept_activation

    act = markers_to_concept_activation("tok", REPO / "assets" / "lexicon" / "curated")
    trace = act.get("marker_concept_trace") or []
    assert trace, "expected one trace row for stubbed tok"
    row = trace[0]
    assert row["landing_source"] == "A"
    assert row["effective_landing_source"] == "B0_fallback"
    assert row["concept_index"] == 7
    monkeypatch.delenv("HESPERIA_CONCEPT_EVIDENCE_GUARD", raising=False)


def test_trace_no_effective_key_when_guard_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HESPERIA_CONCEPT_EVIDENCE_GUARD", raising=False)

    def _stub_dict_a(assets_root=None):
        return {"tok2": {"familyGlobal": 11, "altitude": 0.3}}

    def _stub_dict_b():
        return {}

    monkeypatch.setattr("core.attribution.structural.load_dict_a", _stub_dict_a)
    monkeypatch.setattr("core.attribution.structural.load_dict_b", _stub_dict_b)

    from hesperia.extensions.dynamics.e2e_bridge import markers_to_concept_activation

    act = markers_to_concept_activation("tok2", REPO / "assets" / "lexicon" / "curated")
    trace = act.get("marker_concept_trace") or []
    assert trace
    assert "effective_landing_source" not in trace[0]
