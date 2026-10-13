# HESPERIA — RAD. Ξ / L3 tension proxy → L7 contradiction drive (Ethan compact H8).
# Full Ξ = Σ K_ij c_i c_j − ω Σ W_ij c_i c_j requires graph state; TRIZ rows proxy tension.
# Optional: full-graph KME ActiveGraph tension (env HESPERIA_FIELD_DYNAMICS_XI_KME).

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from core.domain.models import ActiveGraph

from core.topology.invariant_catalog import AREAS as NUM_AREAS


def _xi_scale_from_env() -> float:
    import os

    v = os.environ.get("HESPERIA_FIELD_DYNAMICS_XI_SCALE", "").strip()
    if not v:
        return 0.14
    try:
        return max(0.0, min(0.5, float(v)))
    except (TypeError, ValueError):
        return 0.14


def xi_proxy_from_triz_rows(rows: list[dict[str, Any]]) -> tuple[float, list[float]]:
    """
    Global tension scalar + per-area profile from contradiction topology rows.
    Returns (xi_global in [0,1], xi_area[12] normalized peak=1).
    """
    if not rows:
        return 0.0, [0.0] * NUM_AREAS
    total_score = 0.0
    per = [0.0] * NUM_AREAS
    for r in rows:
        try:
            sc = min(1.0, max(0.0, float(r.get("score") or 0.0)))
        except (TypeError, ValueError):
            sc = 0.0
        total_score += sc
        for ak in ("area_a", "area_b"):
            a = r.get(ak)
            if isinstance(a, int) and 0 <= a < NUM_AREAS:
                per[a] += sc
    xi_global = min(1.0, total_score / max(8.0, float(len(rows))))
    m = max(per) if per else 0.0
    if m <= 0:
        pern = [0.0] * NUM_AREAS
    else:
        pern = [min(1.0, x / m) for x in per]
    return xi_global, pern


def area_label_to_index(area: str | None) -> int | None:
    """Map ``A1``..``A12`` to 0..11; else None."""
    if area is None:
        return None
    s = str(area).strip().upper()
    if not s.startswith("A") or len(s) < 2:
        return None
    try:
        n = int(s[1:])
    except ValueError:
        return None
    if 1 <= n <= NUM_AREAS:
        return n - 1
    return None


def xi_proxy_from_kme_active_graph(
    ag: "ActiveGraph",
    concept_to_area_family: dict[str, tuple[str, str]],
) -> tuple[float, list[float]]:
    """
    Global + per-area tension from full KME ActiveGraph (nodes + cross-area edges).

    - Node mass: each active concept adds ``hit_count`` to its area (from Dict-B placement).
    - Cross-area edges: each edge whose endpoints map to different areas adds geometric-mean
      stress to both endpoint areas (full-graph signal beyond TRIZ contradiction rows).
    """
    per = [0.0] * NUM_AREAS
    if not ag.nodes:
        return 0.0, per

    for cid, node in sorted(ag.nodes.items()):
        af = concept_to_area_family.get(cid)
        if not af:
            continue
        area_s, _fam = af
        ai = area_label_to_index(area_s)
        if ai is None:
            continue
        per[ai] += float(max(0, node.hit_count))

    cross_area_edges = 0
    for e in ag.edges:
        af_s = concept_to_area_family.get(e.source_concept_id)
        af_t = concept_to_area_family.get(e.target_concept_id)
        if not af_s or not af_t:
            continue
        ia = area_label_to_index(af_s[0])
        ib = area_label_to_index(af_t[0])
        if ia is None or ib is None:
            continue
        ns = ag.nodes.get(e.source_concept_id)
        nt = ag.nodes.get(e.target_concept_id)
        if not ns or not nt:
            continue
        w = math.sqrt(float(max(1, ns.hit_count)) * float(max(1, nt.hit_count)))
        if ia == ib:
            per[ia] += w * 0.25
        else:
            cross_area_edges += 1
            per[ia] += w
            per[ib] += w

    m = max(per) if per else 0.0
    if m <= 0:
        pern = [0.0] * NUM_AREAS
    else:
        pern = [min(1.0, x / m) for x in per]

    n_nodes = len(ag.nodes)
    n_edges = len(ag.edges)
    xi_global = min(
        1.0,
        (n_edges / max(8.0, float(n_nodes))) * 0.35 + (float(cross_area_edges) / max(4.0, float(n_edges or 1))) * 0.4,
    )
    return xi_global, pern


def _xi_kme_weight_from_env() -> float:
    import os

    v = os.environ.get("HESPERIA_FIELD_DYNAMICS_XI_KME_WEIGHT", "").strip()
    if not v:
        return 0.55
    try:
        return max(0.0, min(1.0, float(v)))
    except (TypeError, ValueError):
        return 0.55


def apply_xi_to_contradiction_signal(
    c_sig_12: list[float],
    triz_rows: list[dict[str, Any]],
    *,
    xi_scale: float | None = None,
    kme_active_graph: "ActiveGraph | None" = None,
    concept_to_area_family: dict[str, tuple[str, str]] | None = None,
) -> tuple[list[float], dict[str, Any]]:
    """
    Boost L7 area contradiction drive toward TRIZ-localized tension (Ξ proxy).
    ``xi_scale``: if None, uses env ``HESPERIA_FIELD_DYNAMICS_XI_SCALE`` (default 0.14).

    When ``HESPERIA_FIELD_DYNAMICS_XI_KME=1`` and ``kme_active_graph`` + ``concept_to_area_family``
    are provided, blends TRIZ-row profile with full-graph KME tension (Ethan: full-graph Ξ).
    """
    xs = float(xi_scale) if xi_scale is not None else _xi_scale_from_env()
    g_t, per_t = xi_proxy_from_triz_rows(triz_rows)

    use_kme = field_dynamics_xi_kme_enabled() and kme_active_graph is not None and concept_to_area_family
    g_k = 0.0
    per_k = [0.0] * NUM_AREAS
    if use_kme:
        g_k, per_k = xi_proxy_from_kme_active_graph(kme_active_graph, concept_to_area_family)

    wk = _xi_kme_weight_from_env() if use_kme else 0.0
    if use_kme and triz_rows:
        g = (1.0 - wk) * g_t + wk * g_k
        per = [(1.0 - wk) * per_t[i] + wk * per_k[i] for i in range(NUM_AREAS)]
    elif use_kme and not triz_rows:
        g, per = g_k, per_k
    else:
        g, per = g_t, per_t

    meta = {
        "xi_proxy_global": round(g, 6),
        "xi_scale": round(xs, 6),
        "xi_triz_global": round(g_t, 6),
        "xi_kme_global": round(g_k, 6) if use_kme else None,
        "xi_kme_blended": bool(use_kme),
        "xi_kme_weight": round(wk, 6) if use_kme else None,
    }
    if not triz_rows and not use_kme:
        return list(c_sig_12), meta
    out = []
    for a in range(NUM_AREAS):
        boost = xs * (0.35 * g + 0.65 * per[a])
        out.append(min(1.0, max(0.0, float(c_sig_12[a]) + boost)))
    return out, meta


def field_dynamics_xi_enabled() -> bool:
    import os

    v = os.environ.get("HESPERIA_FIELD_DYNAMICS_XI", "1").strip().lower()
    return v not in ("0", "false", "no")


def field_dynamics_xi_kme_enabled() -> bool:
    import os

    v = os.environ.get("HESPERIA_FIELD_DYNAMICS_XI_KME", "0").strip().lower()
    return v in ("1", "true", "yes", "on")
