# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# See LEGAL_NOTICE.md for full terms.

"""Contradiction detection from concept activations + typed relations."""

from __future__ import annotations

from hesperia.extensions.triz.models import ConceptActivation, ConceptRelation, ContradictionSignal, MatrixCoordinate

CONFLICT_TYPES = frozenset({"conflict", "negation", "opposition"})

_REL_WEIGHT: dict[str, float] = {
    "conflict": 1.0,
    "negation": 1.0,
    "opposition": 0.85,
}

# Deterministic pair → principle (supplement to lexical table in triz_classifier)
_HASH_TO_CLASS = (
    "segmentation",
    "counterbalance",
    "parameter_change",
    "dynamic_adaptation",
)


def classify_triz_pattern(concept_a: str, concept_b: str) -> str:
    """
    Return one of: segmentation, counterbalance, parameter_change, dynamic_adaptation.
    Lexical table first; else stable hash bucket.
    """
    from hesperia.extensions.triz.triz_classifier import classify_contradiction

    c = classify_contradiction(concept_a, concept_b)
    if c in _HASH_TO_CLASS:
        return c
    s = "\0".join(sorted((concept_a, concept_b)))
    h = 0
    for ch in s:
        h = (h * 31 + ord(ch)) & 0xFFFFFFFF
    return _HASH_TO_CLASS[h % 4]


def enumerate_contradiction_pairs(
    activations: list[ConceptActivation],
    relations: list[ConceptRelation],
    conflict_types: set[str] | None = None,
) -> list[tuple[str, str, float]]:
    """Return (concept_a, concept_b, raw_score) sorted by score desc, then ids."""
    ct = conflict_types if conflict_types is not None else set(CONFLICT_TYPES)
    act_map = {a.concept_id: float(a.activation) for a in activations}
    out: list[tuple[str, str, float]] = []
    for r in relations:
        rt = (r.relation_type or "").strip().lower()
        if rt not in ct:
            continue
        sa, ta = r.source, r.target
        if sa not in act_map or ta not in act_map:
            continue
        w = _REL_WEIGHT.get(rt, 1.0) * float(r.weight)
        score = min(1.0, act_map[sa] * act_map[ta] * w)
        out.append((sa, ta, score))
    out.sort(key=lambda t: (-t[2], t[0], t[1]))
    return out


def detect_contradictions(
    active_graph: object,
    *,
    concept_to_area: dict[str, int] | None = None,
    min_score: float = 0.15,
) -> list[ContradictionSignal]:
    """
    ActiveGraph path: conflict / negation / opposition edges → ContradictionSignal list.
    """
    from hesperia.extensions.triz.models import ConceptActivation, ConceptRelation, MatrixCoordinate
    from hesperia.extensions.triz.topology_binding import bind_concepts_to_coordinates

    mx = max((node.hit_count for node in active_graph.nodes.values()), default=1)
    mx = max(mx, 1)
    c2a = concept_to_area or {}
    acts: list[ConceptActivation] = []
    for cid, n in sorted(active_graph.nodes.items()):
        act = min(1.0, float(n.hit_count) / float(mx))
        ai = int(c2a[cid]) if cid in c2a else -1
        acts.append(ConceptActivation(cid, act, MatrixCoordinate(ai, -1, None)))
    rels = [
        ConceptRelation(e.source_concept_id, e.target_concept_id, e.relation_type or "", 1.0)
        for e in active_graph.edges
    ]
    coords = bind_concepts_to_coordinates(acts)
    return build_contradiction_signals(acts, rels, coords, min_score=min_score)


def build_contradiction_signals(
    activations: list[ConceptActivation],
    relations: list[ConceptRelation],
    concept_coords: dict[str, MatrixCoordinate],
    *,
    min_score: float = 0.15,
) -> list[ContradictionSignal]:
    """Attach TRIZ class and matrix coordinates; filter by min_score."""
    default = MatrixCoordinate(-1, -1, None)
    raw = enumerate_contradiction_pairs(activations, relations)
    signals: list[ContradictionSignal] = []
    seen: set[tuple[str, str]] = set()
    for sa, ta, sc in raw:
        if sc < min_score:
            continue
        key = (sa, ta) if sa <= ta else (ta, sa)
        if key in seen:
            continue
        seen.add(key)
        triz = classify_triz_pattern(sa, ta)
        signals.append(
            ContradictionSignal(
                concept_a=sa,
                concept_b=ta,
                score=round(float(sc), 6),
                triz_class=triz,
                coord_a=concept_coords.get(sa, default),
                coord_b=concept_coords.get(ta, default),
            )
        )
    signals.sort(key=lambda c: (-c.score, c.concept_a, c.concept_b))
    return signals
