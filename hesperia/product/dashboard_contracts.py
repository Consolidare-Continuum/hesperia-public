# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# See LEGAL_NOTICE.md for full terms.

"""Versioned chart-ready payloads for TRIZ UI."""

from __future__ import annotations

from typing import Any

DASHBOARD_SCHEMA_VERSION = "triz_ui_v1"


def contract_area_family_heatmap(triz_full: dict[str, Any]) -> dict[str, Any]:
    rows: list[int] = []
    cols: list[int] = []
    values: list[float] = []
    for h in sorted(
        triz_full.get("topology", {}).get("family_hotspots", []),
        key=lambda x: (-float(x.get("hotspot_score", 0)), x.get("area_a", 0)),
    )[:48]:
        ra = int(h.get("area_a", -1))
        fa = int(h.get("family_a", 0))
        rb = int(h.get("area_b", -1))
        fb = int(h.get("family_b", 0))
        sc = float(h.get("hotspot_score", 0))
        key_a = ra * 1000 + fa
        key_b = rb * 1000 + fb
        if key_a not in rows:
            rows.append(key_a)
        if key_b not in cols:
            cols.append(key_b)
        values.append(round(sc, 6))
    rows.sort()
    cols.sort()
    return {
        "schema_version": DASHBOARD_SCHEMA_VERSION,
        "type": "area_family_heatmap",
        "rows": rows,
        "cols": cols,
        "values": values[: min(len(values), len(rows) * len(cols) or 1)],
    }


def contract_ranked_clusters(triz_full: dict[str, Any]) -> dict[str, Any]:
    items = sorted(
        triz_full.get("innovation_clusters", []),
        key=lambda x: (-float(x.get("innovation_score", 0)), str(x.get("cluster_id", ""))),
    )
    return {
        "schema_version": DASHBOARD_SCHEMA_VERSION,
        "type": "ranked_clusters",
        "items": [
            {
                "id": c.get("cluster_id"),
                "label": "Innovation Pressure Score",
                "value": round(float(c.get("innovation_score", 0)), 6),
                "concepts": c.get("concepts") or [],
            }
            for c in items
        ],
    }


def contract_route_graph(triz_full: dict[str, Any]) -> dict[str, Any]:
    top = triz_full.get("topology", {}).get("strongest_paths") or []
    nodes: set[int] = set()
    edges: list[dict[str, Any]] = []
    for p in top[:12]:
        path = p.get("path") or []
        for a in path:
            nodes.add(int(a))
        for i in range(len(path) - 1):
            edges.append(
                {
                    "source": int(path[i]),
                    "target": int(path[i + 1]),
                    "weight": round(float(p.get("path_score", 0)), 6),
                    "route_type": p.get("route_type"),
                }
            )
    return {
        "schema_version": DASHBOARD_SCHEMA_VERSION,
        "type": "route_graph",
        "nodes": [{"id": n, "label": f"Area {n}"} for n in sorted(nodes)],
        "edges": edges,
    }


def build_dashboard_bundle(triz_full: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": DASHBOARD_SCHEMA_VERSION,
        "heatmap": contract_area_family_heatmap(triz_full),
        "ranked_clusters": contract_ranked_clusters(triz_full),
        "route_graph": contract_route_graph(triz_full),
    }


def validate_dashboard_bundle(bundle: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    if bundle.get("schema_version") != DASHBOARD_SCHEMA_VERSION:
        errs.append("schema_version mismatch")
    for key in ("heatmap", "ranked_clusters", "route_graph"):
        sub = bundle.get(key)
        if not isinstance(sub, dict):
            errs.append(f"missing {key}")
        elif sub.get("type") is None:
            errs.append(f"{key}.type missing")
    return errs
