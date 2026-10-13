# HESPERIA — GTP-01: hex side operator registry (six sides, dual operators).
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""
Freezes the closed six-side operator set from
docs/brain-export/operational/assignments/HESPERIA-FORMALIZATION-GENERAL-THOUGHT-PROPAGATION-v0_1.md
§6-7 (23_SPEC__General_Thought_Propagation_and_Hex_Orientation_v0_1).

Each of a HexCell's six sides (side_id 0..5) carries exactly one LogicalOperator
(programming/set-theoretic test) and one SemanticOperator (Romanian surface label +
English equivalent) — INV-HEX-SIDES-6, INV-LOGICAL-OPS-6, INV-SEM-OPS-6.

`fara` (without) is registered but deliberately unassigned to any side (INV-FARA-STATELESS,
§7.1) — matching a side requires an operator ADR per spec §14.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class LogicalOperator(str, Enum):
    """Set-theoretic test on input feature set F vs hex/local set H. Spec §6."""

    INCLUDES = "INCLUDES"
    NOT_INCLUDES = "NOT_INCLUDES"
    SUBSUMES = "SUBSUMES"
    OVERLAPS = "OVERLAPS"
    DISJOINT = "DISJOINT"
    EQUIVALENT = "EQUIVALENT"


def logical_test(op: LogicalOperator, feature_set: frozenset, local_set: frozenset) -> bool:
    """Evaluate L_s(F, H) per spec §6 table. Deterministic, no I/O."""
    f, h = feature_set, local_set
    if op is LogicalOperator.INCLUDES:
        return bool(f & h)
    if op is LogicalOperator.NOT_INCLUDES:
        return not (f & h)
    if op is LogicalOperator.SUBSUMES:
        # v0.1 policy: closure(F) = F (configurable closure per spec §6 note).
        return h <= f
    if op is LogicalOperator.OVERLAPS:
        return bool(f & h) and bool(f - h) and bool(h - f)
    if op is LogicalOperator.DISJOINT:
        return not (f & h)
    if op is LogicalOperator.EQUIVALENT:
        # v0.1 policy: symmetric_match(F, H) = set equality (configurable per spec §6 note).
        return f == h
    raise ValueError(f"unknown LogicalOperator: {op!r}")


@dataclass(frozen=True)
class SemanticOperator:
    """Romanian surface label + English equivalent. Spec §7."""

    id: str
    ro: str
    en: str
    stateless: bool = False
    side_id: int | None = None


@dataclass(frozen=True)
class SideSpec:
    """Dual operator bound to one side. Spec §6-7 combined (`SideSpec`, §8)."""

    side_id: int
    logical: LogicalOperator
    semantic: SemanticOperator


# Frozen registry, side_id 0..5 — do not reorder or resize without an operator ADR
# (spec §14: "Change INV-LOGICAL-OPS-6 set requires ADR + migration").
SIDE_SPECS: tuple[SideSpec, ...] = (
    SideSpec(0, LogicalOperator.INCLUDES, SemanticOperator("cu", "cu", "with", side_id=0)),
    SideSpec(1, LogicalOperator.NOT_INCLUDES, SemanticOperator("din", "din", "from", side_id=1)),
    SideSpec(2, LogicalOperator.SUBSUMES, SemanticOperator("la", "la", "at", side_id=2)),
    SideSpec(3, LogicalOperator.OVERLAPS, SemanticOperator("spre", "spre", "toward", side_id=3)),
    SideSpec(4, LogicalOperator.DISJOINT, SemanticOperator("dupa", "dupa", "after", side_id=4)),
    SideSpec(5, LogicalOperator.EQUIVALENT, SemanticOperator("pentru", "pentru", "for", side_id=5)),
)

# Reserved, unassigned — INV-FARA-STATELESS (spec §7.1).
FARA = SemanticOperator("FARA", "fara", "without", stateless=True, side_id=None)

_BY_SIDE_ID: dict[int, SideSpec] = {spec.side_id: spec for spec in SIDE_SPECS}


def side_spec(side_id: int) -> SideSpec:
    """Look up the frozen SideSpec for side_id in {0,...,5}."""
    if side_id not in _BY_SIDE_ID:
        raise ValueError(f"side_id out of range 0..5: {side_id!r}")
    return _BY_SIDE_ID[side_id]


def validate_registry() -> None:
    """INV-HEX-SIDES-6 / INV-LOGICAL-OPS-6 / INV-SEM-OPS-6 self-check."""
    if len(SIDE_SPECS) != 6:
        raise AssertionError("INV-HEX-SIDES-6 violated: expected exactly 6 sides")
    side_ids = {spec.side_id for spec in SIDE_SPECS}
    if side_ids != set(range(6)):
        raise AssertionError("INV-HEX-SIDES-6 violated: side_id set must be 0..5")
    logical_ops = {spec.logical for spec in SIDE_SPECS}
    if len(logical_ops) != 6:
        raise AssertionError("INV-LOGICAL-OPS-6 violated: operators must be distinct")
    semantic_ids = {spec.semantic.id for spec in SIDE_SPECS}
    if len(semantic_ids) != 6:
        raise AssertionError("INV-SEM-OPS-6 violated: semantic operators must be distinct")
    if FARA.side_id is not None or not FARA.stateless:
        raise AssertionError("INV-FARA-STATELESS violated: fara must stay unassigned")
