# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""Dict D JSONL loader + strict row validator — CORE-D2 W6.

Supersedes the Phase A stub: fail-closed structural/numeric parsing, strict
field set (no undeclared properties), canonical pair ordering, duplicate-pair
detection, optional cross-reference against a candidate Dict B's concept IDs,
and optional cross-check of ``agreement_with_b`` against authored relations.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

REQUIRED = ("concept_id_a", "concept_id_b", "cooc_count", "npmi", "g2", "agreement_with_b", "source_books")
ALLOWED_FIELDS = frozenset(REQUIRED)
AGREE = frozenset({"agrees", "novel"})


class DictDValidationError(ValueError):
    """Raised on any fail-closed structural, numeric, or referential violation."""


def validate_dict_d_row(
    row: dict[str, Any],
    *,
    known_concept_ids: frozenset[str] | None = None,
    known_relations: dict[str, frozenset[str]] | None = None,
) -> list[str]:
    """Return a list of violation codes; empty means the row is valid.

    ``known_concept_ids``, when supplied, requires both ``concept_id_a`` and
    ``concept_id_b`` to exist in a candidate Dict B (CORE-D2-065).
    ``known_relations``, when supplied (symmetric closure keyed by
    ``concept_id``), cross-checks ``agreement_with_b`` against actually
    authored relations rather than trusting the label at face value
    (CORE-D2-066).
    """
    errs: list[str] = []
    if not isinstance(row, dict):
        return ["not_an_object"]

    extra = set(row) - ALLOWED_FIELDS
    if extra:
        errs.append(f"undeclared_fields:{sorted(extra)}")
    for k in REQUIRED:
        if k not in row:
            errs.append(f"missing:{k}")
    if errs:
        return errs

    a, b = row["concept_id_a"], row["concept_id_b"]
    if not isinstance(a, str) or not a:
        errs.append("concept_id_a_invalid")
    if not isinstance(b, str) or not b:
        errs.append("concept_id_b_invalid")
    if isinstance(a, str) and isinstance(b, str):
        if a == b:
            errs.append("concept_id_a_equals_concept_id_b")
        elif a > b:
            errs.append("pair_not_canonically_sorted")

    cooc = row["cooc_count"]
    if not isinstance(cooc, int) or isinstance(cooc, bool) or cooc < 1:
        errs.append("cooc_count_invalid")

    for field in ("npmi", "g2"):
        value = row[field]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            errs.append(f"{field}_not_finite")

    if "npmi_not_finite" not in errs:
        npmi = row["npmi"]
        if npmi < -1 or npmi > 1:
            errs.append("npmi_out_of_range")
    if "g2_not_finite" not in errs:
        if row["g2"] < 0:
            errs.append("g2_negative")

    agreement = row["agreement_with_b"]
    if agreement not in AGREE:
        errs.append("bad_agreement_with_b")

    source_books = row["source_books"]
    if (
        not isinstance(source_books, list)
        or not source_books
        or not all(isinstance(x, str) and x for x in source_books)
        or len(source_books) != len(set(source_books))
    ):
        errs.append("source_books_invalid")

    if errs:
        return errs

    if known_concept_ids is not None:
        if a not in known_concept_ids:
            errs.append("concept_id_a_unknown")
        if b not in known_concept_ids:
            errs.append("concept_id_b_unknown")

    if known_relations is not None and not errs:
        related_to_a = b in known_relations.get(a, frozenset())
        related_to_b = a in known_relations.get(b, frozenset())
        actually_related = related_to_a or related_to_b
        if agreement == "agrees" and not actually_related:
            errs.append("agreement_agrees_without_authored_relation")
        if agreement == "novel" and actually_related:
            errs.append("agreement_novel_with_authored_relation")

    return errs


def load_dict_d_jsonl(
    path: Path | str,
    *,
    known_concept_ids: frozenset[str] | None = None,
    known_relations: dict[str, frozenset[str]] | None = None,
) -> list[dict[str, Any]]:
    """Load and strictly validate a Dict D JSONL file. Fails closed on any violation.

    Rejects duplicate unordered pairs (CORE-D2-064) rather than silently
    overwriting. Rejects symlinked paths and malformed UTF-8/JSON explicitly
    rather than skipping (CORE-D2-067 fail-closed path handling).
    """
    p = Path(path)
    if p.is_symlink():
        raise DictDValidationError(f"{p}: refusing to read a symlinked Dict D path")
    if not p.is_file():
        raise DictDValidationError(f"{p}: not a regular file")

    try:
        raw = p.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise DictDValidationError(f"{p}: not valid UTF-8: {exc}") from exc

    rows: list[dict[str, Any]] = []
    seen_pairs: set[tuple[str, str]] = set()
    for i, line in enumerate(raw.splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise DictDValidationError(f"{p}:{i}: malformed JSON: {exc}") from exc
        errs = validate_dict_d_row(
            row, known_concept_ids=known_concept_ids, known_relations=known_relations
        )
        if errs:
            raise DictDValidationError(f"{p}:{i}: {errs}")
        pair = (row["concept_id_a"], row["concept_id_b"])
        if pair in seen_pairs:
            raise DictDValidationError(f"{p}:{i}: duplicate unordered pair {pair}")
        seen_pairs.add(pair)
        rows.append(row)
    return rows
