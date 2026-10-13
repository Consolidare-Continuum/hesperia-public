# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""CLI contract for the CORE-D2 paragraph-resolved corpus exporter."""

from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import math
import os
import re
import stat
import subprocess
import tempfile
import unicodedata
from collections.abc import Callable
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path, PurePosixPath
from types import CodeType
from typing import Any

from core.engine.lexical_concept.pipeline import run_dlcr_pipeline
from core.dynamics.constants import load_engine_constants
from core.lexical.policy import clear_dlcr_policy_cache
from hesperia.engine.engine_signal_calibration import load_engine_signal_calibration

from . import repo_root
from .evaluate import (
    _read_bundle,
    _validate_candidate_artifacts,
    _write_bundle_anchors,
)
from .generation_ledger import load_generation_ledger


RESOLVED_CORPUS_SCHEMA = "hesperia.dict_d.resolved_corpus.v1"
EXPORT_RULE = "resolved-corpus-export-v1"
DICT_D_EXPORT_WEIGHT = 0.0
CANONICAL_RESOLVER_AUTHORITY = "canonical-run-dlcr-pipeline"
TEST_RESOLVER_AUTHORITY = "private-test-runner"
SUPPORTED_SOURCE_SUFFIXES = frozenset({".md", ".txt"})
Runner = Callable[..., dict[str, Any]]
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_RESOLVER_SEMANTIC_SOURCE_PATHS = (
    "core/engine/lexical_concept/pipeline.py",
    "core/lexical/analysis_input.py",
    "core/lexical/matcher.py",
    "core/lexical/normalization.py",
    "core/pipeline/lexical.py",
    "core/resolver/context.py",
    "core/resolver/resolver.py",
    "core/resolver/score_rules.py",
)
_PINNED_PIPELINE_ENV = {
    "HESPERIA_DICT_A_CONFIDENCE_THRESHOLD": "0.35",
    "HESPERIA_DICT_A_MAX_ACCEPTED": "",
    "HESPERIA_DICT_A_MAX_SYNONYMS_PER_CONCEPT": "24",
    "HESPERIA_DLCR_DEBUG_TOKEN_WEIGHTS": "0",
    "HESPERIA_DLCR_DOMAIN_PACK": "default",
    "HESPERIA_DLCR_DOMAIN_WHITELIST": "",
    "HESPERIA_DLCR_MIN_RESOLVE_SCORE": "0.5",
    "HESPERIA_DLCR_MIN_TOKEN_LEN": "2",
    "HESPERIA_DLCR_REJECT_TINY_FRAGMENTS": "0",
    "HESPERIA_DLCR_STOPWORDS": "",
    "HESPERIA_DLCR_TOKEN_TOPK": "3",
    "HESPERIA_CD_DISABLE": "1",
    "HESPERIA_CD_ENABLED": "0",
    "HESPERIA_CD_JSONL": "",
    "HESPERIA_CD_PHASE": "1",
}

_TOP_LEVEL_FIELDS = frozenset({"schema", "provenance", "books", "unresolved"})
_PROVENANCE_FIELDS = frozenset(
    {
        "candidate_bundle_id",
        "candidate_manifest_sha256",
        "corpus_snapshot_sha256",
        "resolver_version",
        "resolver_implementation_sha256",
        "resolver_authority",
        "resolver_configuration_sha256",
        "segmentation_rule",
        "export_rule",
        "dict_d_enabled",
        "dict_d_effective_weight",
    }
)
_BOOK_FIELDS = frozenset(
    {"book_id", "source_path", "source_sha256", "paragraphs"}
)
_PARAGRAPH_FIELDS = frozenset(
    {"paragraph_id", "source_ordinal", "text", "resolved_spans"}
)
_RESOLVED_SPAN_FIELDS = frozenset(
    {
        "span_position",
        "span_end",
        "surface",
        "winning_concept_id",
        "candidate_scores",
    }
)
_UNRESOLVED_FIELDS = frozenset(
    {
        "book_id",
        "paragraph_id",
        "span_position",
        "span_end",
        "surface",
        "reason_codes",
        "candidate_scores",
    }
)
_CANDIDATE_FIELDS = frozenset({"concept_id", "score"})
_CANDIDATE_REJECTED_PREFIX = "candidate_rejected:"
_UNRESOLVED_REASON_CODES = frozenset({"below_threshold", "no_candidates"})


def _require_fields(value: Any, expected: frozenset[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError(f"{label} fields must be exactly {sorted(expected)}")
    return value


def _require_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be non-empty text")
    return value


def _require_sha256(value: Any, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.casefold()
    ):
        raise ValueError(f"{label} must be a lowercase SHA-256 digest")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ValueError(f"{label} must be a lowercase SHA-256 digest") from exc
    return value


def _require_nonnegative_int(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")
    return value


def _validate_candidate_scores(value: Any, label: str) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be a list")
    concept_ids: list[str] = []
    for index, raw_candidate in enumerate(value):
        candidate = _require_fields(
            raw_candidate, _CANDIDATE_FIELDS, f"{label}[{index}]"
        )
        concept_id = _require_text(
            candidate["concept_id"], f"{label}[{index}].concept_id"
        )
        score = candidate["score"]
        if (
            not isinstance(score, (int, float))
            or isinstance(score, bool)
            or (isinstance(score, float) and not math.isfinite(score))
        ):
            raise ValueError(f"{label}[{index}].score must be finite")
        concept_ids.append(concept_id)
    if len(concept_ids) != len(set(concept_ids)):
        raise ValueError(f"{label} contains a duplicate candidate")
    if concept_ids != sorted(concept_ids):
        raise ValueError(f"{label} candidate order must be canonical")
    return value


def _validate_reason_codes(
    value: Any,
    label: str,
    *,
    require_canonical_order: bool = False,
) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{label} must be a non-empty list")
    if any(
        not isinstance(reason, str)
        or (
            reason not in _UNRESOLVED_REASON_CODES
            and not (
                reason.startswith(_CANDIDATE_REJECTED_PREFIX)
                and len(reason) > len(_CANDIDATE_REJECTED_PREFIX)
            )
        )
        for reason in value
    ):
        raise ValueError(f"{label} contains an unknown reason code")
    if len(value) != len(set(value)):
        raise ValueError(f"{label} contains a duplicate reason code")
    ordered = sorted(value)
    if require_canonical_order and value != ordered:
        raise ValueError(f"{label} reason code order must be canonical")
    return ordered


def _validate_unresolved_reason_semantics(
    reason_codes: list[str],
    candidate_scores: list[dict[str, Any]],
    label: str,
) -> None:
    reasons = set(reason_codes)
    candidate_ids = {
        candidate["concept_id"] for candidate in candidate_scores
    }
    rejected_ids = {
        reason.removeprefix(_CANDIDATE_REJECTED_PREFIX)
        for reason in reason_codes
        if reason.startswith(_CANDIDATE_REJECTED_PREFIX)
    }
    if not candidate_scores:
        if reasons != {"no_candidates"}:
            raise ValueError(
                f"{label}.reason_codes must be exactly ['no_candidates'] "
                "when candidate_scores is empty"
            )
        return

    threshold = float(_PINNED_PIPELINE_ENV["HESPERIA_DLCR_MIN_RESOLVE_SCORE"])
    best_score = max(
        float(candidate["score"]) for candidate in candidate_scores
    )
    if best_score >= threshold or "below_threshold" not in reasons:
        raise ValueError(
            f"{label}.reason_codes must truthfully record below_threshold"
        )
    if "no_candidates" in reasons:
        raise ValueError(
            f"{label}.reason_codes cannot contain no_candidates with scores"
        )
    if not rejected_ids.issubset(candidate_ids):
        raise ValueError(
            f"{label}.reason_codes candidate_rejected id is absent from scores"
        )


def _validate_span_bounds(
    record: dict[str, Any], text: str, label: str
) -> tuple[int, int]:
    start = _require_nonnegative_int(record["span_position"], f"{label}.span_position")
    end = _require_nonnegative_int(record["span_end"], f"{label}.span_end")
    surface = _require_text(record["surface"], f"{label}.surface")
    if end <= start or end > len(text) or text[start:end] != surface:
        raise ValueError(f"{label} span is outside or inconsistent with paragraph text")
    return start, end


def _paragraph_identity(book_sha256: str, ordinal: int, text: str) -> str:
    raw_identity = f"{book_sha256}\0{ordinal}\0{text}".encode("utf-8")
    return hashlib.sha256(raw_identity).hexdigest()


def _segment_paragraphs(raw_text: str) -> list[str]:
    normalized = raw_text.replace("\r\n", "\n").replace("\r", "\n")
    paragraphs: list[str] = []
    current_lines: list[str] = []
    for line in normalized.split("\n"):
        if line.strip():
            current_lines.append(line)
        elif current_lines:
            paragraphs.append("\n".join(current_lines))
            current_lines = []
    if current_lines:
        paragraphs.append("\n".join(current_lines))
    return paragraphs


def _canonical_alignment(text: str) -> tuple[str, list[tuple[int, int]]]:
    normalized = ""
    ranges: list[tuple[int, int]] = []
    for source_end in range(1, len(text) + 1):
        updated = unicodedata.normalize("NFKC", text[:source_end])
        common_prefix = 0
        while (
            common_prefix < len(normalized)
            and common_prefix < len(updated)
            and normalized[common_prefix] == updated[common_prefix]
        ):
            common_prefix += 1
        source_start = (
            min(start for start, _ in ranges[common_prefix:])
            if common_prefix < len(ranges)
            else source_end - 1
        )
        ranges = ranges[:common_prefix] + [
            (source_start, source_end)
        ] * (len(updated) - common_prefix)
        normalized = updated

    folded_chars: list[str] = []
    folded_ranges: list[tuple[int, int]] = []
    for character, source_range in zip(normalized, ranges, strict=True):
        folded = (
            character.replace("\u2019", "'")
            .replace("\u2018", "'")
            .casefold()
        )
        folded_chars.extend(folded)
        folded_ranges.extend([source_range] * len(folded))

    canonical_chars: list[str] = []
    canonical_ranges: list[tuple[int, int]] = []
    pending_whitespace: list[tuple[int, int]] = []
    for character, source_range in zip(
        folded_chars, folded_ranges, strict=True
    ):
        if re.fullmatch(r"\s", character):
            pending_whitespace.append(source_range)
            continue
        if pending_whitespace and canonical_chars:
            canonical_chars.append(" ")
            canonical_ranges.append(
                (
                    min(start for start, _ in pending_whitespace),
                    max(end for _, end in pending_whitespace),
                )
            )
        pending_whitespace = []
        canonical_chars.append(character)
        canonical_ranges.append(source_range)
    return "".join(canonical_chars), canonical_ranges


def _translate_canonical_span(
    raw_span: Any,
    canonical_text: str,
    canonical_ranges: list[tuple[int, int]],
    paragraph_text: str,
    label: str,
) -> dict[str, Any]:
    if not isinstance(raw_span, dict):
        raise ValueError(f"{label} must be an object")
    start = raw_span.get("source_char_start")
    end = raw_span.get("source_char_end")
    surface = raw_span.get("source_text_span")
    if (
        not isinstance(start, int)
        or isinstance(start, bool)
        or not isinstance(end, int)
        or isinstance(end, bool)
        or start < 0
        or end <= start
        or end > len(canonical_text)
        or surface != canonical_text[start:end]
    ):
        raise ValueError(f"{label} canonical source offsets are invalid")
    if (
        (start > 0 and canonical_ranges[start - 1][1] > canonical_ranges[start][0])
        or (
            end < len(canonical_ranges)
            and canonical_ranges[end - 1][1] > canonical_ranges[end][0]
        )
    ):
        raise ValueError(f"{label} has ambiguous canonical span boundaries")

    source_start = canonical_ranges[start][0]
    source_end = canonical_ranges[end - 1][1]
    source_surface = paragraph_text[source_start:source_end]
    aligned_surface, _ = _canonical_alignment(source_surface)
    if aligned_surface != canonical_text[start:end]:
        raise ValueError(f"{label} has ambiguous canonical span alignment")
    return {
        **raw_span,
        "source_char_start": source_start,
        "source_char_end": source_end,
        "source_text_span": source_surface,
    }


def _validate_provenance(
    raw_provenance: Any,
    *,
    allow_test_authority: bool,
) -> None:
    provenance = _require_fields(
        raw_provenance, _PROVENANCE_FIELDS, "provenance"
    )
    for key in (
        "candidate_bundle_id",
        "candidate_manifest_sha256",
        "corpus_snapshot_sha256",
        "resolver_implementation_sha256",
        "resolver_configuration_sha256",
    ):
        _require_sha256(provenance[key], f"provenance.{key}")
    for key in (
        "resolver_version",
        "resolver_authority",
        "segmentation_rule",
        "export_rule",
    ):
        _require_text(provenance[key], f"provenance.{key}")
    if provenance["resolver_authority"] not in {
        CANONICAL_RESOLVER_AUTHORITY,
        TEST_RESOLVER_AUTHORITY,
    }:
        raise ValueError("provenance.resolver_authority is unknown")
    if (
        provenance["resolver_authority"] != CANONICAL_RESOLVER_AUTHORITY
        and not allow_test_authority
    ):
        raise ValueError(
            "provenance.resolver_authority must be canonical resolver authority"
        )
    if provenance["dict_d_enabled"] is not False:
        raise ValueError("provenance.dict_d_enabled must be false")
    weight = provenance["dict_d_effective_weight"]
    if (
        not isinstance(weight, (int, float))
        or isinstance(weight, bool)
        or (isinstance(weight, float) and not math.isfinite(weight))
        or weight != 0
    ):
        raise ValueError("provenance.dict_d_effective_weight must be finite zero")


def _validate_source_path(value: Any) -> str:
    path_text = _require_text(value, "book.source_path")
    path = PurePosixPath(path_text)
    if (
        path.is_absolute()
        or path_text != path.as_posix()
        or path_text.startswith("./")
        or "\\" in path_text
        or ".." in path.parts
        or "." in path.parts
    ):
        raise ValueError("book.source_path must be a safe canonical relative path")
    return path_text


def _validate_resolved_spans(
    raw_spans: Any, text: str, paragraph_label: str
) -> None:
    if not isinstance(raw_spans, list):
        raise ValueError(f"{paragraph_label}.resolved_spans must be a list")
    identities: list[tuple[int, int]] = []
    order: list[tuple[int, int, str]] = []
    for index, raw_span in enumerate(raw_spans):
        label = f"{paragraph_label}.resolved_spans[{index}]"
        span = _require_fields(raw_span, _RESOLVED_SPAN_FIELDS, label)
        start, end = _validate_span_bounds(span, text, label)
        winner = _require_text(
            span["winning_concept_id"], f"{label}.winning_concept_id"
        )
        scores = _validate_candidate_scores(
            span["candidate_scores"], f"{label}.candidate_scores"
        )
        if winner not in {candidate["concept_id"] for candidate in scores}:
            raise ValueError(f"{label}.winning_concept_id is absent from candidate_scores")
        identities.append((start, end))
        order.append((start, end, winner))
    if len(identities) != len(set(identities)):
        raise ValueError(f"{paragraph_label} contains a duplicate resolved span")
    if order != sorted(order):
        raise ValueError(f"{paragraph_label} resolved span order is not canonical")


def _validate_books(
    raw_books: Any,
) -> tuple[dict[str, tuple[int, dict[str, Any]]], list[str]]:
    if not isinstance(raw_books, list) or not raw_books:
        raise ValueError("books must be a non-empty list")
    book_ids: set[str] = set()
    ordered_book_ids: list[str] = []
    source_paths: set[str] = set()
    paragraph_ids: set[str] = set()
    paragraph_index: dict[str, tuple[int, dict[str, Any]]] = {}
    ordered_paths: list[str] = []
    for book_index, raw_book in enumerate(raw_books):
        book = _require_fields(raw_book, _BOOK_FIELDS, f"books[{book_index}]")
        book_id = _require_text(book["book_id"], f"books[{book_index}].book_id")
        source_path = _validate_source_path(book["source_path"])
        source_sha256 = _require_sha256(
            book["source_sha256"], f"books[{book_index}].source_sha256"
        )
        if book_id in book_ids or source_path in source_paths:
            raise ValueError("books contains a duplicate book identity")
        book_ids.add(book_id)
        ordered_book_ids.append(book_id)
        source_paths.add(source_path)
        ordered_paths.append(source_path)

        paragraphs = book["paragraphs"]
        if not isinstance(paragraphs, list):
            raise ValueError(f"books[{book_index}].paragraphs must be a list")
        ordinals: list[int] = []
        for paragraph_index_in_book, raw_paragraph in enumerate(paragraphs):
            label = f"books[{book_index}].paragraphs[{paragraph_index_in_book}]"
            paragraph = _require_fields(raw_paragraph, _PARAGRAPH_FIELDS, label)
            paragraph_id = _require_sha256(
                paragraph["paragraph_id"], f"{label}.paragraph_id"
            )
            ordinal = _require_nonnegative_int(
                paragraph["source_ordinal"], f"{label}.source_ordinal"
            )
            text = _require_text(paragraph["text"], f"{label}.text")
            if paragraph_id in paragraph_ids:
                raise ValueError("books contains a duplicate paragraph identity")
            paragraph_ids.add(paragraph_id)
            expected_id = _paragraph_identity(source_sha256, ordinal, text)
            if paragraph_id != expected_id:
                raise ValueError(f"{label}.paragraph_id does not match frozen identity")
            _validate_resolved_spans(paragraph["resolved_spans"], text, label)
            ordinals.append(ordinal)
            paragraph_index[paragraph_id] = (book_index, paragraph)
        if ordinals != list(range(len(ordinals))):
            raise ValueError(f"books[{book_index}] source_ordinal order is not canonical")
    if ordered_paths != sorted(ordered_paths):
        raise ValueError("books source_path order is not canonical")
    return paragraph_index, ordered_book_ids


def _validate_unresolved(
    raw_unresolved: Any,
    paragraph_index: dict[str, tuple[int, dict[str, Any]]],
    book_ids: list[str],
) -> None:
    if not isinstance(raw_unresolved, list):
        raise ValueError("unresolved must be a list")
    valid_book_ids = set(book_ids)
    identities: list[tuple[str, str, int, int]] = []
    order: list[tuple[int, int, int, int]] = []
    for index, raw_record in enumerate(raw_unresolved):
        label = f"unresolved[{index}]"
        record = _require_fields(raw_record, _UNRESOLVED_FIELDS, label)
        book_id = _require_text(record["book_id"], f"{label}.book_id")
        paragraph_id = _require_sha256(
            record["paragraph_id"], f"{label}.paragraph_id"
        )
        if book_id not in valid_book_ids or paragraph_id not in paragraph_index:
            raise ValueError(f"{label}.paragraph_id or book_id is unknown")
        book_index, paragraph = paragraph_index[paragraph_id]
        if book_ids[book_index] != book_id:
            raise ValueError(f"{label}.paragraph_id does not belong to book_id")
        start, end = _validate_span_bounds(record, paragraph["text"], label)
        if any(
            start < resolved["span_end"]
            and resolved["span_position"] < end
            for resolved in paragraph["resolved_spans"]
        ):
            raise ValueError(f"{label} has resolved/unresolved overlap")
        reason_codes = _validate_reason_codes(
            record["reason_codes"],
            f"{label}.reason_codes",
            require_canonical_order=True,
        )
        candidate_scores = _validate_candidate_scores(
            record["candidate_scores"], f"{label}.candidate_scores"
        )
        _validate_unresolved_reason_semantics(
            reason_codes,
            candidate_scores,
            label,
        )
        identities.append((book_id, paragraph_id, start, end))
        order.append((book_index, paragraph["source_ordinal"], start, end))
    if len(identities) != len(set(identities)):
        raise ValueError("unresolved contains a duplicate unresolved record")
    if order != sorted(order):
        raise ValueError("unresolved order is not canonical")


def _validate_resolved_export(
    value: Any,
    *,
    allow_test_authority: bool,
) -> None:
    """Private structural validator with an explicit test-authority seam."""
    export = _require_fields(value, _TOP_LEVEL_FIELDS, "resolved export")
    if export["schema"] != RESOLVED_CORPUS_SCHEMA:
        raise ValueError(f"schema must be {RESOLVED_CORPUS_SCHEMA}")
    _validate_provenance(
        export["provenance"],
        allow_test_authority=allow_test_authority,
    )
    paragraph_index, book_ids = _validate_books(export["books"])
    _validate_unresolved(export["unresolved"], paragraph_index, book_ids)


def validate_resolved_export(value: Any) -> None:
    """Validate one release export; private test authority is forbidden."""
    _validate_resolved_export(value, allow_test_authority=False)


def _canonical_score(value: int | float) -> int | float:
    if isinstance(value, int):
        return value
    if value == 0.0 or value.is_integer():
        return int(value)
    return value


def _canonicalize_resolved_export(
    value: Any,
    *,
    allow_test_authority: bool,
) -> bytes:
    """Private canonicalizer with an explicit test-authority seam."""
    _validate_resolved_export(
        value,
        allow_test_authority=allow_test_authority,
    )
    canonical = deepcopy(value)
    canonical["provenance"]["dict_d_effective_weight"] = 0.0
    for book in canonical["books"]:
        for paragraph in book["paragraphs"]:
            for span in paragraph["resolved_spans"]:
                for candidate in span["candidate_scores"]:
                    candidate["score"] = _canonical_score(candidate["score"])
    for unresolved in canonical["unresolved"]:
        for candidate in unresolved["candidate_scores"]:
            candidate["score"] = _canonical_score(candidate["score"])
    return (
        json.dumps(
            canonical,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def canonicalize_resolved_export(value: Any) -> bytes:
    """Return canonical bytes for a release-valid resolved export."""
    return _canonicalize_resolved_export(
        value,
        allow_test_authority=False,
    )


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _git_snapshot() -> tuple[str, bool]:
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=_PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=_PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return commit, not bool(status)


def _candidate_scores(raw_scores: Any, label: str) -> list[dict[str, Any]]:
    if not isinstance(raw_scores, dict):
        raise ValueError(f"{label}.candidate_scores must be an object")
    return [
        {"concept_id": concept_id, "score": score}
        for concept_id, score in sorted(raw_scores.items())
    ]


def _absolute(path: Path) -> Path:
    return Path(os.path.abspath(path))


def _identity(path_stat: os.stat_result, *, include_times: bool) -> tuple[int, ...]:
    identity = (
        path_stat.st_dev,
        path_stat.st_ino,
        path_stat.st_mode,
        path_stat.st_size,
    )
    if include_times:
        return identity + (path_stat.st_mtime_ns, path_stat.st_ctime_ns)
    return identity


def _source_ancestor_identity(path: Path) -> tuple[int, ...]:
    try:
        ancestor_stat = path.lstat()
    except OSError as exc:
        raise ValueError(
            f"source ancestor cannot be inspected: {path}: {exc}"
        ) from exc
    if stat.S_ISLNK(ancestor_stat.st_mode):
        raise ValueError(f"source ancestor must not be a symlink: {path}")
    if not stat.S_ISDIR(ancestor_stat.st_mode):
        raise ValueError(f"source ancestor must be a directory: {path}")
    return _identity(ancestor_stat, include_times=False)


def _source_ancestor_identities(path: Path) -> dict[Path, tuple[int, ...]]:
    return {
        ancestor: _source_ancestor_identity(ancestor)
        for ancestor in reversed(path.parents)
    }


def _directory_identity(path: Path) -> tuple[int, ...]:
    try:
        directory_stat = path.lstat()
    except OSError as exc:
        raise ValueError(f"source directory cannot be inspected: {path}: {exc}") from exc
    if stat.S_ISLNK(directory_stat.st_mode):
        raise ValueError(f"source directory must not be a symlink: {path}")
    if not stat.S_ISDIR(directory_stat.st_mode):
        raise ValueError(f"source directory must remain a directory: {path}")
    if not os.access(path, os.R_OK | os.X_OK):
        raise ValueError(f"source directory must be readable and searchable: {path}")
    return _identity(directory_stat, include_times=True)


def _source_file_identity(path: Path) -> tuple[int, ...]:
    try:
        source_stat = path.lstat()
    except OSError as exc:
        raise ValueError(f"source file cannot be inspected: {path}: {exc}") from exc
    if stat.S_ISLNK(source_stat.st_mode):
        raise ValueError(f"source file must not be a symlink: {path}")
    if not stat.S_ISREG(source_stat.st_mode):
        raise ValueError(f"source file must be regular: {path}")
    return _identity(source_stat, include_times=True)


def _raise_walk_error(error: OSError) -> None:
    raise ValueError(f"source traversal failed: {error}") from error


def _assert_discovery_stable(discovery: dict[str, Any], phase: str) -> None:
    for path, expected in discovery["ancestors"].items():
        if _source_ancestor_identity(path) != expected:
            raise ValueError(f"source ancestor identity changed during {phase}: {path}")
    for path, expected in discovery["roots"].items():
        current = (
            _directory_identity(path)
            if stat.S_ISDIR(expected[2])
            else _source_file_identity(path)
        )
        if current != expected:
            raise ValueError(f"source root identity changed during {phase}: {path}")
    for path, expected in discovery["directories"].items():
        if _directory_identity(path) != expected:
            raise ValueError(f"source directory identity changed during {phase}: {path}")
    for source in discovery["sources"]:
        if _source_file_identity(source["path"]) != source["identity"]:
            raise ValueError(
                f"source file identity changed during {phase}: {source['path']}"
            )


def _discover_sources(corpus_roots: list[Path]) -> dict[str, Any]:
    roots: list[tuple[Path, bool]] = []
    root_identities: dict[Path, tuple[int, ...]] = {}
    ancestor_identities: dict[Path, tuple[int, ...]] = {}
    for raw_root in corpus_roots:
        root = _absolute(raw_root)
        for path, identity in _source_ancestor_identities(root).items():
            previous = ancestor_identities.setdefault(path, identity)
            if previous != identity:
                raise ValueError(f"source ancestor identity changed: {path}")
        try:
            root_stat = root.lstat()
        except OSError as exc:
            raise ValueError(f"source root cannot be inspected: {raw_root}: {exc}") from exc
        if stat.S_ISLNK(root_stat.st_mode):
            raise ValueError(f"source root must not be a symlink: {raw_root}")
        if stat.S_ISDIR(root_stat.st_mode):
            roots.append((root, True))
        elif stat.S_ISREG(root_stat.st_mode):
            if root.suffix.casefold() not in SUPPORTED_SOURCE_SUFFIXES:
                raise ValueError(f"unsupported source file: {raw_root}")
            roots.append((root, False))
        else:
            raise ValueError(f"source root must be a regular file or directory: {raw_root}")
        root_identity = _identity(root_stat, include_times=True)
        previous_root_identity = root_identities.setdefault(root, root_identity)
        if previous_root_identity != root_identity:
            raise ValueError(f"source root identity changed: {root}")

    unique_roots = sorted(
        set(roots),
        key=lambda item: (item[0].as_posix(), not item[1]),
    )
    identity_roots = [
        root if is_directory else root.parent
        for root, is_directory in unique_roots
    ]
    source_root = Path(os.path.commonpath(identity_roots))
    discovered: dict[Path, dict[str, Any]] = {}
    directory_identities: dict[Path, tuple[int, ...]] = {}

    for root, is_directory in unique_roots:
        if not is_directory:
            candidates = [root]
        else:
            candidates = []
            root_identity = _directory_identity(root)
            previous_root = directory_identities.setdefault(root, root_identity)
            if previous_root != root_identity:
                raise ValueError(f"source directory identity changed: {root}")
            for directory, directory_names, file_names in os.walk(
                root,
                topdown=True,
                onerror=_raise_walk_error,
                followlinks=False,
            ):
                directory_path = Path(directory)
                directory_identity = _directory_identity(directory_path)
                previous_directory = directory_identities.setdefault(
                    directory_path,
                    directory_identity,
                )
                if previous_directory != directory_identity:
                    raise ValueError(
                        f"source directory identity changed during traversal: "
                        f"{directory_path}"
                    )
                for name in directory_names:
                    child = directory_path / name
                    if child.is_symlink():
                        raise ValueError(
                            f"source directory must not be a symlink: {child}"
                        )
                directory_names.sort()
                for name in sorted(file_names):
                    child = directory_path / name
                    if child.suffix.casefold() in SUPPORTED_SOURCE_SUFFIXES:
                        _source_file_identity(child)
                        candidates.append(child)

        for candidate in candidates:
            resolved_path = candidate.resolve(strict=True)
            source_path = candidate.relative_to(source_root).as_posix()
            record = {
                "path": candidate,
                "resolved_path": resolved_path,
                "source_path": source_path,
                "identity": _source_file_identity(candidate),
            }
            previous = discovered.setdefault(resolved_path, record)
            if source_path < previous["source_path"]:
                discovered[resolved_path] = record

    sources = sorted(discovered.values(), key=lambda item: item["source_path"])
    if not sources:
        raise ValueError("source_files must discover at least one supported text file")
    discovery = {
        "corpus_roots": [root for root, _is_directory in unique_roots],
        "ancestors": ancestor_identities,
        "roots": root_identities,
        "directories": directory_identities,
        "sources": sources,
    }
    _assert_discovery_stable(discovery, "traversal")
    return discovery


def _assert_corpus_unchanged(discovery: dict[str, Any]) -> None:
    try:
        current = _discover_sources(discovery["corpus_roots"])
    except (OSError, ValueError) as exc:
        raise ValueError(
            f"source membership or identity changed during resolved export: {exc}"
        ) from exc
    expected_membership = [
        (source["source_path"], source["path"], source["resolved_path"])
        for source in discovery["sources"]
    ]
    current_membership = [
        (source["source_path"], source["path"], source["resolved_path"])
        for source in current["sources"]
    ]
    if current_membership != expected_membership:
        raise ValueError("source membership changed during resolved export")
    if current["ancestors"] != discovery["ancestors"]:
        raise ValueError("source ancestor identity changed during resolved export")
    if current["roots"] != discovery["roots"]:
        raise ValueError("source root identity changed during resolved export")
    if current["directories"] != discovery["directories"]:
        raise ValueError("source directory identity changed during resolved export")
    if [
        source["identity"] for source in current["sources"]
    ] != [
        source["identity"] for source in discovery["sources"]
    ]:
        raise ValueError("source file identity changed during resolved export")


def _snapshot_bundle(
    bundle_dir: Path,
    manifest: dict[str, Any],
    manifest_bytes: bytes,
) -> dict[str, bytes]:
    snapshot = {"manifest.json": manifest_bytes}
    sidecar_path = bundle_dir / "manifest.json.sha256"
    if sidecar_path.is_symlink() or not sidecar_path.is_file():
        raise ValueError("bundle identity file manifest.json.sha256 must be regular")
    snapshot["manifest.json.sha256"] = sidecar_path.read_bytes()
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, dict) or not artifacts:
        raise ValueError("bundle artifacts are missing")
    for role, descriptor in artifacts.items():
        if not isinstance(descriptor, dict):
            raise ValueError(f"bundle artifact {role} descriptor is invalid")
        raw_path = descriptor.get("path")
        if not isinstance(raw_path, str) or not raw_path:
            raise ValueError(f"bundle artifact {role} path is missing")
        relative = Path(raw_path)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"bundle artifact {role} path is unsafe")
        artifact_path = bundle_dir / relative
        try:
            artifact_path.resolve(strict=True).relative_to(bundle_dir.resolve(strict=True))
        except (FileNotFoundError, ValueError) as exc:
            raise ValueError(f"bundle artifact {role} escapes or is missing") from exc
        if artifact_path.is_symlink() or not artifact_path.is_file():
            raise ValueError(f"bundle artifact {role} must be a regular file")
        artifact_bytes = artifact_path.read_bytes()
        if descriptor.get("sha256") != _sha256_bytes(artifact_bytes):
            raise ValueError(f"bundle artifact {role} hash does not match bytes")
        previous = snapshot.setdefault(relative.as_posix(), artifact_bytes)
        if previous != artifact_bytes:
            raise ValueError(f"bundle artifact path aliases different bytes: {role}")
    manifest_path = bundle_dir / "manifest.json"
    if (
        manifest_path.is_symlink()
        or not manifest_path.is_file()
        or manifest_path.read_bytes() != manifest_bytes
    ):
        raise ValueError("bundle manifest changed while snapshotting generation")
    return snapshot


def _load_stable_bundle_generation(
    bundle_dir: Path,
    *,
    require_manifest_v2: bool = False,
) -> tuple[dict[str, Any], dict[str, Any], bytes, dict[str, bytes]]:
    manifest_path = bundle_dir / "manifest.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ValueError("bundle manifest must be a regular file")
    before_bytes = manifest_path.read_bytes()
    before_manifest = json.loads(before_bytes)
    if not isinstance(before_manifest, dict):
        raise ValueError("bundle manifest schema requires an object")
    before_snapshot = _snapshot_bundle(
        bundle_dir,
        before_manifest,
        before_bytes,
    )

    bundle = (
        _read_bundle(bundle_dir, require_manifest_v2=True)
        if require_manifest_v2
        else _read_bundle(bundle_dir)
    )
    _validate_candidate_artifacts(bundle)

    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ValueError("bundle manifest changed during generation read")
    after_bytes = manifest_path.read_bytes()
    after_manifest = json.loads(after_bytes)
    if not isinstance(after_manifest, dict):
        raise ValueError("bundle manifest schema requires an object")
    after_snapshot = _snapshot_bundle(
        bundle_dir,
        after_manifest,
        after_bytes,
    )
    if before_snapshot != after_snapshot:
        raise ValueError("bundle generation changed during parse and validation")
    if bundle.get("bundle_id") != after_manifest.get("bundle_id"):
        raise ValueError("bundle identity does not match stable manifest generation")
    artifacts = after_manifest.get("artifacts")
    if not isinstance(artifacts, dict):
        raise ValueError("bundle artifacts are missing")
    for role, key in (
        ("dict_a_matcher", "dict_a_path"),
        ("dict_b_canonical", "dict_b_path"),
    ):
        descriptor = artifacts.get(role)
        if not isinstance(descriptor, dict):
            raise ValueError(f"bundle artifact {role} descriptor is invalid")
        expected_path = (bundle_dir / str(descriptor.get("path"))).resolve()
        if Path(bundle[key]).resolve() != expected_path:
            raise ValueError(f"bundle {role} path changed across generation")
    return bundle, after_manifest, after_bytes, after_snapshot


def _assert_bundle_unchanged(
    bundle_dir: Path,
    snapshot: dict[str, bytes],
    *,
    require_manifest_v2: bool = False,
) -> None:
    for relative_path, expected_bytes in snapshot.items():
        path = bundle_dir / relative_path
        if path.is_symlink() or not path.is_file() or path.read_bytes() != expected_bytes:
            raise ValueError(f"bundle changed during resolved export: {relative_path}")
    try:
        current = (
            _read_bundle(bundle_dir, require_manifest_v2=True)
            if require_manifest_v2
            else _read_bundle(bundle_dir)
        )
        _validate_candidate_artifacts(current)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError("bundle identity changed during resolved export") from exc


def _runtime_bundle_from_snapshot(
    snapshot: dict[str, bytes],
    destination: Path,
    *,
    require_manifest_v2: bool = False,
) -> dict[str, Any]:
    for relative_path, content in snapshot.items():
        path = destination / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    runtime_bundle = (
        _read_bundle(destination, require_manifest_v2=True)
        if require_manifest_v2
        else _read_bundle(destination)
    )
    _validate_candidate_artifacts(runtime_bundle)
    return runtime_bundle


def _snapshot_source(path: Path) -> dict[str, Any]:
    if path.is_symlink():
        raise ValueError(f"source must not be a symlink: {path}")
    try:
        before = path.lstat()
    except FileNotFoundError as exc:
        raise ValueError(f"source is missing: {path}") from exc
    if not stat.S_ISREG(before.st_mode):
        raise ValueError(f"source must be a regular file: {path}")
    content = path.read_bytes()
    if path.is_symlink():
        raise ValueError(f"source changed to a symlink while snapshotting: {path}")
    after = path.lstat()
    identity = (
        before.st_dev,
        before.st_ino,
        before.st_mode,
        before.st_size,
        before.st_mtime_ns,
    )
    after_identity = (
        after.st_dev,
        after.st_ino,
        after.st_mode,
        after.st_size,
        after.st_mtime_ns,
    )
    if identity != after_identity or len(content) != before.st_size:
        raise ValueError(f"source changed while snapshotting: {path}")
    return {
        "path": path,
        "resolved_path": path.resolve(strict=True),
        "identity": identity,
        "content": content,
        "sha256": _sha256_bytes(content),
    }


def _snapshot_sources(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    snapshots = []
    for source in sources:
        snapshot = _snapshot_source(source["path"])
        if snapshot["resolved_path"] != source["resolved_path"]:
            raise ValueError(f"source identity changed during discovery: {source['path']}")
        snapshot["source_path"] = source["source_path"]
        snapshots.append(snapshot)
    return snapshots


def _assert_sources_unchanged(source_snapshots: list[dict[str, Any]]) -> None:
    for expected in source_snapshots:
        current = _snapshot_source(expected["path"])
        if (
            current["resolved_path"] != expected["resolved_path"]
            or current["identity"] != expected["identity"]
            or current["sha256"] != expected["sha256"]
            or current["content"] != expected["content"]
        ):
            raise ValueError(f"source identity changed during export: {expected['path']}")


def _configuration_file_hashes(repo: Path) -> dict[str, str | None]:
    candidates = {
        "repo_dlcr_policy": repo
        / "assets/data/engine_dynamics_v060/dlcr_policy.yaml",
        "repo_domain_packs": repo
        / "assets/data/engine_dynamics_v060/domain_packs.yaml",
        "repo_version": repo / "assets/data/engine_dynamics_v060/VERSION.yaml",
        "engine_constants": _PROJECT_ROOT / "assets/config/engine_constants.json",
        "engine_signal_main": _PROJECT_ROOT
        / "assets/data/engine_dynamics_v060/semantic_dynamics/signal_calibration_v2.json",
        "engine_signal_legacy": _PROJECT_ROOT
        / "assets/data/engine_dynamics_v060/tfp/tfp_signal_calibration_v2.json",
    }
    return {
        name: _sha256_bytes(path.read_bytes()) if path.is_file() else None
        for name, path in sorted(candidates.items())
    }


def _code_constant_identity(value: Any) -> Any:
    if isinstance(value, CodeType):
        return _code_identity(value)
    if value is None or value is Ellipsis or isinstance(
        value, (bool, int, float, str)
    ):
        return repr(value)
    if isinstance(value, bytes):
        return {"bytes": value.hex()}
    if isinstance(value, tuple):
        return [_code_constant_identity(item) for item in value]
    if isinstance(value, frozenset):
        return sorted(_code_constant_identity(item) for item in value)
    raise ValueError(
        f"runner implementation contains unsupported code constant: "
        f"{type(value).__name__}"
    )


def _code_identity(code: CodeType) -> dict[str, Any]:
    return {
        "argcount": code.co_argcount,
        "posonlyargcount": code.co_posonlyargcount,
        "kwonlyargcount": code.co_kwonlyargcount,
        "flags": code.co_flags,
        "bytecode": code.co_code.hex(),
        "constants": [_code_constant_identity(item) for item in code.co_consts],
        "names": list(code.co_names),
        "varnames": list(code.co_varnames),
        "freevars": list(code.co_freevars),
        "cellvars": list(code.co_cellvars),
    }


def _resolver_semantic_source_hashes() -> dict[str, str]:
    hashes: dict[str, str] = {}
    for relative_path in sorted(_RESOLVER_SEMANTIC_SOURCE_PATHS):
        source_path = _PROJECT_ROOT / relative_path
        if not source_path.is_file():
            raise ValueError(
                f"resolver semantic source is not a regular file: {relative_path}"
            )
        hashes[relative_path] = _sha256_bytes(source_path.read_bytes())
    return hashes


def _assert_semantic_sources_unchanged(expected: dict[str, str]) -> None:
    if _resolver_semantic_source_hashes() != expected:
        raise ValueError("resolver semantic source bytes changed during resolved export")


def _runner_implementation_sha256(runner: Runner) -> str:
    implementation = (
        runner.__func__
        if inspect.ismethod(runner)
        else runner
        if inspect.isfunction(runner)
        else type(runner).__call__
    )
    code = getattr(implementation, "__code__", None)
    source_path_text = inspect.getsourcefile(implementation)
    if not isinstance(code, CodeType) or source_path_text is None:
        raise ValueError("runner implementation identity cannot be determined")
    source_path = Path(source_path_text)
    if not source_path.is_file():
        raise ValueError("runner implementation source is not a regular file")
    return _sha256_bytes(
        _canonical_bytes(
            {
                "schema": "hesperia.resolver_implementation.v1",
                "module": implementation.__module__,
                "qualname": implementation.__qualname__,
                "code": _code_identity(code),
                "source_file_sha256": _sha256_bytes(source_path.read_bytes()),
                "semantic_source_hashes": _resolver_semantic_source_hashes(),
            }
        )
    )


def _require_runner_dict_d_override_contract(runner: Runner) -> None:
    try:
        parameters = inspect.signature(runner).parameters.values()
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "runner signature cannot prove empirical_weight_override support"
        ) from exc
    if not any(
        parameter.name == "empirical_weight_override"
        or parameter.kind is inspect.Parameter.VAR_KEYWORD
        for parameter in parameters
    ):
        raise ValueError(
            "runner must accept the empirical_weight_override keyword"
        )


def _assert_runner_dict_d_off_trace(output: Any) -> None:
    if not isinstance(output, dict):
        raise ValueError("runner output must be an object")
    trace = output.get("resolver_trace")
    effective_weight = (
        trace.get("dict_d_effective_weight")
        if isinstance(trace, dict)
        else None
    )
    if (
        not isinstance(trace, dict)
        or not isinstance(effective_weight, (int, float))
        or isinstance(effective_weight, bool)
        or not math.isfinite(float(effective_weight))
        or float(effective_weight) != DICT_D_EXPORT_WEIGHT
    ):
        raise ValueError(
            "runner did not prove the resolved-export Dict D off override"
        )


def _effective_configuration_sha256(
    manifest_configuration_sha256: str,
    configuration_files: dict[str, str | None],
    resolver_implementation_sha256: str,
) -> str:
    return _sha256_bytes(
        _canonical_bytes(
            {
                "manifest_resolver_configuration_sha256": (
                    manifest_configuration_sha256
                ),
                "resolver_implementation_sha256": resolver_implementation_sha256,
                "pipeline_environment": _PINNED_PIPELINE_ENV,
                "empirical_weight_override": DICT_D_EXPORT_WEIGHT,
                "configuration_files": configuration_files,
            }
        )
    )


@contextmanager
def _isolated_pipeline_environment() -> Any:
    previous = {key: os.environ.get(key) for key in _PINNED_PIPELINE_ENV}
    try:
        os.environ.update(_PINNED_PIPELINE_ENV)
        clear_dlcr_policy_cache()
        load_engine_constants.cache_clear()
        load_engine_signal_calibration.cache_clear()
        yield
        if {
            key: os.environ.get(key) for key in _PINNED_PIPELINE_ENV
        } != _PINNED_PIPELINE_ENV:
            raise ValueError(
                "pipeline callback mutated the isolated effective environment"
            )
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        clear_dlcr_policy_cache()
        load_engine_constants.cache_clear()
        load_engine_signal_calibration.cache_clear()


def _span_record(
    raw_span: Any,
    paragraph_text: str,
    label: str,
) -> tuple[dict[str, Any], bool]:
    if not isinstance(raw_span, dict):
        raise ValueError(f"{label} must be an object")
    start = raw_span.get("source_char_start")
    end = raw_span.get("source_char_end")
    if (
        not isinstance(start, int)
        or isinstance(start, bool)
        or not isinstance(end, int)
        or isinstance(end, bool)
        or start < 0
        or end <= start
        or end > len(paragraph_text)
    ):
        raise ValueError(f"{label} source offsets are invalid")
    surface = raw_span.get("source_text_span")
    if not isinstance(surface, str) or paragraph_text[start:end] != surface:
        raise ValueError(f"{label} surface does not match source offsets")
    scores = _candidate_scores(raw_span.get("candidate_scores"), label)
    winner = raw_span.get("winning_concept_id")
    if winner is None:
        reason_codes = _validate_reason_codes(
            raw_span.get("rejected_reason_codes"),
            f"{label}.rejected_reason_codes",
        )
        return (
            {
                "span_position": start,
                "span_end": end,
                "surface": surface,
                "reason_codes": list(reason_codes),
                "candidate_scores": scores,
            },
            False,
        )
    if not isinstance(winner, str) or not winner:
        raise ValueError(f"{label}.winning_concept_id must be text or null")
    return (
        {
            "span_position": start,
            "span_end": end,
            "surface": surface,
            "winning_concept_id": winner,
            "candidate_scores": scores,
        },
        True,
    )


def _export_resolved_sources(
    *,
    bundle_path: Path,
    source_files: list[Path],
    repo_path: Path | None,
    runner: Runner,
    resolver_authority: str,
) -> dict[str, Any]:
    """Resolve all supported text files beneath the supplied corpus roots."""
    if not isinstance(source_files, list) or not source_files:
        raise ValueError("source_files must contain at least one corpus root")
    discovery = _discover_sources([Path(path) for path in source_files])
    source_snapshots = _snapshot_sources(discovery["sources"])

    bundle_dir = Path(bundle_path)
    require_manifest_v2 = False
    bundle, manifest, manifest_bytes, bundle_snapshot = (
        _load_stable_bundle_generation(bundle_dir)
    )
    _assert_corpus_unchanged(discovery)
    _assert_sources_unchanged(source_snapshots)
    provenance = manifest["provenance"]
    ledger_path: Path | None = None
    ledger: dict[str, Any] | None = None
    if manifest.get("schema_version") == "hesperia.dict_calibration.freeze_manifest.v2":
        ledger_descriptor = manifest["artifacts"]["generation_ledger"]
        ledger_path = bundle_dir / ledger_descriptor["path"]
        ledger = load_generation_ledger(
            ledger_path,
            git_snapshot=_git_snapshot(),
        )
        expected_sources = ledger["source_hashes"]
        actual_sources = {
            source["source_path"]: source["sha256"] for source in source_snapshots
        }
        if (
            actual_sources != expected_sources
            or len(source_snapshots) != ledger["source_count"]
            or manifest["generation"]["generation_id"] != ledger["generation_id"]
            or manifest["generation"]["ledger_sha256"] != _sha256_bytes(
                ledger_path.read_bytes()
            )
        ):
            raise ValueError(
                "resolved export source membership or generation-ledger binding differs"
            )
    repo = repo_path or repo_root()
    configuration_files = _configuration_file_hashes(repo)
    _require_runner_dict_d_override_contract(runner)
    semantic_source_hashes = _resolver_semantic_source_hashes()
    resolver_implementation_sha256 = _runner_implementation_sha256(runner)
    effective_configuration_sha256 = _effective_configuration_sha256(
        provenance["resolver"]["configuration_sha256"],
        configuration_files,
        resolver_implementation_sha256,
    )
    books: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    source_hashes: dict[str, str] = {}

    with tempfile.TemporaryDirectory(prefix="hesperia-resolved-export-") as temp_dir:
        snapshot_dir = Path(temp_dir) / "bundle"
        runtime_bundle = _runtime_bundle_from_snapshot(
            bundle_snapshot,
            snapshot_dir,
            require_manifest_v2=require_manifest_v2,
        )
        anchors_path = Path(temp_dir) / "bundle-anchors.json"
        _write_bundle_anchors(runtime_bundle, anchors_path)
        for source_snapshot in source_snapshots:
            _assert_bundle_unchanged(
                bundle_dir,
                bundle_snapshot,
                require_manifest_v2=require_manifest_v2,
            )
            _assert_bundle_unchanged(
                snapshot_dir,
                bundle_snapshot,
                require_manifest_v2=require_manifest_v2,
            )
            source = Path(source_snapshot["path"])
            source_path = source_snapshot["source_path"]
            source_bytes = source_snapshot["content"]
            source_sha256 = source_snapshot["sha256"]
            source_hashes[source_path] = source_sha256
            try:
                raw_text = source_bytes.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise ValueError(
                    f"{source_path} must contain valid UTF-8 text"
                ) from exc
            paragraph_texts = _segment_paragraphs(raw_text)
            book_id = _sha256_bytes(source_path.encode("utf-8"))
            paragraphs: list[dict[str, Any]] = []
            for source_ordinal, paragraph_text in enumerate(paragraph_texts):
                with _isolated_pipeline_environment():
                    output = runner(
                        paragraph_text,
                        repo_root=repo,
                        dict_a_paths=[runtime_bundle["dict_a_path"]],
                        dict_b_paths=[runtime_bundle["dict_b_path"]],
                        anchors_path=anchors_path,
                        mode="core",
                        empirical_weight_override=DICT_D_EXPORT_WEIGHT,
                    )
                    _assert_runner_dict_d_off_trace(output)
                    _assert_semantic_sources_unchanged(semantic_source_hashes)
                    if (
                        _runner_implementation_sha256(runner)
                        != resolver_implementation_sha256
                    ):
                        raise ValueError(
                            "runner implementation changed during resolved export"
                        )
                _assert_bundle_unchanged(
                    bundle_dir,
                    bundle_snapshot,
                    require_manifest_v2=require_manifest_v2,
                )
                _assert_bundle_unchanged(
                    snapshot_dir,
                    bundle_snapshot,
                    require_manifest_v2=require_manifest_v2,
                )
                _assert_corpus_unchanged(discovery)
                _assert_sources_unchanged(source_snapshots)
                if _configuration_file_hashes(repo) != configuration_files:
                    raise ValueError(
                        "effective pipeline configuration changed during export"
                    )
                canonical_text = output.get("canonical_text")
                aligned_text, canonical_ranges = _canonical_alignment(paragraph_text)
                if (
                    not isinstance(canonical_text, str)
                    or canonical_text != aligned_text
                ):
                    raise ValueError(
                        f"{source_path} pipeline canonical_text cannot align to paragraph"
                    )
                paragraph_id = _paragraph_identity(
                    source_sha256, source_ordinal, paragraph_text
                )
                resolved_spans: list[dict[str, Any]] = []
                span_collections = (
                    ("span_resolutions", True),
                    ("unresolved_span_resolutions", False),
                )
                for collection_name, expected_resolved in span_collections:
                    raw_spans = output.get(collection_name)
                    if not isinstance(raw_spans, list):
                        raise ValueError(
                            f"{source_path}.{collection_name} must be a list"
                        )
                    for span_index, raw_span in enumerate(raw_spans):
                        span_label = (
                            f"{source_path}.{collection_name}[{span_index}]"
                        )
                        translated_span = _translate_canonical_span(
                            raw_span,
                            canonical_text,
                            canonical_ranges,
                            paragraph_text,
                            span_label,
                        )
                        record, is_resolved = _span_record(
                            translated_span,
                            paragraph_text,
                            span_label,
                        )
                        if is_resolved != expected_resolved:
                            raise ValueError(
                                f"{span_label} resolution state does not match "
                                f"{collection_name}"
                            )
                        if is_resolved:
                            resolved_spans.append(record)
                        else:
                            unresolved.append(
                                {
                                    "book_id": book_id,
                                    "paragraph_id": paragraph_id,
                                    **record,
                                }
                            )
                paragraphs.append(
                    {
                        "paragraph_id": paragraph_id,
                        "source_ordinal": source_ordinal,
                        "text": paragraph_text,
                        "resolved_spans": sorted(
                            resolved_spans,
                            key=lambda span: (
                                span["span_position"],
                                span["span_end"],
                                span["winning_concept_id"],
                            ),
                        ),
                    }
                )
            books.append(
                {
                    "book_id": book_id,
                    "source_path": source_path,
                    "source_sha256": source_sha256,
                    "paragraphs": paragraphs,
                }
            )

    _assert_corpus_unchanged(discovery)
    _assert_sources_unchanged(source_snapshots)
    _assert_bundle_unchanged(
        bundle_dir,
        bundle_snapshot,
        require_manifest_v2=require_manifest_v2,
    )
    _assert_semantic_sources_unchanged(semantic_source_hashes)
    if _runner_implementation_sha256(runner) != resolver_implementation_sha256:
        raise ValueError("runner implementation changed during resolved export")
    if ledger_path is not None and ledger is not None:
        final_ledger = load_generation_ledger(
            ledger_path,
            git_snapshot=_git_snapshot(),
        )
        if final_ledger != ledger:
            raise ValueError("generation ledger or code snapshot changed during export")
    export = {
        "schema": RESOLVED_CORPUS_SCHEMA,
        "provenance": {
            "candidate_bundle_id": bundle["bundle_id"],
            "candidate_manifest_sha256": _sha256_bytes(manifest_bytes),
            "corpus_snapshot_sha256": _sha256_bytes(_canonical_bytes(source_hashes)),
            "resolver_version": provenance["resolver"]["version"],
            "resolver_implementation_sha256": resolver_implementation_sha256,
            "resolver_authority": resolver_authority,
            "resolver_configuration_sha256": effective_configuration_sha256,
            "segmentation_rule": provenance["segmentation_rule"],
            "export_rule": EXPORT_RULE,
            "dict_d_enabled": False,
            "dict_d_effective_weight": 0.0,
        },
        "books": books,
        "unresolved": sorted(
            unresolved,
            key=lambda record: (
                next(
                    index
                    for index, book in enumerate(books)
                    if book["book_id"] == record["book_id"]
                ),
                next(
                    paragraph["source_ordinal"]
                    for book in books
                    if book["book_id"] == record["book_id"]
                    for paragraph in book["paragraphs"]
                    if paragraph["paragraph_id"] == record["paragraph_id"]
                ),
                record["span_position"],
                record["span_end"],
            ),
        ),
    }
    _validate_resolved_export(
        export,
        allow_test_authority=resolver_authority == TEST_RESOLVER_AUTHORITY,
    )
    return export


def export_resolved_sources(
    *,
    bundle_path: Path,
    source_files: list[Path],
    repo_path: Path | None = None,
    runner: Runner = run_dlcr_pipeline,
) -> dict[str, Any]:
    """Release export, restricted to the canonical in-process DLCR pipeline."""
    if runner is not run_dlcr_pipeline:
        raise ValueError(
            "release export requires canonical run_dlcr_pipeline identity"
        )
    return _export_resolved_sources(
        bundle_path=bundle_path,
        source_files=source_files,
        repo_path=repo_path,
        runner=runner,
        resolver_authority=CANONICAL_RESOLVER_AUTHORITY,
    )


def _export_resolved_sources_for_test(
    *,
    bundle_path: Path,
    source_files: list[Path],
    repo_path: Path | None = None,
    runner: Runner,
) -> dict[str, Any]:
    """Private test seam; emitted provenance is explicitly non-release."""
    return _export_resolved_sources(
        bundle_path=bundle_path,
        source_files=source_files,
        repo_path=repo_path,
        runner=runner,
        resolver_authority=TEST_RESOLVER_AUTHORITY,
    )


def _write_new_atomic(output: Path, content: bytes) -> None:
    if output.is_symlink() or output.exists():
        raise ValueError("output destination already exists")
    parent = output.parent
    if parent.is_symlink() or not parent.is_dir():
        raise ValueError("output destination directory must be a regular directory")

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{output.name}.",
        suffix=".tmp",
        dir=parent,
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        if output.is_symlink() or output.exists():
            raise ValueError("output destination appeared before atomic install")
        os.replace(temporary, output)
        directory_descriptor = os.open(parent, os.O_RDONLY)
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
    finally:
        temporary.unlink(missing_ok=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Resolve every supported text file under supplied corpus files or "
            "directories with one frozen candidate bundle. Paragraph segmentation "
            "remains a separate CORE-D2 gate."
        )
    )
    parser.add_argument("--bundle", required=True)
    parser.add_argument("--corpus", required=True, nargs="+")
    parser.add_argument("--output", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output = Path(args.output)
    if output.is_symlink() or output.exists():
        raise ValueError("output destination already exists")
    export = export_resolved_sources(
        bundle_path=Path(args.bundle),
        source_files=[Path(path) for path in args.corpus],
    )
    _write_new_atomic(output, canonicalize_resolved_export(export))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
