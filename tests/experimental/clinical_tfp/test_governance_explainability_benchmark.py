# HESPERIA — Ontology registry, explainability, logging, graph store, config, safety, benchmark
"""Tests for ontology governance, activation_trace, session_log, graph_store, benchmark."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def test_ontology_registry() -> None:
    from hesperia.ontology import load_ontology_registry, get_ontology_version, get_dict_versions

    reg = load_ontology_registry()
    assert isinstance(reg, dict)
    v = get_ontology_version()
    assert isinstance(v, str)
    d = get_dict_versions()
    assert "dictA" in d and "dictB" in d


def test_build_activation_trace() -> None:
    from core.engine.explainability import build_activation_trace, trace_to_readable

    markers = [("B_A3_F1_001", 0.5), ("B_A4_F1_001", 0.3)]
    af = {"B_A3_F1_001": ("A3", "F1"), "B_A4_F1_001": ("A4", "F1")}
    trace = build_activation_trace(markers, af)
    assert len(trace) == 2
    assert trace[0]["family_id"] == "A3_F1" and trace[0]["area_id"] == "A3"
    lines = trace_to_readable(trace)
    assert isinstance(lines, list)


def test_session_log() -> None:
    from hesperia.logging.session_log import log_session_record, SessionLogWriter

    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
        path = f.name
    try:
        log_session_record(path, {"session_id": "t1", "raw_text": "Test", "tokens": ["test"]})
        with SessionLogWriter(path) as w:
            w.set("session_id", "t2")
            w.set("activation", {"areas": {"A3": 0.5}})
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()
        assert len(lines) >= 1
    finally:
        Path(path).unlink(missing_ok=True)


def test_graph_store() -> None:
    from hesperia.graph import save_graph_json, load_graph_json, save_graph_graphml, load_graph_graphml

    graph = {"nodes": [{"id": "A3", "weight": 0.5}], "edges": [{"source": "c1", "target": "A3_F1", "weight": 0.5}]}
    with tempfile.TemporaryDirectory() as d:
        jp = Path(d) / "g.json"
        save_graph_json(graph, jp)
        loaded = load_graph_json(jp)
        assert loaded.get("nodes") and loaded.get("edges")
        mp = Path(d) / "g.graphml"
        save_graph_graphml(graph, mp)
        ml = load_graph_graphml(mp)
        assert ml.get("nodes") and ml.get("edges")


def test_benchmark_sessions_yaml() -> None:
    import yaml

    bench = Path(__file__).resolve().parent / "benchmark_sessions.yaml"
    assert bench.exists()
    with open(bench, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    sessions = data.get("sessions") or []
    assert len(sessions) >= 1
    assert "session_id" in sessions[0] and "expected" in sessions[0]


def test_benchmark_run_one() -> None:
    import yaml
    from hesperia.nlp.session_parser import analyze_session_speaker_aware

    bench = Path(__file__).resolve().parent / "benchmark_sessions.yaml"
    with open(bench, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    sessions = data.get("sessions") or []
    if not sessions:
        return
    s = sessions[0]
    text = s.get("text", "")
    act = analyze_session_speaker_aware(text)
    assert "areas" in act and "families" in act
    expected = s.get("expected") or {}
    if expected.get("aggression_level"):
        assert "areas" in act


def test_safety_filter() -> None:
    from research.clinical_tfp.safety_layer import apply_safety_filter, get_minimum_evidence_threshold

    act = {"concepts": {"c1": 0.001}, "families": {"A3_F1": 0.001}, "areas": {"A3": 0.001}}
    out = apply_safety_filter(act, min_evidence=0.01, min_markers=1)
    assert out.get("safety_filter_applied") is True
    assert get_minimum_evidence_threshold() >= 0


def test_config_loader() -> None:
    from hesperia.config import load_clinical_config, get_clinical_config

    cfg = load_clinical_config()
    assert isinstance(cfg, dict)
    c2 = get_clinical_config()
    assert isinstance(c2, dict)
