# HESPERIA — RAD. Map TRIZ contradiction rows → 12-area drive for Phase 1 p_a.

from __future__ import annotations

from typing import Any

from core.topology.invariant_catalog import AREAS as NUM_AREAS


def contradiction_signal_12_from_con_rows(con_rows: list[dict[str, Any]]) -> list[float]:
    """
    Accumulate contradiction scores onto areas (area_a / area_b; fallback area_cluster).
    Normalized so max component is 1.0 when any mass; else zeros.
    """
    sig = [0.0] * NUM_AREAS
    for row in con_rows:
        try:
            sc = float(row.get("score") or 0.0)
        except (TypeError, ValueError):
            sc = 0.0
        sc = min(1.0, max(0.0, sc))
        areas: set[int] = set()
        for ak in ("area_a", "area_b"):
            a = row.get(ak)
            if isinstance(a, int) and 0 <= a < NUM_AREAS:
                areas.add(a)
        if not areas:
            for a in row.get("area_cluster") or []:
                if isinstance(a, int) and 0 <= a < NUM_AREAS:
                    areas.add(a)
        for a in areas:
            sig[a] += sc
    m = max(sig) if sig else 0.0
    if m > 0:
        return [min(1.0, x / m) for x in sig]
    return [0.0] * NUM_AREAS


def fetch_triz_contradiction_rows(
    text: str,
) -> tuple[list[dict[str, Any]], dict[str, Any], Any]:
    """
    Session → clinical graph → TRIZ complete; return contradiction rows + small meta + ActiveGraph.

    Third value is the clinical :class:`~core.domain.models.ActiveGraph` when built (possibly
    empty nodes), or ``None`` on hard failure. Used for full-graph Ξ (KME) when TRIZ rows are sparse.
    On failure: ``([], {"_error": ...}, None)``.
    """
    meta: dict[str, Any] = {"contradiction_count": 0}
    try:
        from hesperia.engine.kme.clinical_bridge import build_clinical_active_graph
        from hesperia.extensions.triz.pipeline import active_graph_from_payload, run_triz_analysis_complete
        from hesperia.nlp.session_parser import analyze_session

        try:
            from sphere.topology.family_embedding import load_family_embedding_tfp

            embedding = load_family_embedding_tfp()
        except Exception:
            embedding = {}
        activation = analyze_session(text, embedding=embedding)
        ag = build_clinical_active_graph(activation)
        if not ag.nodes:
            meta["triz_note"] = "no_active_nodes"
            return [], meta, ag
        payload = {
            "nodes": {cid: {"hitCount": n.hit_count} for cid, n in sorted(ag.nodes.items())},
            "edges": [
                {
                    "source": e.source_concept_id,
                    "target": e.target_concept_id,
                    "type": e.relation_type or "",
                }
                for e in sorted(
                    ag.edges,
                    key=lambda x: (x.source_concept_id, x.target_concept_id, x.relation_type or ""),
                )
            ],
        }
        from runtime.pipeline.run_e2e_all import _activation_topology_maps

        topo = _activation_topology_maps(activation, set(ag.nodes.keys()))
        ag2 = active_graph_from_payload(payload)
        content = run_triz_analysis_complete(
            ag2,
            topo,
            narrative_id="field_dynamics_e2e",
            run_id=None,
            topology_mode=True,
        )
        rows = list(content.get("contradictions") or [])
        meta["contradiction_count"] = len(rows)
        return rows, meta, ag
    except Exception as e:
        meta["_error"] = str(e)
        return [], meta, None
