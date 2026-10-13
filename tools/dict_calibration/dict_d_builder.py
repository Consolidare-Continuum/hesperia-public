# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""Deterministic Dict D (concept co-occurrence) builder — CORE-D2 W5.

Consumes a schema-valid ``hesperia.dict_d.resolved_corpus.v1`` export
(``resolved_export.py``) and a candidate Dict B's canonical relations, and
emits Dict D rows per the frozen W0 statistical contract
(``docs/specs/ETHAN-CORE-D2-REAL-DICT-D-PROGRAM-CONTRACT.md``):

- one event per unordered distinct-concept pair per paragraph (a concept
  winning twice in the same paragraph still counts once for that paragraph);
- ``N`` = every paragraph in the export, including zero-concept ones;
- ``NPMI = PMI / -ln(n_ij / N)``, exactly ``1.0`` at perfect co-occurrence
  (``n_ij == n_i == n_j == N``);
- ``G² = 2 * sum(O * ln(O / E))`` over non-zero observed cells of the 2×2
  contingency table, zero cells contribute 0;
- the evidence floor is a release-inclusion filter applied only after exact
  counts/marginals are complete — it never feeds back into any count;
- runtime rows carry only ``agrees``/``novel`` — ``contradicts`` is a
  review-only label from a separate authored-edge audit, never emitted here;
- two builds from byte-identical inputs produce byte-identical output.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from itertools import combinations
from pathlib import Path
from typing import Any

from .resolved_export import validate_resolved_export

DICT_D_BUILD_SCHEMA = "hesperia.dict_calibration.dict_d_build.v1"
BUILD_RULE = "dict-d-cooccurrence-build-v1"
DEFAULT_EVIDENCE_FLOOR = 5
_AGREE = frozenset({"agrees", "novel"})


class DictDBuildError(ValueError):
    """Raised on any fail-closed input/consistency violation."""


def _paragraph_concepts(paragraph: dict[str, Any]) -> frozenset[str]:
    return frozenset(
        span["winning_concept_id"] for span in paragraph["resolved_spans"]
    )


def _iter_paragraphs(resolved_export: dict[str, Any]) -> list[tuple[str, frozenset[str]]]:
    """Return ``[(book_id, concept_set), ...]``, one entry per paragraph, export order."""
    out: list[tuple[str, frozenset[str]]] = []
    for book in resolved_export["books"]:
        book_id = book["book_id"]
        for paragraph in book["paragraphs"]:
            out.append((book_id, _paragraph_concepts(paragraph)))
    return out


def _symmetric_relations(candidate_dict_b: list[dict[str, Any]]) -> dict[str, frozenset[str]]:
    """Symmetric closure of ``related_concept_ids`` keyed by ``concept_id``."""
    relations: dict[str, set[str]] = {}
    for row in candidate_dict_b:
        concept_id = row["concept_id"]
        related = row.get("related_concept_ids") or []
        relations.setdefault(concept_id, set()).update(related)
        for other in related:
            relations.setdefault(other, set()).add(concept_id)
    return {k: frozenset(v) for k, v in relations.items()}


def _npmi(n_ij: int, n_i: int, n_j: int, n_total: int) -> float:
    if n_ij == n_i == n_j == n_total:
        return 1.0
    pmi = math.log((n_ij * n_total) / (n_i * n_j))
    denom = -math.log(n_ij / n_total)
    npmi = pmi / denom
    if not math.isfinite(npmi):
        raise DictDBuildError(f"non-finite npmi for n_ij={n_ij} n_i={n_i} n_j={n_j} N={n_total}")
    if npmi < -1.0 - 1e-9 or npmi > 1.0 + 1e-9:
        raise DictDBuildError(f"npmi out of bounds: {npmi}")
    return max(-1.0, min(1.0, npmi))


def _g2(n_ij: int, n_i: int, n_j: int, n_total: int) -> float:
    o11 = n_ij
    o10 = n_i - n_ij
    o01 = n_j - n_ij
    o00 = n_total - n_i - n_j + n_ij
    for label, cell in (("o11", o11), ("o10", o10), ("o01", o01), ("o00", o00)):
        if cell < 0:
            raise DictDBuildError(f"negative contingency cell {label}={cell}")
    r1, r0 = n_i, n_total - n_i
    c1, c0 = n_j, n_total - n_j
    total = 0.0
    for observed, row_total, col_total in (
        (o11, r1, c1),
        (o10, r1, c0),
        (o01, r0, c1),
        (o00, r0, c0),
    ):
        if observed == 0:
            continue
        expected = (row_total * col_total) / n_total
        if expected <= 0:
            raise DictDBuildError("zero expected cell with nonzero observed cell")
        total += observed * math.log(observed / expected)
    g2 = 2.0 * total
    if not math.isfinite(g2):
        raise DictDBuildError(f"non-finite g2 for n_ij={n_ij} n_i={n_i} n_j={n_j} N={n_total}")
    if g2 < 0:
        if g2 < -1e-6:
            raise DictDBuildError(f"g2 computed negative beyond float tolerance: {g2}")
        g2 = 0.0
    return g2


def build_dict_d(
    *,
    resolved_export: dict[str, Any],
    candidate_dict_b: list[dict[str, Any]],
    evidence_floor: int = DEFAULT_EVIDENCE_FLOOR,
) -> dict[str, Any]:
    """Build Dict D rows + summary metadata from a validated resolved-corpus export.

    Returns ``{"rows": [...], "summary": {...}}``. Caller is responsible for
    canonicalizing/writing the rows (see :func:`write_dict_d`).
    """
    validate_resolved_export(resolved_export)
    if evidence_floor < 0:
        raise DictDBuildError("evidence_floor must be non-negative")

    paragraphs = _iter_paragraphs(resolved_export)
    n_total = len(paragraphs)
    if n_total <= 0:
        raise DictDBuildError("resolved export contains no paragraphs (N must be > 0)")

    concept_counts: dict[str, int] = {}
    pair_counts: dict[tuple[str, str], int] = {}
    pair_books: dict[tuple[str, str], set[str]] = {}

    for book_id, concepts in paragraphs:
        for concept_id in concepts:
            concept_counts[concept_id] = concept_counts.get(concept_id, 0) + 1
        for a, b in combinations(sorted(concepts), 2):
            key = (a, b)
            pair_counts[key] = pair_counts.get(key, 0) + 1
            pair_books.setdefault(key, set()).add(book_id)

    relations = _symmetric_relations(candidate_dict_b)

    rows: list[dict[str, Any]] = []
    for (a, b), n_ij in pair_counts.items():
        n_i = concept_counts[a]
        n_j = concept_counts[b]
        if n_i < n_ij or n_j < n_ij or n_i > n_total or n_j > n_total:
            raise DictDBuildError(f"marginal out of [0,N] bounds for pair ({a},{b})")
        npmi = _npmi(n_ij, n_i, n_j, n_total)
        g2 = _g2(n_ij, n_i, n_j, n_total)
        agrees = b in relations.get(a, frozenset()) or a in relations.get(b, frozenset())
        agreement = "agrees" if agrees else "novel"
        if agreement not in _AGREE:
            raise DictDBuildError(f"illegal agreement label {agreement!r}")
        rows.append(
            {
                "concept_id_a": a,
                "concept_id_b": b,
                "cooc_count": n_ij,
                "npmi": npmi,
                "g2": g2,
                "agreement_with_b": agreement,
                "source_books": sorted(pair_books[(a, b)]),
            }
        )

    rows.sort(key=lambda r: (r["concept_id_a"], r["concept_id_b"]))
    released = [r for r in rows if r["cooc_count"] >= evidence_floor]

    summary = {
        "schema": DICT_D_BUILD_SCHEMA,
        "build_rule": BUILD_RULE,
        "candidate_bundle_id": resolved_export["provenance"]["candidate_bundle_id"],
        "corpus_snapshot_sha256": resolved_export["provenance"]["corpus_snapshot_sha256"],
        "n_paragraphs": n_total,
        "n_pairs_observed": len(rows),
        "n_pairs_released": len(released),
        "evidence_floor": evidence_floor,
        "source_books": sorted({book_id for book_id, _ in paragraphs}),
    }
    return {"rows": released, "summary": summary}


def _canonical_row_bytes(row: dict[str, Any]) -> bytes:
    return (
        json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
        + "\n"
    ).encode("utf-8")


def canonical_jsonl(rows: list[dict[str, Any]]) -> bytes:
    return b"".join(_canonical_row_bytes(row) for row in rows)


def canonical_summary_bytes(summary: dict[str, Any], *, rows_sha256: str) -> bytes:
    payload = dict(summary)
    payload["rows_sha256"] = rows_sha256
    return (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
        + "\n"
    ).encode("utf-8")


def write_dict_d(built: dict[str, Any], *, rows_path: Path, summary_path: Path) -> dict[str, str]:
    """Atomically write the JSONL rows + summary sidecar. Refuses to overwrite."""
    for path in (rows_path, summary_path):
        if path.is_symlink() or path.exists():
            raise DictDBuildError(f"output destination already exists: {path}")
    rows_bytes = canonical_jsonl(built["rows"])
    rows_sha256 = hashlib.sha256(rows_bytes).hexdigest()
    summary_bytes = canonical_summary_bytes(built["summary"], rows_sha256=rows_sha256)
    _atomic_write(rows_path, rows_bytes)
    _atomic_write(summary_path, summary_bytes)
    return {"rows_sha256": rows_sha256}


def _atomic_write(path: Path, content: bytes) -> None:
    import os
    import tempfile

    parent = path.parent
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        if path.is_symlink() or path.exists():
            raise DictDBuildError(f"output destination appeared before atomic install: {path}")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build Dict D from a resolved-corpus export.")
    parser.add_argument("--resolved-export", required=True, type=Path)
    parser.add_argument("--candidate-dict-b", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--evidence-floor", type=int, default=DEFAULT_EVIDENCE_FLOOR)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    export = json.loads(args.resolved_export.read_text(encoding="utf-8"))
    dict_b = [json.loads(line) for line in args.candidate_dict_b.read_text(encoding="utf-8").splitlines() if line.strip()]
    built = build_dict_d(resolved_export=export, candidate_dict_b=dict_b, evidence_floor=args.evidence_floor)
    summary_path = args.output.with_suffix(args.output.suffix + ".meta.json")
    result = write_dict_d(built, rows_path=args.output, summary_path=summary_path)
    print(json.dumps({**built["summary"], **result}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
