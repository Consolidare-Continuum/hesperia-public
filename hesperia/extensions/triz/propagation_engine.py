# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# See LEGAL_NOTICE.md for full terms.

"""Iterative activation propagation over topology + narrative metrics."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from hesperia.extensions.triz.models import NarrativeSignal

if TYPE_CHECKING:
    from core.domain.models import ActiveGraph


def _base_activations(graph: "ActiveGraph") -> dict[str, float]:
    mx = max((n.hit_count for n in graph.nodes.values()), default=1)
    mx = max(mx, 1)
    return {cid: min(1.0, float(n.hit_count) / float(mx)) for cid, n in graph.nodes.items()}


def _build_adjacency_from_active(graph: "ActiveGraph") -> dict[str, list[tuple[str, float]]]:
    adj: dict[str, list[tuple[str, float]]] = {cid: [] for cid in graph.nodes}
    conflict = frozenset({"conflict", "negation", "opposition"})
    for e in graph.edges:
        u, v = e.source_concept_id, e.target_concept_id
        if u not in adj or v not in adj:
            continue
        rt = (e.relation_type or "").strip().lower()
        if rt in conflict:
            continue
        adj[u].append((v, 1.0))
        adj[v].append((u, 1.0))
    for k in adj:
        adj[k] = sorted(adj[k], key=lambda t: (t[0], t[1]))
    return adj


def propagate_activations(
    active_graph: "ActiveGraph",
    topology_adjacency: dict[str, list[tuple[str, float]]] | None,
    *,
    max_steps: int = 12,
    damping: float = 0.08,
) -> tuple[dict[str, float], int, list[float]]:
    """
    activation_next = base + Σ(neighbor_weight * relation_strength) - damping, clamped [0,1].
    Returns (final_activation, steps_run, history_total_activation_per_step).
    """
    base = _base_activations(active_graph)
    if not base:
        return {}, 0, []
    adj = topology_adjacency if topology_adjacency else _build_adjacency_from_active(active_graph)
    cur = dict(base)
    hist: list[float] = []
    steps_run = 0
    for _ in range(max_steps):
        nxt: dict[str, float] = {}
        for node in sorted(cur.keys()):
            b = base.get(node, 0.0)
            acc = sum(w * cur[nb] for nb, w in adj.get(node, []) if nb in cur)
            val = b + acc - damping
            nxt[node] = max(0.0, min(1.0, val))
        steps_run += 1
        hist.append(sum(nxt.values()))
        if all(abs(nxt[k] - cur[k]) < 1e-8 for k in cur):
            cur = nxt
            break
        cur = nxt
    return cur, steps_run, hist


def _persistence_stability(hist: list[float], max_steps: int) -> float:
    """Trailing steps where total activation change is negligible."""
    if len(hist) < 2:
        return 0.0
    persistence = 0
    for i in range(len(hist) - 1, 0, -1):
        if abs(hist[i] - hist[i - 1]) < 1e-5:
            persistence += 1
        else:
            break
    return min(1.0, float(persistence) / float(max(max_steps - 1, 1)))


def compute_narrative_signals(
    active_graph: "ActiveGraph",
    topology_adjacency: dict[str, list[tuple[str, float]]] | None,
    *,
    concept_to_area: dict[str, int] | None,
    concept_to_family: dict[str, int] | None,
    total_families: int = 240,
    min_propagation_steps: int = 2,
    max_steps: int = 12,
    damping: float = 0.08,
    narrative_id: str = "narrative_primary",
) -> list[NarrativeSignal]:
    """velocity = activated_areas / steps_eff; penetration; stability = persistence_time."""
    final, steps, hist = propagate_activations(
        active_graph,
        topology_adjacency,
        max_steps=max_steps,
        damping=damping,
    )
    steps_eff = max(steps, min_propagation_steps)

    areas_active: set[int] = set()
    if concept_to_area:
        for cid, act in final.items():
            if act > 0.05 and cid in concept_to_area:
                areas_active.add(int(concept_to_area[cid]))
    else:
        order = sorted(active_graph.nodes.keys())
        pos = {c: i for i, c in enumerate(order)}
        for cid, act in final.items():
            if act > 0.05 and cid in pos:
                areas_active.add(pos[cid] % 10)

    activated_areas_list = sorted(areas_active)
    n_areas = max(len(activated_areas_list), 1)
    velocity = min(1.0, float(n_areas) / float(steps_eff))

    fam_active: set[int] = set()
    if concept_to_family:
        for cid, act in final.items():
            if act > 0.05 and cid in concept_to_family:
                fam_active.add(int(concept_to_family[cid]))
    penetration = min(1.0, float(len(fam_active)) / float(max(total_families, 1)))

    stability = _persistence_stability(hist, max_steps)

    return [
        NarrativeSignal(
            narrative_id=narrative_id,
            activated_areas=activated_areas_list,
            penetration=round(penetration, 6),
            velocity=round(velocity, 6),
            stability=round(stability, 6),
        )
    ]


# --- Area-level propagation (TRIZ pipeline spec) ---


def aggregate_area_activation(
    activations: list,
) -> dict[int, float]:
    """Sum activations per area_id (0..11); unknown areas skipped."""
    from collections import defaultdict

    acc: dict[int, float] = defaultdict(float)
    cnt: dict[int, int] = defaultdict(int)
    for a in activations:
        aid = int(a.coordinate.area_id)
        if aid < 0 or aid > 11:
            continue
        acc[aid] += float(a.activation)
        cnt[aid] += 1
    return {k: round(acc[k] / max(cnt[k], 1), 6) for k in sorted(acc.keys())}


def propagate_activation(
    area_activation: dict[int, float],
    adjacency: dict[int, list[int]],
    steps: int = 3,
    damping: float = 0.2,
) -> dict[int, float]:
    """
    next_area ≈ base + mean(neighbor activation) - damping per step, clamped [0,1].
    """
    base = {i: 0.0 for i in range(12)}
    for a, v in area_activation.items():
        if 0 <= int(a) <= 11:
            base[int(a)] = float(v)
    cur = dict(base)
    for _ in range(max(1, steps)):
        nxt: dict[int, float] = {}
        for aid in range(12):
            b = base[aid]
            nbs = adjacency.get(aid, [])
            flow = sum(cur.get(nb, 0.0) for nb in nbs) / float(len(nbs)) if nbs else 0.0
            nxt[aid] = max(0.0, min(1.0, b + flow - damping))
        cur = {k: round(v, 6) for k, v in sorted(nxt.items())}
    return cur


def propagate_activation_with_history(
    area_activation: dict[int, float],
    adjacency: dict[int, list[int]],
    steps: int = 3,
    damping: float = 0.2,
) -> tuple[list[dict[int, float]], dict[int, float]]:
    """
    Return (history_per_step, final_state). history[t][a] for t=0..steps, areas 0..11.
    Step 0 = base injection; step k+1 after k propagation iterations.
    """
    base = {i: 0.0 for i in range(12)}
    for a, v in area_activation.items():
        if 0 <= int(a) <= 11:
            base[int(a)] = float(v)
    history: list[dict[int, float]] = []
    cur = {i: round(base[i], 6) for i in range(12)}
    history.append({i: cur[i] for i in range(12)})
    for _ in range(max(1, steps)):
        nxt: dict[int, float] = {}
        for aid in range(12):
            b = base[aid]
            nbs = adjacency.get(aid, [])
            flow = sum(cur.get(nb, 0.0) for nb in nbs) / float(len(nbs)) if nbs else 0.0
            nxt[aid] = max(0.0, min(1.0, b + flow - damping))
        cur = {k: round(v, 6) for k, v in sorted(nxt.items())}
        history.append({i: cur[i] for i in range(12)})
    return history, cur


def build_narrative_signals(
    propagated_activation: dict[int, float],
    family_count: int,
    *,
    activations: list,
    steps: int = 3,
    narrative_id: str = "narrative_primary",
) -> list[NarrativeSignal]:
    activated_areas = sorted(
        a for a, v in propagated_activation.items() if float(v) > 1e-6 and 0 <= int(a) <= 11
    )
    n_areas = max(len(activated_areas), 1)
    velocity = round(min(1.0, float(n_areas) / float(max(steps, 1))), 6)
    fams = {int(a.coordinate.family_id) for a in activations if int(a.coordinate.family_id) >= 0}
    penetration = round(min(1.0, len(fams) / float(max(family_count, 1))), 6)
    tot = sum(float(propagated_activation.get(i, 0.0)) for i in range(12))
    stability = round(min(1.0, tot / float(n_areas) / 6.0), 6)
    return [
        NarrativeSignal(
            narrative_id=narrative_id,
            activated_areas=activated_areas,
            penetration=penetration,
            velocity=velocity,
            stability=stability,
        )
    ]


# --- Topology mode: canonical area adjacency, family propagation, contradiction penalty ---

META_AREAS = frozenset({5, 11})


def contradiction_pressure_by_area(
    contradictions: list[Any],
    concept_to_area: dict[str, int],
) -> dict[int, float]:
    from collections import defaultdict

    p: dict[int, float] = defaultdict(float)
    for c in contradictions:
        for cid in (c.concept_a, c.concept_b):
            if cid in concept_to_area:
                p[int(concept_to_area[cid])] += float(c.score) * 0.5
    return dict(sorted(p.items()))


def propagate_area_activation(
    current_area_state: list[float],
    neighbors: dict[int, list[int]],
    base: list[float],
    contradiction_pressure: dict[int, float],
    damping: float,
    *,
    meta_edge_scale: float = 0.5,
) -> list[float]:
    """
    One step: flow only along canonical adjacency; effective_flow reduces by contradiction pressure.
    """
    n = len(current_area_state)
    nxt = [0.0] * n
    for a in range(n):
        nbs = neighbors.get(a, [])
        if not nbs:
            raw_flow = 0.0
        else:
            acc = 0.0
            for b in nbs:
                w = meta_edge_scale if (a in META_AREAS or b in META_AREAS) else 1.0
                acc += w * current_area_state[b]
            raw_flow = acc / float(len(nbs))
        pen = float(contradiction_pressure.get(a, 0.0))
        effective = max(0.0, raw_flow - pen * 0.35)
        v = base[a] + 0.28 * effective - damping
        nxt[a] = max(0.0, min(1.0, v))
    return nxt


def propagate_family_activation(
    area_id: int,
    family_states: dict[int, float],
    global_family_to_area: list[int],
    neighbor_area_activation: dict[int, float],
    neighbors: dict[int, list[int]],
    base_family: dict[int, float],
    contradiction_pressure: dict[int, float],
    damping: float,
    cross_area_penalty: float = 0.35,
) -> dict[int, float]:
    """Families in same area propagate cheaply; adjacent areas contribute scaled by penalty."""
    fams = [f for f in sorted(family_states.keys()) if 0 <= f < len(global_family_to_area) and global_family_to_area[f] == area_id]
    if not fams:
        return {}
    nxt: dict[int, float] = {}
    same_vals = [family_states[f] for f in fams]
    for f in fams:
        others = [family_states[g] for g in fams if g != f]
        intra = sum(others) / float(len(others)) if others else 0.0
        cross = 0.0
        for nb in neighbors.get(area_id, []):
            boost = float(neighbor_area_activation.get(nb, 0.0))
            cross += boost * cross_area_penalty * 0.12
        pen = float(contradiction_pressure.get(area_id, 0.0))
        raw = float(base_family.get(f, 0.0)) + 0.42 * intra + cross - damping - pen * 0.1
        nxt[f] = max(0.0, min(1.0, raw))
    return nxt


def propagate_topology_mode(
    active_graph: "ActiveGraph",
    concept_to_area: dict[str, int],
    concept_to_family: dict[str, int],
    contradictions: list[Any],
    *,
    max_steps: int = 12,
    area_damping: float = 0.06,
    family_damping: float = 0.05,
    cross_area_penalty: float = 0.35,
) -> dict[str, Any]:
    """
    Bounded propagation: area↔area only on canonical edges; meta areas as reduced-weight channels;
    family flow intra-area first, cross-area penalized; contradiction pressure slows flow.
    """
    from collections import defaultdict

    from sphere.topology.topology_loader import load_family_area_mapping

    from hesperia.extensions.triz.topology_metrics import canonical_area_adjacency, neighbors_from_adjacency

    adj = canonical_area_adjacency()
    neighbors = neighbors_from_adjacency(adj)
    fam_area = load_family_area_mapping().astype(int).tolist()
    mx = max((n.hit_count for n in active_graph.nodes.values()), default=1)
    mx = max(mx, 1)

    base_area = [0.0] * 12
    cnt_a = [0] * 12
    for cid, node in active_graph.nodes.items():
        a = concept_to_area.get(cid)
        if a is None:
            continue
        ai = int(a)
        if ai < 0 or ai > 11 or ai in META_AREAS:
            continue
        act = min(1.0, float(node.hit_count) / float(mx))
        base_area[ai] += act
        cnt_a[ai] += 1
    for i in range(12):
        if cnt_a[i]:
            base_area[i] /= float(cnt_a[i])

    pressure = contradiction_pressure_by_area(contradictions, concept_to_area)
    cur_area = list(base_area)
    area_history: list[tuple[float, ...]] = []
    for _ in range(max_steps):
        cur_area = propagate_area_activation(
            cur_area, neighbors, base_area, pressure, area_damping
        )
        area_history.append(tuple(round(x, 6) for x in cur_area))

    base_f: dict[int, float] = defaultdict(float)
    cnt_f: dict[int, int] = defaultdict(int)
    for cid, node in active_graph.nodes.items():
        f = concept_to_family.get(cid)
        if f is None or int(f) < 0 or int(f) >= len(fam_area):
            continue
        fi = int(f)
        if int(concept_to_area.get(cid, -1)) in META_AREAS:
            continue
        act = min(1.0, float(node.hit_count) / float(mx))
        base_f[fi] += act
        cnt_f[fi] += 1
    for f in list(base_f.keys()):
        base_f[f] /= float(cnt_f[f])

    cur_f = dict(base_f)
    neighbor_area_act = {i: cur_area[i] for i in range(12)}
    for _ in range(max_steps):
        nf: dict[int, float] = {}
        for f in sorted(cur_f.keys()):
            a = fam_area[f]
            others = [cur_f[g] for g in cur_f if fam_area[g] == a and g != f]
            intra = sum(others) / float(len(others)) if others else 0.0
            cross = 0.0
            for nb in neighbors.get(a, []):
                cross += neighbor_area_act.get(nb, 0.0) * cross_area_penalty * 0.1
            pen = float(pressure.get(a, 0.0))
            v = float(base_f.get(f, 0.0)) + 0.42 * intra + cross - family_damping - pen * 0.1
            nf[f] = max(0.0, min(1.0, v))
        cur_f = nf

    return {
        "mode": "topology",
        "area_base": [round(x, 6) for x in base_area],
        "area_activation_final": [round(float(x), 6) for x in cur_area],
        "area_history": area_history,
        "family_activation_final": {str(k): round(v, 6) for k, v in sorted(cur_f.items())},
        "contradiction_pressure": {k: round(v, 6) for k, v in sorted(pressure.items())},
    }

