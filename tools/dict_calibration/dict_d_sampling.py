# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""CORE-D2 W7 — seeded sample selection and source-excerpt attachment.

Implements the strata/seed/thresholds frozen in
``docs/specs/ETHAN-CORE-D2-W7-SAMPLING-STABILITY-CONTRACT.md``.
"""
from __future__ import annotations

import random
from typing import Any

SAMPLE_SEED = 20260916
SAMPLE_SIZE = 25
HIGH_NPMI_THRESHOLD = 0.3
DISAGREEMENT_NPMI_THRESHOLD = 0.0

STRATUM_HIGH_NPMI_NOVEL = "high_npmi_novel"
STRATUM_AUTHORED_EDGE_DISAGREEMENT = "authored_edge_disagreement"


def _canonical_sorted(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda r: (r["concept_id_a"], r["concept_id_b"]))


def select_high_npmi_novel(rows: list[dict[str, Any]], *, seed: int = SAMPLE_SEED, size: int = SAMPLE_SIZE) -> list[dict[str, Any]]:
    eligible = _canonical_sorted([r for r in rows if r["agreement_with_b"] == "novel" and r["npmi"] >= HIGH_NPMI_THRESHOLD])
    rng = random.Random(seed)
    return rng.sample(eligible, min(size, len(eligible)))


def select_authored_edge_disagreement(rows: list[dict[str, Any]], *, seed: int = SAMPLE_SEED, size: int = SAMPLE_SIZE) -> list[dict[str, Any]]:
    eligible = _canonical_sorted([r for r in rows if r["agreement_with_b"] == "agrees" and r["npmi"] <= DISAGREEMENT_NPMI_THRESHOLD])
    rng = random.Random(seed)
    return rng.sample(eligible, min(size, len(eligible)))


class ExcerptNotFoundError(ValueError):
    """Raised when a sampled pair has no locatable co-occurring paragraph."""


def _paragraph_concept_ids(paragraph: dict[str, Any]) -> frozenset[str]:
    return frozenset(span["winning_concept_id"] for span in paragraph["resolved_spans"])


def attach_excerpts(pairs: list[dict[str, Any]], resolved_export: dict[str, Any]) -> list[dict[str, Any]]:
    """Attach one source excerpt per sampled pair, first co-occurring paragraph in canonical order."""
    out: list[dict[str, Any]] = []
    for pair in pairs:
        a, b = pair["concept_id_a"], pair["concept_id_b"]
        found: dict[str, Any] | None = None
        for book in resolved_export["books"]:
            for paragraph in book["paragraphs"]:
                concepts = _paragraph_concept_ids(paragraph)
                if a in concepts and b in concepts:
                    found = {
                        "book_id": book["book_id"],
                        "paragraph_id": paragraph["paragraph_id"],
                        "text": paragraph["text"],
                    }
                    break
            if found:
                break
        if found is None:
            raise ExcerptNotFoundError(f"no co-occurring paragraph found for pair ({a}, {b})")
        out.append({"pair": {"concept_id_a": a, "concept_id_b": b}, **found})
    return out


def build_review_records(
    pairs: list[dict[str, Any]], resolved_export: dict[str, Any], *, stratum: str
) -> list[dict[str, Any]]:
    """Build the Colombo-role review disposition skeleton (no content judgment made here)."""
    excerpts = attach_excerpts(pairs, resolved_export)
    return [
        {
            "pair": excerpt["pair"],
            "stratum": stratum,
            "excerpt": {"book_id": excerpt["book_id"], "paragraph_id": excerpt["paragraph_id"], "text": excerpt["text"]},
            "disposition": None,
            "note": "",
        }
        for excerpt in excerpts
    ]
