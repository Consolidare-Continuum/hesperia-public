# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""Deterministic producer-to-candidate materialization for CORE-D2 releases."""

from __future__ import annotations

import hashlib
import json
import math
import shutil
from collections import defaultdict
from pathlib import Path
from typing import Any


MATCH_TYPES = frozenset({"exact", "phrase", "lemma", "stem", "pattern"})
EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()
PRODUCER_FILES = (
    "dict_a_engine.jsonl",
    "dict_b_draft.jsonl",
    "dict_b_anchored.jsonl",
    "dict_b_rejected.jsonl",
    "dict_a_to_b_links.jsonl",
)

_A_FIELDS = frozenset(
    {
        "entry_id",
        "surface_form",
        "normalized_form",
        "match_type",
        "candidate_concept_ids",
        "priority",
        "version",
    }
)
_LINK_FIELDS = frozenset({"lexical", "concept_id", "match_type", "priority"})


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def canonical_object_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def _no_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON number: {value}")


def load_jsonl(path: Path, *, allow_empty: bool) -> list[dict[str, Any]]:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"producer input must be a regular non-symlink file: {path.name}")
    try:
        raw = path.read_bytes()
        text = raw.decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ValueError(f"{path.name} must contain valid UTF-8") from exc
    rows: list[dict[str, Any]] = []
    for ordinal, line in enumerate(text.splitlines()):
        if not line.strip():
            raise ValueError(f"{path.name} contains blank JSONL record {ordinal}")
        try:
            row = json.loads(
                line,
                object_pairs_hook=_no_duplicate_keys,
                parse_constant=_reject_constant,
            )
        except (json.JSONDecodeError, ValueError) as exc:
            raise ValueError(f"{path.name} invalid JSONL at ordinal {ordinal}: {exc}") from exc
        if not isinstance(row, dict):
            raise ValueError(f"{path.name} row {ordinal} must be an object")
        canonical_bytes(row)
        rows.append(row)
    if not rows and not allow_empty:
        raise ValueError(f"{path.name} must not be empty")
    return rows


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be non-empty text")
    return value


def _finite_number(value: Any, label: str) -> int | float:
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(float(value))
    ):
        raise ValueError(f"{label} must be finite")
    return value


def _canonical_text_list(value: Any, label: str, *, nonempty: bool) -> list[str]:
    if (
        not isinstance(value, list)
        or (nonempty and not value)
        or any(not isinstance(item, str) or not item.strip() for item in value)
        or len(value) != len(set(value))
        or value != sorted(value)
    ):
        raise ValueError(f"{label} must be unique non-empty text in canonical order")
    return value


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"".join(canonical_bytes(row) for row in rows))


def _project_dict_b(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, bytes] = {}
    projected_by_id: dict[str, dict[str, Any]] = {}
    for ordinal, row in enumerate(rows):
        concept_id = _text(row.get("concept_id"), f"dict_b_anchored[{ordinal}].concept_id")
        projected: dict[str, Any] = {
            "concept_id": concept_id,
            "related_concept_ids": _canonical_text_list(
                row.get("related_concept_ids"),
                f"{concept_id}.related_concept_ids",
                nonempty=False,
            ),
        }
        for field in ("area_ids", "family_ids"):
            if field in row:
                projected[field] = _canonical_text_list(
                    row[field], f"{concept_id}.{field}", nonempty=True
                )
        serialized = canonical_bytes(projected)
        previous = grouped.setdefault(concept_id, serialized)
        if previous != serialized:
            raise ValueError(f"conflicting duplicate Dict B projection: {concept_id}")
        projected_by_id[concept_id] = projected
    result = [projected_by_id[key] for key in sorted(projected_by_id)]
    concept_ids = set(projected_by_id)
    for row in result:
        concept_id = row["concept_id"]
        related = row["related_concept_ids"]
        if concept_id in related:
            raise ValueError(f"Dict B self-relation is forbidden: {concept_id}")
        missing = sorted(set(related) - concept_ids)
        if missing:
            raise ValueError(f"Dict B reference closure failed: {missing}")
        for target in related:
            if concept_id not in projected_by_id[target]["related_concept_ids"]:
                raise ValueError(f"asymmetric authored relation: {concept_id}, {target}")
    return result


def _project_dict_a(
    rows: list[dict[str, Any]],
    concept_ids: set[str],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    entry_ids: set[str] = set()
    matcher_keys: set[tuple[str, str]] = set()
    for ordinal, row in enumerate(rows):
        if set(row) != _A_FIELDS:
            raise ValueError("dict_a_engine row schema must be exact")
        entry_id = _text(row["entry_id"], f"dict_a_engine[{ordinal}].entry_id")
        normalized = _text(
            row["normalized_form"], f"dict_a_engine[{ordinal}].normalized_form"
        )
        match_type = row["match_type"]
        if match_type not in MATCH_TYPES:
            raise ValueError(f"unsupported Dict A match_type: {match_type}")
        candidates = _canonical_text_list(
            row["candidate_concept_ids"],
            f"dict_a_engine[{ordinal}].candidate_concept_ids",
            nonempty=True,
        )
        missing = sorted(set(candidates) - concept_ids)
        if missing:
            raise ValueError(f"Dict A candidate closure failed: {missing}")
        matcher_key = (normalized, match_type)
        if entry_id in entry_ids:
            raise ValueError(f"duplicate Dict A entry_id: {entry_id}")
        if matcher_key in matcher_keys:
            raise ValueError(f"duplicate normalized Dict A matcher: {matcher_key}")
        entry_ids.add(entry_id)
        matcher_keys.add(matcher_key)
        result.append(
            {
                "entry_id": entry_id,
                "normalized_form": normalized,
                "match_type": match_type,
                "candidate_concept_ids": candidates,
            }
        )
    return sorted(
        result,
        key=lambda row: (row["normalized_form"], row["match_type"], row["entry_id"]),
    )


def _proposal_id(row: dict[str, Any], ordinal: int) -> str:
    return sha256_bytes(
        canonical_object_bytes(row) + b"\0" + str(ordinal).encode("ascii")
    )


def _proposal_evidence(
    drafts: list[dict[str, Any]],
    anchored: list[dict[str, Any]],
    rejected: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_concept: dict[str, list[tuple[int, dict[str, Any], str]]] = defaultdict(list)
    by_bytes: dict[bytes, list[tuple[int, dict[str, Any], str]]] = defaultdict(list)
    unmatched_ordinals: set[int] = set()
    for ordinal, draft in enumerate(drafts):
        concept_id = _text(
            draft.get("concept_id"), f"dict_b_draft[{ordinal}].concept_id"
        )
        proposal_id = _proposal_id(draft, ordinal)
        proposal = (ordinal, draft, proposal_id)
        by_concept[concept_id].append(proposal)
        by_bytes[canonical_object_bytes(draft)].append(proposal)
        unmatched_ordinals.add(ordinal)

    dispositions: dict[str, dict[str, Any]] = {}
    for ordinal, row in enumerate(anchored):
        draft_id = _text(
            row.get("calibration_draft_id"),
            f"dict_b_anchored[{ordinal}].calibration_draft_id",
        )
        matches = [
            proposal
            for proposal in by_concept.get(draft_id, [])
            if proposal[0] in unmatched_ordinals
        ]
        preserved: dict[str, Any] = {}
        if "calibration_from_lexical" in row:
            preserved["from_lexical"] = row["calibration_from_lexical"]
        for field, value in row.items():
            if field.startswith("calibration_draft_") and field != "calibration_draft_id":
                preserved[field.removeprefix("calibration_draft_")] = value
        matches = [
            proposal
            for proposal in matches
            if all(proposal[1].get(field) == value for field, value in preserved.items())
        ]
        if not matches:
            raise ValueError(f"unknown proposal occurrence for anchored row: {draft_id}")
        distinct_content = {
            canonical_object_bytes(proposal[1]) for proposal in matches
        }
        if len(distinct_content) > 1:
            raise ValueError(
                f"ambiguous differing content for anchored proposal: {draft_id}"
            )
        source_ordinal, draft, proposal_id = min(
            matches,
            key=lambda proposal: proposal[0],
        )
        unmatched_ordinals.remove(source_ordinal)
        evidence = {
            "proposal_id": proposal_id,
            "outcome": "anchored",
            "proposed_concept_id": draft["concept_id"],
            "anchor": _text(row.get("concept_id"), "anchored concept_id"),
            "bind_score": _finite_number(
                row.get("calibration_bind_score"), "calibration_bind_score"
            ),
            "bind_reason": _text(
                row.get("calibration_bind_reason"), "calibration_bind_reason"
            ),
            "source_ordinal": source_ordinal,
        }
        if proposal_id in dispositions:
            raise ValueError(f"multiple dispositions for proposal: {proposal_id}")
        dispositions[proposal_id] = evidence

    for ordinal, row in enumerate(rejected):
        if set(row) != {"draft", "reason", "best_score", "detail"}:
            raise ValueError("dict_b_rejected row schema must be exact")
        draft = row["draft"]
        if not isinstance(draft, dict):
            raise ValueError(f"dict_b_rejected[{ordinal}].draft must be an object")
        matches = [
            proposal
            for proposal in by_bytes.get(canonical_object_bytes(draft), [])
            if proposal[0] in unmatched_ordinals
        ]
        if not matches:
            raise ValueError("unknown proposal occurrence for rejected row")
        source_ordinal, source_draft, proposal_id = min(
            matches,
            key=lambda proposal: proposal[0],
        )
        unmatched_ordinals.remove(source_ordinal)
        evidence = {
            "proposal_id": proposal_id,
            "outcome": "rejected",
            "proposed_concept_id": source_draft["concept_id"],
            "reason": _text(row["reason"], "rejection reason"),
            "best_score": _finite_number(row["best_score"], "rejection best_score"),
            "detail": _text(row["detail"], "rejection detail"),
            "source_ordinal": source_ordinal,
        }
        if proposal_id in dispositions:
            raise ValueError(f"multiple dispositions for proposal: {proposal_id}")
        dispositions[proposal_id] = evidence

    if unmatched_ordinals:
        raise ValueError(
            "proposal multiset has residual undisposed occurrences: "
            f"{sorted(unmatched_ordinals)}"
        )
    return [dispositions[key] for key in sorted(dispositions)]


def _materialize_edges(
    producer_dir: Path,
    dict_b: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], str]:
    canonical_edges = {
        tuple(sorted((row["concept_id"], target)))
        for row in dict_b
        for target in row["related_concept_ids"]
    }
    edge_path = producer_dir / "dict_b_authored_edges.jsonl"
    if not canonical_edges:
        if edge_path.exists() and load_jsonl(edge_path, allow_empty=True):
            raise ValueError("authored-edge evidence exists for relation-free Dict B")
        return [], "truthful_zero"
    if not edge_path.exists():
        raise ValueError("claimed relation lacks authored-edge evidence")
    rows = load_jsonl(edge_path, allow_empty=False)
    mapped: set[tuple[str, str]] = set()
    result: list[dict[str, Any]] = []
    for ordinal, row in enumerate(rows):
        if set(row) != {"source", "target"}:
            raise ValueError("authored-edge row schema must be exact")
        source = _text(row["source"], f"authored_edge[{ordinal}].source")
        target = _text(row["target"], f"authored_edge[{ordinal}].target")
        edge = tuple(sorted((source, target)))
        if source == target or edge not in canonical_edges or edge in mapped:
            raise ValueError("authored-edge mapping is incomplete or duplicated")
        mapped.add(edge)
        result.append({"source": edge[0], "target": edge[1]})
    if mapped != canonical_edges:
        raise ValueError("authored-edge evidence does not cover canonical Dict B")
    return sorted(result, key=lambda row: (row["source"], row["target"])), "present"


def _materialize_dict_c(
    links: list[dict[str, Any]],
    concept_ids: set[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    source_rows: list[dict[str, Any]] = []
    for ordinal, row in enumerate(links):
        if set(row) != _LINK_FIELDS:
            raise ValueError("dict_a_to_b_links row schema must be exact")
        lexical = _text(row["lexical"], f"link[{ordinal}].lexical")
        concept_id = _text(row["concept_id"], f"link[{ordinal}].concept_id")
        if concept_id not in concept_ids:
            raise ValueError(f"Dict C concept closure failed: {concept_id}")
        match_type = _text(row["match_type"], f"link[{ordinal}].match_type")
        priority = _finite_number(row["priority"], f"link[{ordinal}].priority")
        source_rows.append(
            {
                "link_id": sha256_bytes(
                    canonical_object_bytes(row)
                    + b"\0"
                    + str(ordinal).encode("ascii")
                ),
                "lexical": lexical,
                "concept_id": concept_id,
                "match_type": match_type,
                "priority": priority,
                "source_ordinal": ordinal,
            }
        )
    source_rows.sort(key=lambda row: row["link_id"])
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in source_rows:
        groups[row["lexical"]].append(row)
    intermediate = [
        {
            "normalized_form": lexical,
            "candidate_concept_ids": sorted({row["concept_id"] for row in rows}),
            "priority": max(row["priority"] for row in rows),
            "source_link_ids": sorted(row["link_id"] for row in rows),
        }
        for lexical, rows in sorted(groups.items())
    ]
    runtime = [
        {
            "normalized_form": row["normalized_form"],
            "candidate_concept_ids": row["candidate_concept_ids"],
            "priority": row["priority"],
        }
        for row in intermediate
    ]
    return source_rows, intermediate, runtime


def _source_snapshot(producer_dir: Path) -> dict[str, str]:
    snapshot: dict[str, str] = {}
    for name in PRODUCER_FILES:
        path = producer_dir / name
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"required producer file is missing or unsafe: {name}")
        snapshot[name] = sha256_file(path)
    optional = producer_dir / "dict_b_authored_edges.jsonl"
    if optional.exists():
        if optional.is_symlink() or not optional.is_file():
            raise ValueError("optional authored-edge producer file is unsafe")
        snapshot[optional.name] = sha256_file(optional)
    return snapshot


def materialize_candidate(producer_dir: Path, destination: Path) -> dict[str, Any]:
    """Materialize canonical A/B/C and evidence from one stable producer directory."""
    producer_dir = producer_dir.resolve(strict=True)
    if destination.exists():
        if not destination.is_dir() or any(destination.iterdir()):
            raise ValueError("materialization destination must be absent or empty")
    destination.mkdir(parents=True, exist_ok=True)
    snapshot = _source_snapshot(producer_dir)
    try:
        anchored = load_jsonl(producer_dir / "dict_b_anchored.jsonl", allow_empty=False)
        dict_b = _project_dict_b(anchored)
        concept_ids = {row["concept_id"] for row in dict_b}
        dict_a = _project_dict_a(
            load_jsonl(producer_dir / "dict_a_engine.jsonl", allow_empty=False),
            concept_ids,
        )
        proposals = _proposal_evidence(
            load_jsonl(producer_dir / "dict_b_draft.jsonl", allow_empty=False),
            anchored,
            load_jsonl(producer_dir / "dict_b_rejected.jsonl", allow_empty=True),
        )
        edges, evidence_status = _materialize_edges(producer_dir, dict_b)
        source, intermediate, runtime = _materialize_dict_c(
            load_jsonl(
                producer_dir / "dict_a_to_b_links.jsonl",
                allow_empty=False,
            ),
            concept_ids,
        )
        artifacts = {
            "dict_a_matcher": ("dict_a.jsonl", dict_a),
            "dict_b_canonical": ("dict_b.jsonl", dict_b),
            "dict_b_proposal_evidence": (
                "evidence/dict_b_proposals.jsonl",
                proposals,
            ),
            "dict_b_authored_edge_provenance": (
                "evidence/dict_b_authored_edges.jsonl",
                edges,
            ),
            "dict_c_source": ("evidence/dict_c_source.jsonl", source),
            "dict_c_intermediate": (
                "evidence/dict_c_intermediate.jsonl",
                intermediate,
            ),
            "dict_c_runtime_conversion": ("dict_c.jsonl", runtime),
        }
        for relative_path, rows in artifacts.values():
            _write_jsonl(destination / relative_path, rows)
        if _source_snapshot(producer_dir) != snapshot:
            raise ValueError("producer input mutation detected during materialization")
        return {
            "artifacts": {
                role: {
                    "path": relative_path,
                    "row_count": len(rows),
                    "sha256": sha256_file(destination / relative_path),
                }
                for role, (relative_path, rows) in sorted(artifacts.items())
            },
            "row_counts": {
                role: len(rows)
                for role, (_relative_path, rows) in sorted(artifacts.items())
            },
            "authored_edge_evidence_status": evidence_status,
            "producer_snapshot": snapshot,
        }
    except Exception:
        shutil.rmtree(destination, ignore_errors=True)
        raise
