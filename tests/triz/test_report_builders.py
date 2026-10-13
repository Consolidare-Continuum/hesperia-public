# Product report builders

from __future__ import annotations

import json
from pathlib import Path

from hesperia.extensions.triz.pipeline import active_graph_from_payload, run_triz_analysis_complete
from hesperia.extensions.triz.report_builders import build_all_reports, build_contradiction_report


def test_build_contradiction_report_shape() -> None:
    ctx = {
        "contradictions": [
            {"concept_a": "a", "concept_b": "b", "score": 0.4, "triz_class": "x", "area_a": 0, "area_b": 1}
        ],
        "family_hotspots": [],
        "persistent_contradictions": [],
    }
    r = build_contradiction_report(ctx)
    assert "global_tension_index" in r
    assert "triz_classes" in r


def test_build_all_from_polarized_fixture() -> None:
    fix = Path(__file__).resolve().parent / "fixtures" / "polarized.json"
    d = json.loads(fix.read_text(encoding="utf-8"))
    ag = active_graph_from_payload(d["active_graph"])
    full = run_triz_analysis_complete(ag, d["topology"], run_id="rb_polarized")
    rep = build_all_reports(
        {
            "contradictions": full["contradictions"],
            "family_hotspots": full["topology"]["family_hotspots"],
            "innovation_clusters": full["innovation_clusters"],
            "narratives": full["narratives"],
            "narrative_monitor": {"blocked_areas": [], "dominant_routes": [], "spillover_targets": []},
            "persistent_contradictions": [],
            "propagation_topology": {},
        }
    )
    assert "meta_synthesis" in rep
    assert "meta_area_11_equivalent" in rep["meta_synthesis"]
