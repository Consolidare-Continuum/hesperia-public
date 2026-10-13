# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# See LEGAL_NOTICE.md for full terms.

"""Family- and area-family-level contradiction clustering and hotspots."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from hesperia.extensions.triz.topology_binding import bind_concept_to_matrix
from hesperia.extensions.triz.topology_metrics import area_distance


def cluster_contradictions_by_family(
    contradictions: list[Any],
    concept_mapping: dict[str, Any],
) -> list[dict[str, Any]]:
    """Group by global family pair (f1, f2) with count, avg_score, top_concepts."""
    groups: dict[tuple[int, int], list[Any]] = defaultdict(list)
    for c in contradictions:
        ma = bind_concept_to_matrix(c.concept_a, concept_mapping)
        mb = bind_concept_to_matrix(c.concept_b, concept_mapping)
        fa, fb = ma.family_id, mb.family_id
        if fa < 0 or fb < 0:
            continue
        key = tuple(sorted((fa, fb)))
        groups[key].append(c)
    out: list[dict[str, Any]] = []
    for (f1, f2), items in sorted(groups.items(), key=lambda x: (-len(x[1]), x[0][0], x[0][1])):
        scores = [float(x.score) for x in items]
        concepts: set[str] = set()
        for x in items:
            concepts.add(x.concept_a)
            concepts.add(x.concept_b)
        top = sorted(concepts)[:12]
        out.append(
            {
                "family_pair": [f1, f2],
                "count": len(items),
                "avg_score": round(sum(scores) / max(len(scores), 1), 6),
                "top_concepts": top,
            }
        )
    return out


def cluster_contradictions_by_area_family(
    contradictions: list[Any],
    concept_mapping: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Pairs like Area 3 / Family 8 ↔ Area 7 / Family 14.
    Key is canonical sorted ((area_a, fam_a), (area_b, fam_b)).
    """
    groups: dict[tuple[tuple[int, int], tuple[int, int]], list[Any]] = defaultdict(list)
    for c in contradictions:
        ma = bind_concept_to_matrix(c.concept_a, concept_mapping)
        mb = bind_concept_to_matrix(c.concept_b, concept_mapping)
        if ma.area_id < 0 or mb.area_id < 0 or ma.family_id < 0 or mb.family_id < 0:
            continue
        p1 = (ma.area_id, ma.family_id)
        p2 = (mb.area_id, mb.family_id)
        key = tuple(sorted((p1, p2)))
        groups[key].append(c)
    out: list[dict[str, Any]] = []
    for key, items in sorted(groups.items(), key=lambda x: (-len(x[1]), x[0])):
        (a1, f1), (a2, f2) = key[0], key[1]
        scores = [float(x.score) for x in items]
        out.append(
            {
                "area_a": a1,
                "family_a": f1,
                "area_b": a2,
                "family_b": f2,
                "count": len(items),
                "avg_score": round(sum(scores) / max(len(scores), 1), 6),
            }
        )
    return out


def get_conflict_hotspots(
    contradictions: list[Any],
    concept_mapping: dict[str, Any],
    top_n: int = 20,
) -> list[dict[str, Any]]:
    """hotspot_score = count * avg_score * cross_area_factor."""
    af_clusters = cluster_contradictions_by_area_family(contradictions, concept_mapping)
    ranked: list[dict[str, Any]] = []
    for row in af_clusters:
        d = area_distance(int(row["area_a"]), int(row["area_b"]))
        if d == 0:
            cross = 1.0
        elif d == 1:
            cross = 1.5
        else:
            cross = 2.0
        score = float(row["count"]) * float(row["avg_score"]) * cross
        ranked.append(
            {
                "area_a": row["area_a"],
                "family_a": row["family_a"],
                "area_b": row["area_b"],
                "family_b": row["family_b"],
                "contradiction_count": row["count"],
                "avg_score": row["avg_score"],
                "cross_area_factor": cross,
                "hotspot_score": round(score, 6),
            }
        )
    ranked.sort(key=lambda x: (-x["hotspot_score"], x["area_a"], x["family_a"], x["area_b"], x["family_b"]))
    return ranked[: max(0, top_n)]
