# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# See LEGAL_NOTICE.md for full terms.

"""
TRIZ structural guards: read-only over ontology, topology, and lexical→matrix binding.
"""

from __future__ import annotations

from typing import Any

TRIZ_READONLY_MESSAGE = (
    "TRIZ layer is read-only over structural semantics. "
    "No mutation of ontology files, dict A/B, topology adjacency, or creation of new Areas/Families/Hexes."
)

# Meta reference areas (A6=5, A12=11): no direct lexical activation in topology mode.
META_AREA_INDICES = frozenset({5, 11})


class TrizStructuralViolation(ValueError):
    """Raised when inputs would violate TRIZ read-only or meta-area rules."""


def guard_no_meta_lexical_activation(concept_to_area: dict[str, int] | None) -> None:
    """Fail fast if any concept is placed in a meta area as lexical origin."""
    if not concept_to_area:
        return
    for cid, a in concept_to_area.items():
        if int(a) in META_AREA_INDICES:
            raise TrizStructuralViolation(
                f"{TRIZ_READONLY_MESSAGE} "
                f"No direct activation into meta areas from lexical stage (concept={cid!r}, area={a})."
            )


def guard_adjacency_immutable(adj_matrix: Any) -> None:
    """Detect accidental in-place mutation of loaded adjacency (best-effort)."""
    if hasattr(adj_matrix, "flags") and getattr(adj_matrix.flags, "writeable", True):
        try:
            adj_matrix.setflags(write=False)
        except Exception:
            pass


def assert_read_only_binding(mapping: dict[str, Any]) -> None:
    """Document-only: callers must not reassign coordinates; TRIZ only reads mapping."""


def fail_if_structural_write_attempt(operation: str) -> None:
    """Call from any code path that would mutate ontology, dict A/B, or adjacency."""
    raise TrizStructuralViolation(f"{TRIZ_READONLY_MESSAGE} Blocked operation: {operation}")
