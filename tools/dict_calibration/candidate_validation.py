# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""Shared manifest-v2 artifact, count, status, and lineage validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .core_candidate import EMPTY_SHA256, canonical_bytes, load_jsonl, sha256_file


MANIFEST_V2 = "hesperia.dict_calibration.freeze_manifest.v2"
ROLE_STATUS = {
    "dict_a_matcher": "matcher_ready",
    "dict_b_canonical": "canonical",
    "dict_b_proposal_evidence": "proposal_evidence",
    "dict_b_authored_edge_provenance": "authored_edge_provenance",
    "dict_c_source": "source_evidence",
    "dict_c_intermediate": "intermediate_evidence",
    "dict_c_runtime_conversion": "matcher_ready",
    "generation_ledger": "generation_evidence",
    "evaluation_metrics": "evaluation_evidence",
}
REQUIRED_V2_ROLES = frozenset(ROLE_STATUS)


def _safe_path(bundle: Path, value: Any, role: str) -> Path:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{role} path is missing")
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"{role} path is unsafe")
    path = bundle / relative
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"{role} path must be a regular file")
    try:
        path.resolve(strict=True).relative_to(bundle.resolve(strict=True))
    except (FileNotFoundError, ValueError) as exc:
        raise ValueError(f"{role} path escapes bundle") from exc
    return path


def _json_row_count(path: Path) -> int:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not value:
        raise ValueError(f"{path.name} must be a non-empty JSON object")
    canonical_bytes(value)
    return 1


def _validate_lineage(paths: dict[str, Path]) -> None:
    source = load_jsonl(paths["dict_c_source"], allow_empty=False)
    intermediate = load_jsonl(paths["dict_c_intermediate"], allow_empty=False)
    runtime = load_jsonl(paths["dict_c_runtime_conversion"], allow_empty=False)
    source_fields = {
        "link_id",
        "lexical",
        "concept_id",
        "match_type",
        "priority",
        "source_ordinal",
    }
    intermediate_fields = {
        "normalized_form",
        "candidate_concept_ids",
        "priority",
        "source_link_ids",
    }
    runtime_fields = {"normalized_form", "candidate_concept_ids", "priority"}
    if any(set(row) != source_fields for row in source):
        raise ValueError("Dict C source schema is strict")
    if any(set(row) != intermediate_fields for row in intermediate):
        raise ValueError("Dict C intermediate schema is strict")
    if any(set(row) != runtime_fields for row in runtime):
        raise ValueError("Dict C runtime schema is strict")
    source_ids = [row["link_id"] for row in source]
    claimed_ids = [
        link_id for row in intermediate for link_id in row["source_link_ids"]
    ]
    if (
        len(source_ids) != len(set(source_ids))
        or len(claimed_ids) != len(set(claimed_ids))
        or set(source_ids) != set(claimed_ids)
    ):
        raise ValueError("Dict C source/intermediate lineage is incomplete or ambiguous")
    source_by_id = {row["link_id"]: row for row in source}
    expected_runtime: list[dict[str, Any]] = []
    normalized: list[str] = []
    for row in intermediate:
        members = [source_by_id[link_id] for link_id in row["source_link_ids"]]
        if (
            not members
            or any(member["lexical"] != row["normalized_form"] for member in members)
            or row["candidate_concept_ids"]
            != sorted({member["concept_id"] for member in members})
            or row["priority"] != max(member["priority"] for member in members)
            or row["source_link_ids"] != sorted(row["source_link_ids"])
        ):
            raise ValueError("Dict C intermediate derivation does not recompute")
        normalized.append(row["normalized_form"])
        expected_runtime.append(
            {
                "normalized_form": row["normalized_form"],
                "candidate_concept_ids": row["candidate_concept_ids"],
                "priority": row["priority"],
            }
        )
    if normalized != sorted(normalized) or len(normalized) != len(set(normalized)):
        raise ValueError("Dict C intermediate identity/order is invalid")
    if runtime != expected_runtime:
        raise ValueError("Dict C runtime projection or lineage is invalid")


def _validate_proposals(path: Path) -> None:
    rows = load_jsonl(path, allow_empty=False)
    identities: set[str] = set()
    anchored = {
        "proposal_id",
        "outcome",
        "proposed_concept_id",
        "anchor",
        "bind_score",
        "bind_reason",
        "source_ordinal",
    }
    rejected = {
        "proposal_id",
        "outcome",
        "proposed_concept_id",
        "reason",
        "best_score",
        "detail",
        "source_ordinal",
    }
    for row in rows:
        expected = anchored if row.get("outcome") == "anchored" else rejected
        if set(row) != expected or row.get("outcome") not in {"anchored", "rejected"}:
            raise ValueError("Dict B proposal evidence tagged variant is invalid")
        proposal_id = row["proposal_id"]
        if proposal_id in identities:
            raise ValueError("Dict B proposal disposition is duplicated")
        identities.add(proposal_id)
    if [row["proposal_id"] for row in rows] != sorted(identities):
        raise ValueError("Dict B proposal evidence order is not canonical")


def _validate_edges(paths: dict[str, Path], descriptors: dict[str, Any]) -> None:
    dict_b = load_jsonl(paths["dict_b_canonical"], allow_empty=False)
    canonical_edges = {
        tuple(sorted((row["concept_id"], target)))
        for row in dict_b
        for target in row["related_concept_ids"]
    }
    descriptor = descriptors["dict_b_authored_edge_provenance"]
    edge_path = paths["dict_b_authored_edge_provenance"]
    if descriptor["row_count"] == 0:
        if (
            descriptor.get("evidence_status") != "truthful_zero"
            or edge_path.read_bytes()
            or descriptor["sha256"] != EMPTY_SHA256
            or canonical_edges
        ):
            raise ValueError("truthful-zero authored-edge evidence is false")
        return
    rows = load_jsonl(edge_path, allow_empty=False)
    if descriptor.get("evidence_status") != "present":
        raise ValueError("non-zero authored-edge evidence status must be present")
    mapped = {
        tuple(sorted((row.get("source"), row.get("target"))))
        for row in rows
        if set(row) == {"source", "target"}
    }
    if len(mapped) != len(rows) or mapped != canonical_edges:
        raise ValueError("authored-edge evidence does not map canonical Dict B")


def validate_v2_artifacts(
    bundle: Path,
    manifest: dict[str, Any],
) -> tuple[dict[str, Path], dict[str, int]]:
    if manifest.get("schema_version") != MANIFEST_V2:
        raise ValueError("manifest-v2 validation requires freeze_manifest.v2")
    generation = manifest.get("generation")
    provenance = manifest.get("provenance")
    if (
        not isinstance(generation, dict)
        or set(generation) != {"generation_id", "ledger_sha256"}
        or not isinstance(provenance, dict)
        or provenance.get("generation_id") != generation.get("generation_id")
        or provenance.get("generation_ledger_sha256") != generation.get("ledger_sha256")
    ):
        raise ValueError("manifest generation/ledger lineage is invalid")
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, dict) or set(artifacts) != REQUIRED_V2_ROLES:
        raise ValueError("manifest-v2 artifact roles are strict and complete")
    paths: dict[str, Path] = {}
    counts: dict[str, int] = {}
    for role, descriptor in artifacts.items():
        expected_fields = {"path", "sha256", "status", "row_count"}
        if role == "dict_b_authored_edge_provenance":
            expected_fields.add("evidence_status")
        if (
            not isinstance(descriptor, dict)
            or set(descriptor) != expected_fields
            or descriptor.get("status") != ROLE_STATUS[role]
            or not isinstance(descriptor.get("row_count"), int)
            or isinstance(descriptor.get("row_count"), bool)
            or descriptor["row_count"] < 0
        ):
            raise ValueError(f"{role} manifest descriptor/count/status is invalid")
        path = _safe_path(bundle, descriptor["path"], role)
        if descriptor.get("sha256") != sha256_file(path):
            raise ValueError(f"{role} digest does not match")
        count = (
            _json_row_count(path)
            if role in {"generation_ledger", "evaluation_metrics"}
            else len(path.read_text(encoding="utf-8").splitlines())
        )
        if count != descriptor["row_count"]:
            raise ValueError(f"{role} row_count does not recompute")
        if role != "dict_b_authored_edge_provenance" and count == 0:
            raise ValueError(f"{role} must be non-empty")
        paths[role] = path
        counts[role] = count
    _validate_proposals(paths["dict_b_proposal_evidence"])
    _validate_edges(paths, artifacts)
    _validate_lineage(paths)
    return paths, counts
