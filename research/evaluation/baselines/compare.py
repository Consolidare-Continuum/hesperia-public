# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# See LEGAL_NOTICE.md for full terms.

from __future__ import annotations

from pathlib import Path
from typing import Any

from hesperia.extensions.triz.pipeline import active_graph_from_payload, run_triz_analysis_complete
from research.evaluation.baselines.graph_baseline import run_graph_baseline
from research.evaluation.baselines.keyword_baseline import run_keyword_baseline
from research.evaluation.baselines.tfidf_baseline import run_tfidf_style_baseline


def run_triz_vs_baselines(
    corpus_dir: str | Path,
    *,
    topology_mode: bool = True,
) -> dict[str, Any]:
    """
    Load corpus.txt + graph.json from benchmark folder; run TRIZ + baselines.
    """
    d = Path(corpus_dir)
    text = (d / "corpus.txt").read_text(encoding="utf-8", errors="replace")
    spec = __import__("json").loads((d / "graph.json").read_text(encoding="utf-8"))
    ag = active_graph_from_payload(spec["active_graph"])
    topo = spec.get("topology")
    triz = run_triz_analysis_complete(ag, topo, topology_mode=topology_mode)
    cr = triz.get("reports", {}).get("contradiction_report", {})
    kw = run_keyword_baseline(text)
    gr = run_graph_baseline(text)
    tf = run_tfidf_style_baseline(text)
    triz_tension = float(cr.get("global_tension_index", 0))
    trix_xd = len([c for c in triz.get("contradictions", []) if not c.get("same_area", True)])
    return {
        "delta_summary": {
            "cross_domain_tracked": trix_xd,
            "keyword_proxy": kw["normalized_score"],
            "tension_gap_vs_keyword": round(triz_tension - kw["normalized_score"], 6),
            "triz_sees_typed_conflicts": triz.get("contradictions", []) != [],
        },
        "graph_baseline": gr,
        "keyword_baseline": kw,
        "tfidf_baseline": tf,
        "triz_layer": {
            "contradiction_count": len(triz.get("contradictions", [])),
            "global_tension_index": triz_tension,
            "innovation_clusters": len(triz.get("innovation_clusters", [])),
        },
    }
