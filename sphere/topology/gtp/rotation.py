# HESPERIA — GTP-03: hex_rotation calibration + per-side match score.
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""
HexOrientation / hex_rotation per spec §3, §5, §8:

    side_active(k) = (k + hex_rotation) mod 6
    m_s = w_L * match_logical(phi, L) + w_Sigma * match_semantic(phi, Sigma)
    hex_rotation' = argmax_r  sum_k match(phi, L[side_active(k;r)], Sigma[side_active(k;r)])

phi (input wording features) is deliberately minimal per spec §1/§10.3 ("low semantic load"):
a lowercased token set, no embeddings, no LLM call. The engine computes hex_rotation
deterministically; an LLM may only *propose* a candidate r (spec §5.2, "LLM role: propose ...
Engine role: score, select, log provenance").
"""

from __future__ import annotations

import re

from sphere.topology.gtp.side_operators import (
    SIDE_SPECS,
    LogicalOperator,
    SideSpec,
    side_spec,
)

W_L_DEFAULT = 0.7
W_SEM_DEFAULT = 0.3

_TOKEN_RE = re.compile(r"[a-zA-ZĀ-ɏ]+")

# Minimal, explicit keyword sets per LogicalOperator (English; RO surface words are
# matched separately via SemanticOperator). Not exhaustive by design — spec calls for
# "minimal semantic involvement", not a classifier.
_LOGICAL_KEYWORDS: dict[LogicalOperator, frozenset[str]] = {
    LogicalOperator.INCLUDES: frozenset({"include", "includes", "including", "contains", "has", "with"}),
    LogicalOperator.NOT_INCLUDES: frozenset({"exclude", "excludes", "excluding", "without", "lacks", "not"}),
    LogicalOperator.SUBSUMES: frozenset({"covers", "covering", "implies", "subsumes", "encompasses", "all"}),
    LogicalOperator.OVERLAPS: frozenset({"overlaps", "overlapping", "partial", "partially", "some"}),
    LogicalOperator.DISJOINT: frozenset({"disjoint", "separate", "distinct", "none", "unrelated"}),
    LogicalOperator.EQUIVALENT: frozenset({"same", "equivalent", "equal", "identical", "equals"}),
}


def input_features(text: str) -> frozenset[str]:
    """phi(input): minimal, deterministic lowercase token set. No embeddings/LLM."""
    return frozenset(m.group(0).lower() for m in _TOKEN_RE.finditer(text or ""))


def side_active(k: int, hex_rotation: int) -> int:
    """Active side index after rotation. Spec §5.1: side_active(k) = (k + hex_rotation) mod 6."""
    return (k + hex_rotation) % 6


def match_logical(phi: frozenset[str], op: LogicalOperator) -> float:
    """Fraction-style boolean match in [0, 1]: 1.0 if any keyword for op is present."""
    return 1.0 if (phi & _LOGICAL_KEYWORDS[op]) else 0.0


def match_semantic(phi: frozenset[str], spec: SideSpec) -> float:
    """1.0 if the side's RO or EN surface word appears in phi, else 0.0."""
    sem = spec.semantic
    return 1.0 if (sem.ro.lower() in phi or sem.en.lower() in phi) else 0.0


def side_match_score(
    phi: frozenset[str],
    spec: SideSpec,
    *,
    w_logical: float = W_L_DEFAULT,
    w_semantic: float = W_SEM_DEFAULT,
) -> float:
    """m_s per spec §8. w_logical + w_semantic should sum to 1 (not enforced, documented)."""
    return w_logical * match_logical(phi, spec.logical) + w_semantic * match_semantic(phi, spec)


def select_hex_rotation(
    text: str,
    *,
    w_logical: float = W_L_DEFAULT,
    w_semantic: float = W_SEM_DEFAULT,
) -> tuple[int, dict[int, float]]:
    """
    Deterministic hex_rotation' — **Option B (primary-side-only)** per Ethan FPF-HSR-02/14.

    For each candidate rotation ``r``, score only the primary active side ``k=0``
    (``side_active(0, r)``). The literal §5.2 full-sum over ``k=0..5`` is rotation-invariant
    (cyclic permutation) and always tied to ``r=0``; Option B is the ratified discriminating
    rewrite. Same input + same weights → same output. Ties broken by lowest ``r``.

    Provisional ADR tag ``hex_rotation_r0_interim`` is cleared when Option B is active (this
    implementation). See governance ETHAN-FPF-HSR-02-10 packet §FPF-HSR-02 Option B.
    """
    phi = input_features(text)
    scores: dict[int, float] = {}
    for r in range(6):
        # Option B: primary side only (k=0) — discriminates rotations.
        spec = side_spec(side_active(0, r))
        scores[r] = side_match_score(phi, spec, w_logical=w_logical, w_semantic=w_semantic)
    best_r = min(range(6), key=lambda r: (-scores[r], r))
    return best_r, scores


def side_specs_for_rotation(hex_rotation: int) -> tuple[SideSpec, ...]:
    """The 6 SideSpecs in active-side order (k=0..5) for a given rotation."""
    return tuple(side_spec(side_active(k, hex_rotation)) for k in range(6))
