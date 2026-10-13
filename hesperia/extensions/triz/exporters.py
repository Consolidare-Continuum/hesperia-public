# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# See LEGAL_NOTICE.md for full terms.

"""Product exports: policy contradiction JSON, innovation radar, narrative monitor."""

from __future__ import annotations

import csv
import io
import json
from typing import Any

from hesperia.extensions.triz.models import TRIZReport
from hesperia.extensions.triz.pipeline import triz_report_to_dict


def export_policy_report(report: TRIZReport, *, indent: int | None = 2) -> str:
    """JSON string — Policy Contradiction Detector output."""
    body = {
        "product": "policy_contradiction_detector",
        "contradictions": triz_report_to_dict(report)["contradictions"],
    }
    return json.dumps(body, sort_keys=True, indent=indent)


def export_innovation_radar(report: TRIZReport) -> dict[str, Any]:
    """
    Innovation Radar: CSV slice + dashboard metrics.
    """
    clusters = triz_report_to_dict(report)["innovation_clusters"]
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(
        ["cluster_id", "innovation_score", "rarity", "contradiction_density", "propagation_reach", "concepts"]
    )
    for cl in clusters:
        w.writerow(
            [
                cl["cluster_id"],
                cl["innovation_score"],
                cl["rarity"],
                cl["contradiction_density"],
                cl["propagation_reach"],
                "|".join(cl["concepts"]),
            ]
        )
    scores = [float(c["innovation_score"]) for c in clusters]
    metrics = {
        "cluster_count": len(clusters),
        "max_innovation_score": round(max(scores), 6) if scores else 0.0,
        "mean_innovation_score": round(sum(scores) / len(scores), 6) if scores else 0.0,
    }
    return {
        "product": "innovation_radar",
        "csv": buf.getvalue(),
        "metrics": metrics,
        "clusters_json": clusters,
    }


def export_narrative_monitor(report: TRIZReport) -> dict[str, Any]:
    """Dashboard metrics — Narrative Propagation Monitor."""
    narratives = triz_report_to_dict(report)["narratives"]
    return {
        "product": "narrative_propagation_monitor",
        "dashboard": {
            "narratives": narratives,
            "aggregate_penetration": round(
                sum(float(n["penetration"]) for n in narratives) / max(len(narratives), 1),
                6,
            ),
            "aggregate_velocity": round(
                sum(float(n["velocity"]) for n in narratives) / max(len(narratives), 1),
                6,
            ),
            "aggregate_stability": round(
                sum(float(n["stability"]) for n in narratives) / max(len(narratives), 1),
                6,
            ),
        },
    }


def triz_topology_csv_bundle(
    contradictions: list[dict[str, Any]],
    innovation_clusters: list[dict[str, Any]],
    narrative_routes: list[dict[str, Any]],
    strongest_paths: list[dict[str, Any]],
    area_hotspots: list[dict[str, Any]],
) -> dict[str, str]:
    """Deterministic CSV exports; sort by score desc then id."""
    def w_csv(headers: list[str], rows: list[list[Any]]) -> str:
        buf = io.StringIO()
        wr = csv.writer(buf)
        wr.writerow(headers)
        for r in rows:
            wr.writerow(r)
        return buf.getvalue()

    con_sorted = sorted(
        contradictions,
        key=lambda x: (-float(x.get("score", 0)), str(x.get("concept_a", "")), str(x.get("concept_b", ""))),
    )
    c_headers = [
        "concept_a",
        "concept_b",
        "score",
        "triz_class",
        "area_a",
        "area_b",
        "family_a",
        "family_b",
        "same_area",
        "adjacent_areas",
        "locality_score",
    ]
    c_rows = [
        [
            r.get("concept_a"),
            r.get("concept_b"),
            round(float(r.get("score", 0)), 6),
            r.get("triz_class"),
            r.get("area_a"),
            r.get("area_b"),
            r.get("family_a"),
            r.get("family_b"),
            r.get("same_area"),
            r.get("adjacent_areas"),
            r.get("locality_score"),
        ]
        for r in con_sorted
    ]
    ic_sorted = sorted(
        innovation_clusters,
        key=lambda x: (-float(x.get("innovation_score", 0)), str(x.get("cluster_id", ""))),
    )
    ic_rows = [
        [
            c.get("cluster_id"),
            round(float(c.get("innovation_score", 0)), 6),
            c.get("rarity"),
            c.get("contradiction_density"),
            c.get("propagation_reach"),
            "|".join(c.get("concepts") or []),
        ]
        for c in ic_sorted
    ]
    nr_sorted = sorted(narrative_routes, key=lambda x: (x.get("step", 0), x.get("area", 0)))
    nr_rows = [[r.get("step"), r.get("area"), r.get("activation")] for r in nr_sorted]
    sp_sorted = sorted(
        strongest_paths,
        key=lambda x: (-float(x.get("path_score", 0)), str(x.get("path", []))),
    )
    sp_rows = [
        [p.get("narrative_id"), "|".join(str(x) for x in (p.get("path") or [])), p.get("path_score"), p.get("route_type")]
        for p in sp_sorted
    ]
    ah_sorted = sorted(area_hotspots, key=lambda x: (-float(x.get("hotspot_score", 0)), x.get("area", 0)))
    ah_rows = [[h.get("area"), round(float(h.get("hotspot_score", 0)), 6)] for h in ah_sorted]

    return {
        "area_hotspots.csv": w_csv(["area", "hotspot_score"], ah_rows),
        "contradictions.csv": w_csv(c_headers, c_rows),
        "innovation_clusters.csv": w_csv(
            ["cluster_id", "innovation_score", "rarity", "contradiction_density", "propagation_reach", "concepts"],
            ic_rows,
        ),
        "narrative_routes.csv": w_csv(["step", "area", "activation"], nr_rows),
        "narrative_strongest_paths.csv": w_csv(
            ["narrative_id", "path", "path_score", "route_type"],
            sp_rows,
        ),
    }
