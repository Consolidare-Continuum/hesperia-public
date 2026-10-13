from __future__ import annotations

import json
from pathlib import Path

from runtime.pipeline import run_tfp_file_pipeline as mod


def _write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def test_load_contradictions_uses_canonical_12_source(tmp_path: Path) -> None:
    sid = "s1"
    _write_json(
        tmp_path / "08_triz_complete.json",
        {
            "sessions": [
                {
                    "session_id": sid,
                    "triz_complete": {
                        "triz_complete": {
                            "contradictions": [
                                {"pair": ["c2", "c1"], "raw_contradiction_score": 0.4},
                                {"pair": ["c1", "c3"], "raw_contradiction_score": 0.6},
                            ]
                        }
                    },
                }
            ]
        },
    )
    _write_json(
        tmp_path / "12_s1_contradictions.json",
        [{"pair": ["x1", "x2"], "raw_contradiction_score": 0.9}],
    )
    rows, source = mod._load_contradictions(tmp_path, sid)
    assert source == "12_topology_derived_contradictions"
    assert len(rows) == 1
    assert [tuple(r["pair"]) for r in rows] == [("x1", "x2")]


def test_activation_receives_contradictions(monkeypatch, tmp_path: Path) -> None:
    sid = "s2"
    _write_json(
        tmp_path / "12_s2_contradictions.json",
        {
            "contradictions": [
                {"pair": ["x", "y"], "raw_contradiction_score": 0.7},
            ]
        },
    )
    captured: dict[str, object] = {}

    def fake_analyze_session(text: str, **kwargs):
        captured["text"] = text
        captured["contradictions"] = kwargs.get("contradictions")
        return {"contradiction_count_used": 1, "contradiction_coupling_active": True, "areas_final": {"A1": 1.0}}

    monkeypatch.setattr("hesperia.nlp.session_parser.analyze_session", fake_analyze_session)
    row, trace = mod._build_activation_with_bundle_contradictions(
        session_id=sid,
        text="hello",
        bundle_dir=tmp_path,
        embedding=None,
    )
    assert isinstance(captured["contradictions"], list)
    assert len(captured["contradictions"]) == 1
    assert trace["used_in_activation"] is True
    assert row["contradiction_pipeline"]["count"] == 1


def test_activation_differs_with_and_without_contradictions(monkeypatch, tmp_path: Path) -> None:
    sid = "s3"
    with_dir = tmp_path / "with"
    without_dir = tmp_path / "without"
    _write_json(
        with_dir / "12_s3_contradictions.json",
        [{"pair": ["a", "b"], "raw_contradiction_score": 0.8}],
    )

    def fake_analyze_session(_text: str, **kwargs):
        contradictions = kwargs.get("contradictions")
        if contradictions:
            return {
                "contradiction_count_used": 1,
                "contradiction_coupling_active": True,
                "areas_final": {"A1": 0.3, "A2": 0.7},
                "contradiction_pressure": {"A1": 1.0},
            }
        return {
            "contradiction_count_used": 0,
            "contradiction_coupling_active": False,
            "areas_final": {"A1": 0.8, "A2": 0.2},
            "contradiction_pressure": {"A1": 0.0},
        }

    monkeypatch.setattr("hesperia.nlp.session_parser.analyze_session", fake_analyze_session)

    row_with, trace_with = mod._build_activation_with_bundle_contradictions(
        session_id=sid,
        text="text",
        bundle_dir=with_dir,
        embedding=None,
    )
    row_without, trace_without = mod._build_activation_with_bundle_contradictions(
        session_id=sid,
        text="text",
        bundle_dir=without_dir,
        embedding=None,
    )

    assert trace_with["count"] == 1
    assert trace_without["count"] == 0
    assert row_with["activation"]["areas_final"] != row_without["activation"]["areas_final"]
    assert row_with["activation"]["contradiction_coupling_active"] is True
    assert row_without["activation"]["contradiction_coupling_active"] is False
