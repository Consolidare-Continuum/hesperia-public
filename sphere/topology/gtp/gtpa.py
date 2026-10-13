# HESPERIA — GTP-05: GTPA next-hex selection (deterministic core).
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""
Score(h') and argmax per spec §10.2:

    Score(h') = eta * PathPrior(h, h', P)
              + kappa * CoherenceAlign(h', Psi)
              + lambda * sum_s m_s(h', s)
              - mu * SemanticPenalty(h')          # default mu -> 0

    h* = argmax_{h' in N(h)} Score(h')
    exit_side* = argmax_s m_s(h*, s)
    hex_rotation* = the calibrated rotation used to score h*

Deterministic tie-break per spec §10.2: lower global_id, then lower hex_index,
then lower side_id.

PathPrior and CoherenceAlign both fall back to the spec's own stated defaults where
the referenced `40_POLICY`/`anchor_map_v1` don't exist yet (see neighbors.py,
coherence.py docstrings): PathPrior is a uniform per-step-kind weight (overridable via
`path_template`); CoherenceAlign is the spec's explicitly allowed "lookup table from
anchor map" fallback — the sum of the area and family delta_k slots of Psi.vector
matching h'.
"""

from __future__ import annotations

from dataclasses import dataclass

from sphere.topology.gtp.coherence import NUM_AREAS, CoherenceField
from sphere.topology.gtp.neighbors import HexCell, legal_neighbors
from sphere.topology.gtp.rotation import side_match_score, side_specs_for_rotation

ETA_DEFAULT = 1.0
KAPPA_DEFAULT = 1.0
LAMBDA_DEFAULT = 1.0
MU_DEFAULT = 0.0  # spec §10.2: "default mu -> 0 for almost no semantic"

DEFAULT_PATH_TEMPLATE: dict[str, float] = {"area": 1.0, "family": 1.0, "hex": 1.0}


def _step_kind(h: HexCell, h2: HexCell) -> str:
    if h2.area_id != h.area_id:
        return "area"
    if h2.global_id != h.global_id:
        return "family"
    return "hex"


def path_prior(h: HexCell, h2: HexCell, path_template: dict[str, float] | None = None) -> float:
    template = path_template or DEFAULT_PATH_TEMPLATE
    return template.get(_step_kind(h, h2), 0.0)


def coherence_align(h2: HexCell, psi: CoherenceField) -> float:
    """Lookup-table fallback per spec §10.2: sum of h2's area and family delta_k slots."""
    area_delta = psi.vector[h2.area_id]
    family_delta = psi.vector[NUM_AREAS + h2.global_id]
    return area_delta + family_delta


@dataclass(frozen=True)
class GTPAResult:
    next_hex: HexCell
    exit_side: int
    hex_rotation: int
    score: float


def score(
    h: HexCell,
    h2: HexCell,
    *,
    psi: CoherenceField,
    phi: frozenset[str],
    hex_rotation: int,
    path_template: dict[str, float] | None = None,
    eta: float = ETA_DEFAULT,
    kappa: float = KAPPA_DEFAULT,
    lam: float = LAMBDA_DEFAULT,
    mu: float = MU_DEFAULT,
    semantic_penalty: float = 0.0,
) -> float:
    """
    Score(h') per spec §10.2.

    Scoping note: `side_sum` uses the single `hex_rotation` calibrated once per step
    (GTP-03, over the whole input wording) rather than a per-candidate rotation search —
    it is therefore the same value added to every h2 in one gtpa_next_hex() call. Only
    `path_prior` and `coherence_align` actually discriminate between candidates in v0.1.
    A per-candidate rotation search is a valid future extension, not required by the
    spec's own definitions (the six-side operator registry is universal, not per-hex).
    """
    side_sum = sum(side_match_score(phi, spec) for spec in side_specs_for_rotation(hex_rotation))
    return (
        eta * path_prior(h, h2, path_template)
        + kappa * coherence_align(h2, psi)
        + lam * side_sum
        - mu * semantic_penalty
    )


def gtpa_next_hex(
    h: HexCell,
    *,
    psi: CoherenceField,
    phi: frozenset[str],
    hex_rotation: int,
    path_template: dict[str, float] | None = None,
    eta: float = ETA_DEFAULT,
    kappa: float = KAPPA_DEFAULT,
    lam: float = LAMBDA_DEFAULT,
    mu: float = MU_DEFAULT,
) -> GTPAResult:
    """h* = argmax over N(h); deterministic tie-break. Spec §10.2-10.3."""
    candidates = legal_neighbors(h)
    if not candidates:
        raise ValueError(f"no legal neighbors for {h!r}")

    side_specs = side_specs_for_rotation(hex_rotation)
    exit_side = max(range(6), key=lambda k: (side_match_score(phi, side_specs[k]), -k))

    scored: list[tuple[float, HexCell]] = [
        (
            score(
                h,
                h2,
                psi=psi,
                phi=phi,
                hex_rotation=hex_rotation,
                path_template=path_template,
                eta=eta,
                kappa=kappa,
                lam=lam,
                mu=mu,
            ),
            h2,
        )
        for h2 in candidates
    ]
    # Higher score wins; ties broken by lower global_id, then lower hex_index (spec §10.2).
    best_score, next_hex = max(scored, key=lambda item: (item[0], -item[1].global_id, -item[1].hex_index))
    return GTPAResult(next_hex=next_hex, exit_side=exit_side, hex_rotation=hex_rotation, score=best_score)
