# HESPERIA — GTP-06: ThoughtImprint + ImprintDifference.
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""
Spec §10.3 (23_SPEC__) path-discovery pipeline stages:

    W (wording) -> phi -> L (logic check per side) -> I (ThoughtImprint) -> D (ImprintDifference)

ThoughtImprint: "surface record of which sides/operators fired on input wording
(minimal semantic)" — (hex, side, operators), low semantic load.
ImprintDifference: "Delta between imprint and baseline/prior step — drives path
discovery"; baseline = original Area/Family attachment of the session slice, spec §10.3.
"""

from __future__ import annotations

from dataclasses import dataclass

from sphere.topology.gtp.neighbors import HexCell
from sphere.topology.gtp.rotation import match_logical, side_specs_for_rotation
from sphere.topology.gtp.side_operators import LogicalOperator


@dataclass(frozen=True)
class ThoughtImprint:
    """(hex, side, operators) that fired on input wording. Spec §10.3."""

    hex: HexCell
    hex_rotation: int
    fired_sides: tuple[int, ...]
    fired_operators: tuple[LogicalOperator, ...]


def build_thought_imprint(h: HexCell, phi: frozenset[str], hex_rotation: int) -> ThoughtImprint:
    """L stage + I stage: which L_s fire on phi at the active sides for hex_rotation."""
    specs = side_specs_for_rotation(hex_rotation)
    fired_sides: list[int] = []
    fired_ops: list[LogicalOperator] = []
    for k, spec in enumerate(specs):
        if match_logical(phi, spec.logical) > 0.0:
            fired_sides.append(k)
            fired_ops.append(spec.logical)
    return ThoughtImprint(
        hex=h,
        hex_rotation=hex_rotation,
        fired_sides=tuple(fired_sides),
        fired_operators=tuple(fired_ops),
    )


@dataclass(frozen=True)
class ImprintDifference:
    """Delta vs original Area/Family baseline. Spec §10.3 — "anchor-only", not corpus retrieval."""

    area_shifted: bool
    family_shifted: bool
    new_fired_sides: tuple[int, ...]


def imprint_difference(
    current: ThoughtImprint,
    *,
    baseline_area_id: int,
    baseline_global_id: int,
    prior: ThoughtImprint | None = None,
) -> ImprintDifference:
    """D stage: Delta vs baseline area/family attachment, plus vs prior step's imprint if given."""
    prior_sides = frozenset(prior.fired_sides) if prior is not None else frozenset()
    new_sides = tuple(sorted(frozenset(current.fired_sides) - prior_sides))
    return ImprintDifference(
        area_shifted=current.hex.area_id != baseline_area_id,
        family_shifted=current.hex.global_id != baseline_global_id,
        new_fired_sides=new_sides,
    )
