# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""Fail-closed validation for frozen core dictionary calibration packs."""

from __future__ import annotations

import hashlib
import json
import math
import re
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from .candidate_validation import MANIFEST_V2, validate_v2_artifacts


GATE_SCHEMA = "hesperia.core_calibration_pack_gate.v1"
MANIFEST_SCHEMA = "hesperia.dict_calibration.freeze_manifest.v1"
EVALUATION_SCHEMA = "hesperia.dict_calibration.bundle_comparison.v1"
LIMITS_SCHEMA = "hesperia.dict_calibration.limits.v1"

ProcessRunner = Callable[..., subprocess.CompletedProcess[str]]
BoundaryChecker = Callable[[Path], subprocess.CompletedProcess[str]]

_SHA256_LENGTH = 64
_SUBPROCESS_TIMEOUT_SECONDS = 300.0
_REQUIRED_ROLES = frozenset(
    {"dict_a_matcher", "dict_b_canonical", "dict_c_runtime_conversion"}
)
_EVIDENCE_ROLES = frozenset(
    {
        "dict_a_proposal_evidence",
        "dict_a_anchor_evidence",
        "dict_b_proposal_evidence",
        "dict_b_authored_edge_provenance",
        "dict_c_source",
        "dict_c_intermediate",
        "evaluation_metrics",
    }
)
_ALLOWED_ROLES = _REQUIRED_ROLES | _EVIDENCE_ROLES | {"dict_d"}
_ROLE_STATUS = {
    "dict_a_matcher": "matcher_ready",
    "dict_a_proposal_evidence": "proposal_evidence",
    "dict_a_anchor_evidence": "anchor_evidence",
    "dict_b_canonical": "canonical",
    "dict_b_proposal_evidence": "proposal_evidence",
    "dict_b_authored_edge_provenance": "authored_edge_provenance",
    "dict_c_source": "source_evidence",
    "dict_c_intermediate": "intermediate_evidence",
    "dict_c_runtime_conversion": "matcher_ready",
    "evaluation_metrics": "evaluation_evidence",
    "dict_d": "validated_optional",
}
_MATCH_TYPES = frozenset({"exact", "phrase", "lemma", "stem", "pattern"})
_LIMIT_KEYS = frozenset(
    {"accepted", "rejected", "coverage", "entropy", "family_distribution"}
)
_FIELD_SPECIFIC_MARKER = re.compile(
    r"(^|[^a-z0-9])tfp(?:$|[._/:\-])",
    re.IGNORECASE,
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


def _sha256(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _is_sha256(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != _SHA256_LENGTH:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return value == value.casefold()


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_finite_number(value: Any) -> bool:
    return _is_number(value) and math.isfinite(float(value))


def _nonempty_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _text_list(value: Any, *, nonempty: bool) -> bool:
    return (
        isinstance(value, list)
        and (bool(value) or not nonempty)
        and all(_nonempty_text(item) for item in value)
        and len(value) == len(set(value))
    )


def _object_without_duplicate_keys(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def _loads_json(value: str) -> Any:
    return json.loads(value, object_pairs_hook=_object_without_duplicate_keys)


def _load_json_object(path: Path, label: str) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"{label} path must be a regular non-symlink file")
    try:
        value = _loads_json(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{label} is missing or malformed JSON") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label} schema requires a JSON object")
    return value


def _validate_sidecar(path: Path, label: str) -> None:
    sidecar = path.with_name(f"{path.name}.sha256")
    if sidecar.is_symlink() or not sidecar.is_file():
        raise ValueError(f"{label} hash sidecar is missing or unsafe")
    try:
        parts = sidecar.read_text(encoding="ascii").strip().split()
    except (OSError, UnicodeDecodeError) as exc:
        raise ValueError(f"{label} hash sidecar is unreadable") from exc
    if len(parts) != 2 or parts[1] != path.name or not _is_sha256(parts[0]):
        raise ValueError(f"{label} hash sidecar format or filename is invalid")
    if parts[0] != _sha256(path):
        raise ValueError(f"{label} bytes do not match hash sidecar digest")


def _safe_artifact_path(bundle: Path, value: Any, role: str) -> Path:
    if not _nonempty_text(value):
        raise ValueError(f"{role} path is missing")
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"{role} path is unsafe")
    path = bundle / relative
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"{role} path must be a regular non-symlink file")
    try:
        path.resolve(strict=True).relative_to(bundle.resolve(strict=True))
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        raise ValueError(f"{role} path escapes the candidate bundle") from exc
    return path


def _validate_provenance(value: Any) -> None:
    if not isinstance(value, dict):
        raise ValueError("manifest provenance must be an object")
    for key in (
        "model",
        "checkpoint",
        "segmentation_rule",
        "statistical_rule",
        "builder_revision",
    ):
        if not _nonempty_text(value.get(key)):
            raise ValueError(f"manifest provenance.{key} is missing")
    provenance_identity = " ".join(
        str(value.get(key, "")) for key in ("model", "checkpoint", "profile", "mode")
    ).casefold()
    if (
        ("mock" in value and value["mock"] is not False)
        or ("degraded" in value and value["degraded"] is not False)
        or any(
            marker in provenance_identity
            for marker in ("mock", "degraded")
        )
    ):
        raise ValueError("manifest provenance identifies mock or fixture data")
    if not _is_sha256(value.get("prompt_sha256")):
        raise ValueError("manifest provenance.prompt_sha256 is invalid")
    resolver = value.get("resolver")
    if (
        not isinstance(resolver, dict)
        or not _nonempty_text(resolver.get("version"))
        or not _is_sha256(resolver.get("configuration_sha256"))
    ):
        raise ValueError("manifest provenance.resolver is incomplete")
    corpus = value.get("corpus")
    source_hashes = corpus.get("source_hashes") if isinstance(corpus, dict) else None
    if (
        not isinstance(corpus, dict)
        or not _nonempty_text(corpus.get("path"))
        or not isinstance(source_hashes, dict)
        or not source_hashes
    ):
        raise ValueError("manifest provenance.corpus is incomplete")
    if "tfp" in str(corpus["path"]).casefold():
        raise ValueError("manifest provenance corpus path violates the core boundary")
    for relative, digest in source_hashes.items():
        if (
            not _nonempty_text(relative)
            or Path(relative).is_absolute()
            or ".." in Path(relative).parts
            or not _is_sha256(digest)
        ):
            raise ValueError("manifest provenance corpus source hash/path is invalid")
    _reject_field_specific_markers(value, role="manifest provenance")


def _validate_manifest(
    bundle: Path,
    *,
    require_manifest_v2: bool = False,
) -> tuple[dict[str, Any], dict[str, Path]]:
    if bundle.is_symlink() or not bundle.is_dir():
        raise ValueError("candidate bundle must be a regular directory")
    manifest_path = bundle / "manifest.json"
    manifest = _load_json_object(manifest_path, "manifest")
    _validate_sidecar(manifest_path, "manifest")

    schema_version = manifest.get("schema_version")
    if schema_version not in {MANIFEST_SCHEMA, MANIFEST_V2}:
        raise ValueError("manifest schema_version is unsupported")
    if require_manifest_v2 and schema_version != MANIFEST_V2:
        raise ValueError("manifest-v1 is historical and release-ineligible")
    if manifest.get("state") not in {
        "candidate",
        "release_candidate",
        "active",
        "last_known_good",
    }:
        raise ValueError("manifest state is quarantined or release-ineligible")
    if manifest.get("quarantined") is True:
        raise ValueError("manifest is quarantined")
    if manifest.get("release_eligibility") is False:
        raise ValueError("manifest is release-ineligible")
    if "degraded" in str(manifest.get("profile", "")).casefold():
        raise ValueError("manifest degraded profile is forbidden")
    _validate_provenance(manifest.get("provenance"))

    unsigned = {key: value for key, value in manifest.items() if key != "bundle_id"}
    try:
        expected_bundle_id = _sha256_bytes(_canonical_bytes(unsigned))
    except (TypeError, ValueError) as exc:
        raise ValueError("manifest contains non-canonical or non-finite JSON") from exc
    if manifest.get("bundle_id") != expected_bundle_id:
        raise ValueError("manifest bundle_id does not match canonical digest")

    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, dict):
        raise ValueError("manifest artifacts must be an object")
    if schema_version == MANIFEST_V2:
        paths, _counts = validate_v2_artifacts(bundle, manifest)
        for role, path in paths.items():
            _validate_sidecar(path, role)
        return manifest, paths
    roles = set(artifacts)
    missing = sorted(_REQUIRED_ROLES - roles)
    unknown = sorted(roles - _ALLOWED_ROLES)
    if missing:
        raise ValueError(f"manifest required role is missing: {', '.join(missing)}")
    if unknown:
        raise ValueError(f"manifest contains unknown artifact role: {', '.join(unknown)}")

    paths: dict[str, Path] = {}
    for role in sorted(roles):
        descriptor = artifacts[role]
        if not isinstance(descriptor, dict):
            raise ValueError(f"{role} manifest descriptor must be an object")
        if set(descriptor) != {"path", "sha256", "status"}:
            raise ValueError(f"{role} manifest descriptor schema is strict")
        if descriptor.get("status") != _ROLE_STATUS[role]:
            raise ValueError(f"{role} status is not release-eligible")
        path = _safe_artifact_path(bundle, descriptor.get("path"), role)
        digest = descriptor.get("sha256")
        if not _is_sha256(digest) or digest != _sha256(path):
            raise ValueError(f"{role} artifact hash/digest mismatch")
        _validate_sidecar(path, role)
        paths[role] = path
    return manifest, paths


def _candidate_snapshot(
    bundle: Path,
    artifact_paths: Mapping[str, Path],
) -> dict[str, str]:
    files = {
        "manifest": bundle / "manifest.json",
        "manifest_sidecar": bundle / "manifest.json.sha256",
    }
    for role, path in artifact_paths.items():
        files[f"artifact:{role}"] = path
        files[f"artifact_sidecar:{role}"] = path.with_name(f"{path.name}.sha256")
    return {label: _sha256(path) for label, path in sorted(files.items())}


def _load_jsonl(path: Path, role: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        raise ValueError(f"{role} JSONL is unreadable") from exc
    for line_number, raw in enumerate(lines, 1):
        if not raw.strip():
            continue
        try:
            row = _loads_json(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{role} invalid JSONL at line {line_number}") from exc
        if not isinstance(row, dict):
            raise ValueError(f"{role} schema requires object rows")
        try:
            _canonical_bytes(row)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{role} row contains non-finite or invalid JSON") from exc
        rows.append(row)
    if not rows:
        raise ValueError(f"{role} artifact is empty JSONL")
    return rows


def _validate_concept_id(value: Any) -> bool:
    if not _nonempty_text(value):
        return False
    if value.startswith("core."):
        body = value.removeprefix("core.")
        if not body or body.startswith(".") or body.endswith(".") or ".." in body:
            return False
        return all(
            character.isalnum() or character in {".", "-", "_"}
            for character in value
        )
    if not value.startswith("C-"):
        return False
    body = value.removeprefix("C-")
    return bool(body) and all(
        character.isalnum() or character in {"-", "_"} for character in body
    )


def _validate_concept_ids(values: Any, *, nonempty: bool) -> bool:
    return _text_list(values, nonempty=nonempty) and all(
        _validate_concept_id(value) for value in values
    )


def _validate_a_row(row: dict[str, Any]) -> None:
    required = {"normalized_form", "candidate_concept_ids"}
    optional = {"entry_id", "match_type"}
    if not required <= set(row) or not set(row) <= required | optional:
        raise ValueError("dict_a_matcher row schema is strict")
    if (
        not _nonempty_text(row["normalized_form"])
        or not _validate_concept_ids(row["candidate_concept_ids"], nonempty=True)
        or ("entry_id" in row and not _nonempty_text(row["entry_id"]))
        or ("match_type" in row and row["match_type"] not in _MATCH_TYPES)
    ):
        raise ValueError(
            "dict_a_matcher row schema or concept namespace is invalid"
        )


def _validate_b_row(row: dict[str, Any]) -> None:
    required = {"concept_id", "related_concept_ids"}
    optional = {"area_ids", "family_ids"}
    if not required <= set(row) or not set(row) <= required | optional:
        raise ValueError("dict_b_canonical row schema is strict")
    if (
        not _validate_concept_id(row["concept_id"])
        or not _validate_concept_ids(row["related_concept_ids"], nonempty=False)
        or ("area_ids" in row and not _text_list(row["area_ids"], nonempty=True))
        or ("family_ids" in row and not _text_list(row["family_ids"], nonempty=True))
    ):
        raise ValueError(
            f"dict_b_canonical row schema or concept namespace is invalid: "
            f"{row.get('concept_id')}"
        )


def _validate_c_row(row: dict[str, Any]) -> None:
    required = {"normalized_form", "candidate_concept_ids"}
    optional = {"priority"}
    if not required <= set(row) or not set(row) <= required | optional:
        raise ValueError("dict_c_runtime_conversion row schema is strict")
    if not _nonempty_text(row["normalized_form"]) or not _validate_concept_ids(
        row["candidate_concept_ids"], nonempty=True
    ) or (
        "priority" in row
        and (
            not _is_finite_number(row["priority"])
        )
    ):
        raise ValueError(
            "dict_c_runtime_conversion row schema or concept namespace is invalid"
        )


def _validate_d_row(row: dict[str, Any]) -> None:
    if set(row) != {
        "concept_id_a",
        "concept_id_b",
        "cooc_count",
        "npmi",
        "g2",
        "source_books",
        "agreement_with_b",
    }:
        raise ValueError("dict_d row schema is strict")
    if (
        not _validate_concept_id(row["concept_id_a"])
        or not _validate_concept_id(row["concept_id_b"])
        or row["concept_id_a"] >= row["concept_id_b"]
        or not isinstance(row["cooc_count"], int)
        or isinstance(row["cooc_count"], bool)
        or row["cooc_count"] <= 0
        or not _is_finite_number(row["npmi"])
        or not -1.0 <= float(row["npmi"]) <= 1.0
        or not _is_finite_number(row["g2"])
        or float(row["g2"]) < 0.0
        or not _text_list(row["source_books"], nonempty=True)
        or row["source_books"] != sorted(row["source_books"])
        or row["agreement_with_b"] not in {"agrees", "novel"}
    ):
        raise ValueError(
            "dict_d row schema or concept namespace is invalid: "
            f"{row.get('concept_id_a')}, {row.get('concept_id_b')}"
        )


def _validate_evidence_row(role: str, row: dict[str, Any]) -> None:
    valid = {
        "dict_a_proposal_evidence": (
            _nonempty_text(row.get("text"))
            and _is_finite_number(row.get("frequency"))
            and float(row["frequency"]) >= 0.0
        ),
        "dict_a_anchor_evidence": (
            _nonempty_text(row.get("text"))
            and _nonempty_text(row.get("normalized"))
        ),
        "dict_b_proposal_evidence": (
            _nonempty_text(row.get("proposed_concept_id"))
            and _nonempty_text(row.get("anchor"))
        ),
        "dict_b_authored_edge_provenance": (
            _nonempty_text(row.get("source"))
            and _nonempty_text(row.get("target"))
        ),
        "dict_c_source": (
            _nonempty_text(row.get("phrase"))
            and _nonempty_text(row.get("source"))
        ),
        "dict_c_intermediate": (
            _nonempty_text(row.get("phrase"))
            and _nonempty_text(row.get("anchor"))
        ),
    }.get(role, False)
    if not valid:
        raise ValueError(f"{role} evidence row schema is invalid")


def _reject_field_specific_markers(value: Any, *, role: str, path: str = "") -> None:
    if isinstance(value, str):
        identifier_path = role != "manifest provenance" and "/" in value
        if _FIELD_SPECIFIC_MARKER.search(value) or identifier_path:
            raise ValueError(
                f"{role} field-specific namespace/path/corpus marker at {path or 'row'}"
            )
    if isinstance(value, dict):
        for key, child in value.items():
            _reject_field_specific_markers(
                child,
                role=role,
                path=f"{path}.{key}" if path else str(key),
            )
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_field_specific_markers(
                child,
                role=role,
                path=f"{path}[{index}]",
            )


def _load_metrics(path: Path, role: str) -> dict[str, Any]:
    metrics = _load_json_object(path, role)
    if not metrics:
        raise ValueError("evaluation_metrics evidence must be non-empty")
    _assert_finite_tree(metrics, role)
    _reject_field_specific_markers(metrics, role=role)
    return metrics


def _validate_artifacts(paths: Mapping[str, Path]) -> dict[str, int]:
    rows_by_role = {
        role: _load_jsonl(path, role)
        for role, path in paths.items()
        if role != "evaluation_metrics"
    }
    metrics = (
        _load_metrics(paths["evaluation_metrics"], "evaluation_metrics")
        if "evaluation_metrics" in paths
        else None
    )
    validators = {
        "dict_a_matcher": _validate_a_row,
        "dict_b_canonical": _validate_b_row,
        "dict_c_runtime_conversion": _validate_c_row,
        "dict_d": _validate_d_row,
    }
    identities: dict[str, set[Any]] = {
        "dict_a_matcher": set(),
        "dict_b_canonical": set(),
        "dict_c_runtime_conversion": set(),
        "dict_d": set(),
    }
    for role in sorted(rows_by_role):
        for row in rows_by_role[role]:
            validator = validators.get(role)
            if validator is None:
                _validate_evidence_row(role, row)
            else:
                validator(row)
            _reject_field_specific_markers(row, role=role)
            if role in _EVIDENCE_ROLES:
                continue
            if role == "dict_a_matcher":
                identity: Any = row.get("entry_id")
                alternate = (
                    row["normalized_form"],
                    row.get("match_type", "exact"),
                )
                if (
                    (identity is not None and identity in identities[role])
                    or alternate in identities[role]
                ):
                    raise ValueError(f"{role} duplicate identity violates uniqueness")
                identities[role].add(alternate)
                if identity is not None:
                    identities[role].add(identity)
            elif role == "dict_b_canonical":
                identity = row["concept_id"]
                if identity in identities[role]:
                    raise ValueError(f"{role} duplicate concept_id violates uniqueness")
                identities[role].add(identity)
            elif role == "dict_c_runtime_conversion":
                identity = row["normalized_form"]
                if identity in identities[role]:
                    raise ValueError(f"{role} duplicate normalized_form violates uniqueness")
                identities[role].add(identity)
            else:
                identity = tuple(sorted((row["concept_id_a"], row["concept_id_b"])))
                if identity in identities[role]:
                    raise ValueError("dict_d duplicate pair violates uniqueness")
                identities[role].add(identity)

    concept_ids = {
        row["concept_id"] for row in rows_by_role["dict_b_canonical"]
    }
    references: list[tuple[str, str]] = []
    for row in rows_by_role["dict_b_canonical"]:
        references.extend(
            ("dict_b_canonical", concept_id)
            for concept_id in row["related_concept_ids"]
        )
    for role in ("dict_a_matcher", "dict_c_runtime_conversion"):
        for row in rows_by_role[role]:
            references.extend(
                (role, concept_id) for concept_id in row["candidate_concept_ids"]
            )
    for row in rows_by_role.get("dict_d", []):
        references.extend(
            [
                ("dict_d", row["concept_id_a"]),
                ("dict_d", row["concept_id_b"]),
            ]
        )
    missing = sorted(
        {f"{role}:{concept_id}" for role, concept_id in references if concept_id not in concept_ids}
    )
    if missing:
        raise ValueError(
            "runtime concept reference closure failed: " + ", ".join(missing)
        )
    counts = {role: len(rows) for role, rows in sorted(rows_by_role.items())}
    if metrics is not None:
        counts["evaluation_metrics"] = 1
    return dict(sorted(counts.items()))


def _assert_finite_tree(value: Any, path: str = "evaluation") -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"{path} contains a non-finite metric")
    if isinstance(value, dict):
        for key, child in value.items():
            _assert_finite_tree(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _assert_finite_tree(child, f"{path}[{index}]")


def _require_metric_map(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != _LIMIT_KEYS:
        raise ValueError(f"{label} metric schema is incomplete or contains extra metrics")
    for metric in ("accepted", "rejected", "coverage", "entropy"):
        if not _is_finite_number(value[metric]):
            raise ValueError(f"{label}.{metric} must be a finite metric")
    families = value["family_distribution"]
    if (
        not isinstance(families, dict)
        or not all(_nonempty_text(key) and _is_finite_number(item) for key, item in families.items())
    ):
        raise ValueError(f"{label}.family_distribution must contain finite metrics")
    return value


def _validate_sample_payload(value: Any, label: str) -> dict[str, Any]:
    required = {
        "accepted",
        "rejected",
        "coverage",
        "concept_weights",
        "family_activation",
        "span_resolutions",
    }
    if not isinstance(value, dict) or set(value) != required:
        raise ValueError(f"{label} sample payload schema is strict")
    for metric in ("accepted", "rejected"):
        if (
            not isinstance(value[metric], int)
            or isinstance(value[metric], bool)
            or value[metric] < 0
        ):
            raise ValueError(f"{label}.{metric} must be a non-negative integer")
    if (
        not _is_finite_number(value["coverage"])
        or not 0.0 <= float(value["coverage"]) <= 1.0
    ):
        raise ValueError(f"{label}.coverage must be finite and bounded")
    for field in ("concept_weights", "family_activation"):
        weights = value[field]
        if (
            not isinstance(weights, dict)
            or not all(
                _nonempty_text(key)
                and _is_finite_number(weight)
                and float(weight) >= 0.0
                for key, weight in weights.items()
            )
        ):
            raise ValueError(f"{label}.{field} must contain finite weights")
    if not isinstance(value["span_resolutions"], list):
        raise ValueError(f"{label}.span_resolutions must be a list")
    return value


def _deltas_match_recomputed(
    reported: Mapping[str, Any],
    baseline: Mapping[str, Any],
    candidate: Mapping[str, Any],
) -> bool:
    signed_matches: list[bool] = []
    for metric in ("accepted", "rejected", "coverage", "entropy"):
        recomputed = float(candidate[metric]) - float(baseline[metric])
        if not math.isclose(
            abs(float(reported[metric])),
            abs(recomputed),
            rel_tol=0.0,
            abs_tol=1e-12,
        ):
            return False
        if not math.isclose(recomputed, 0.0, rel_tol=0.0, abs_tol=1e-12):
            signed_matches.append(
                math.isclose(
                    float(reported[metric]),
                    recomputed,
                    rel_tol=0.0,
                    abs_tol=1e-12,
                )
            )
    families = set(baseline["family_distribution"]) | set(
        candidate["family_distribution"]
    )
    if set(reported["family_distribution"]) != families:
        return False
    for family_id in families:
        recomputed = float(candidate["family_distribution"].get(family_id, 0.0)) - float(
            baseline["family_distribution"].get(family_id, 0.0)
        )
        if not math.isclose(
            abs(float(reported["family_distribution"][family_id])),
            abs(recomputed),
            rel_tol=0.0,
            abs_tol=1e-12,
        ):
            return False
        if not math.isclose(recomputed, 0.0, rel_tol=0.0, abs_tol=1e-12):
            signed_matches.append(
                math.isclose(
                    float(reported["family_distribution"][family_id]),
                    recomputed,
                    rel_tol=0.0,
                    abs_tol=1e-12,
                )
            )
    return not signed_matches or all(signed_matches)


def _validate_same_bundle_diffs(sample: Mapping[str, Any]) -> None:
    for diff in sample["span_diffs"]:
        if (
            not isinstance(diff, dict)
            or diff.get("status") != "unchanged"
            or diff.get("baseline") != diff.get("candidate")
        ):
            raise ValueError("evaluation same-bundle span_diffs contain a change")

    expected_ambiguous: list[dict[str, Any]] = []
    for span in sample["candidate"]["span_resolutions"]:
        candidates = span.get("candidate_concepts") if isinstance(span, dict) else None
        if not isinstance(candidates, list) or len(candidates) <= 1:
            continue
        start = span.get("source_char_start")
        end = span.get("source_char_end")
        source_text = span.get("source_text_span")
        if not isinstance(start, int) or not isinstance(end, int) or not isinstance(
            source_text, str
        ):
            raise ValueError("evaluation same-bundle ambiguous span is malformed")
        expected_ambiguous.append(
            {
                "span_id": _sha256_bytes(
                    f"{sample['sample_id']}\0{start}\0{end}\0{source_text}".encode(
                        "utf-8"
                    )
                ),
                "source_char_start": start,
                "source_char_end": end,
                "candidate_concepts": candidates,
                "winning_concept_id": span.get("winning_concept_id"),
            }
        )
    if sample["ambiguous_candidate_spans"] != expected_ambiguous:
        raise ValueError(
            "evaluation same-bundle ambiguous_candidate_spans are forged"
        )


def _validate_evaluation(
    path: Path,
    candidate_bundle_id: str,
) -> dict[str, Any]:
    report = _load_json_object(path, "evaluation report")
    _assert_finite_tree(report)
    if report.get("schema_version") != EVALUATION_SCHEMA:
        raise ValueError("evaluation report schema_version is unsupported")
    report_sha256 = report.get("report_sha256")
    unsigned = {key: value for key, value in report.items() if key != "report_sha256"}
    if not _is_sha256(report_sha256) or report_sha256 != _sha256_bytes(
        _canonical_bytes(unsigned)
    ):
        raise ValueError("evaluation report_sha256 does not match canonical report")
    baseline = report.get("baseline")
    candidate = report.get("candidate")
    if (
        not isinstance(baseline, dict)
        or set(baseline) != {"bundle_id"}
        or not _is_sha256(baseline.get("bundle_id"))
        or not isinstance(candidate, dict)
        or set(candidate) != {"bundle_id"}
        or candidate.get("bundle_id") != candidate_bundle_id
    ):
        raise ValueError("evaluation candidate/baseline bundle binding is invalid")
    samples = report.get("samples")
    if not isinstance(samples, list) or not samples:
        raise ValueError("evaluation samples must be a non-empty ordered list")
    for ordinal, sample in enumerate(samples):
        if (
            not isinstance(sample, dict)
            or set(sample)
            != {
                "sample_id",
                "ordinal",
                "text_sha256",
                "baseline",
                "candidate",
                "span_diffs",
                "ambiguous_candidate_spans",
            }
            or sample.get("ordinal") != ordinal
            or not _is_sha256(sample.get("sample_id"))
            or not _is_sha256(sample.get("text_sha256"))
            or not isinstance(sample.get("span_diffs"), list)
            or not isinstance(sample.get("ambiguous_candidate_spans"), list)
        ):
            raise ValueError("evaluation sample identity or ordinal is not stable")
        baseline_payload = _validate_sample_payload(
            sample["baseline"],
            f"evaluation sample {ordinal} baseline",
        )
        candidate_payload = _validate_sample_payload(
            sample["candidate"],
            f"evaluation sample {ordinal} candidate",
        )
        if (
            baseline["bundle_id"] == candidate["bundle_id"]
            and baseline_payload != candidate_payload
        ):
            raise ValueError(
                f"evaluation sample {ordinal} identity payload does not match"
            )
    aggregate = report.get("aggregate")
    if not isinstance(aggregate, dict) or set(aggregate) != {
        "baseline",
        "candidate",
        "delta",
    }:
        raise ValueError("evaluation aggregate schema is invalid")
    baseline_metrics = _require_metric_map(aggregate["baseline"], "evaluation baseline")
    candidate_metrics = _require_metric_map(aggregate["candidate"], "evaluation candidate")
    delta_metrics = _require_metric_map(aggregate["delta"], "evaluation delta")
    if not _deltas_match_recomputed(
        delta_metrics,
        baseline_metrics,
        candidate_metrics,
    ):
        raise ValueError(
            "evaluation signed candidate-minus-baseline delta is forged "
            "or does not recompute"
        )
    if baseline["bundle_id"] == candidate["bundle_id"]:
        if report.get("weight_zero_identity") is not True:
            raise ValueError("evaluation same-bundle identity evidence is false")
        for sample in samples:
            _validate_same_bundle_diffs(sample)
        if baseline_metrics != candidate_metrics:
            raise ValueError("evaluation same-bundle metrics are not identical")
        scalar_deltas = [
            delta_metrics[key] for key in ("accepted", "rejected", "coverage", "entropy")
        ]
        family_deltas = list(delta_metrics["family_distribution"].values())
        if any(float(value) != 0.0 for value in scalar_deltas + family_deltas):
            raise ValueError("evaluation same-bundle identity has non-zero deltas")
    return report


def _validate_limits(
    path: Path,
    candidate_bundle_id: str,
    evaluation_report_sha256: str,
    expected_limits_sha256: str,
) -> tuple[dict[str, float], str]:
    limits = _load_json_object(path, "limits")
    _validate_sidecar(path, "limits")
    actual_limits_sha256 = _sha256(path)
    if set(limits) != {
        "schema_version",
        "candidate_bundle_id",
        "evaluation_report_sha256",
        "max_absolute_deltas",
    }:
        raise ValueError("limits schema is strict and complete")
    if limits.get("schema_version") != LIMITS_SCHEMA:
        raise ValueError("limits schema_version is unsupported")
    if limits.get("candidate_bundle_id") != candidate_bundle_id:
        raise ValueError("limits candidate bundle identity binding does not match")
    if limits.get("evaluation_report_sha256") != evaluation_report_sha256:
        raise ValueError("limits evaluation report identity binding does not match")
    if (
        not _is_sha256(expected_limits_sha256)
        or expected_limits_sha256 != actual_limits_sha256
    ):
        raise ValueError(
            "limits digest does not match independent expected_limits_sha256"
        )
    maxima = limits.get("max_absolute_deltas")
    if not isinstance(maxima, dict) or set(maxima) != _LIMIT_KEYS:
        raise ValueError("limits metric schema is incomplete or contains extra metrics")
    for metric, maximum in maxima.items():
        if not _is_finite_number(maximum) or float(maximum) < 0.0:
            raise ValueError(f"limits {metric} maximum must be finite and non-negative")
    return (
        {key: float(value) for key, value in maxima.items()},
        actual_limits_sha256,
    )


def _validate_deltas(report: Mapping[str, Any], limits: Mapping[str, float]) -> None:
    delta = report["aggregate"]["delta"]
    for metric in ("accepted", "rejected", "coverage", "entropy"):
        if abs(float(delta[metric])) > limits[metric]:
            raise ValueError(
                f"evaluation {metric} absolute delta exceeds frozen limit"
            )
    for family_id, value in sorted(delta["family_distribution"].items()):
        if abs(float(value)) > limits["family_distribution"]:
            raise ValueError(
                f"evaluation family {family_id} absolute delta exceeds frozen limit"
            )


def _default_subprocess_runner(
    command: list[str],
    **kwargs: Any,
) -> subprocess.CompletedProcess[str]:
    options = dict(kwargs)
    options.setdefault("timeout", _SUBPROCESS_TIMEOUT_SECONDS)
    return subprocess.run(command, **options)


def _default_boundary_checker(repo_root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(repo_root / "tools/check_core_calibration_boundary.py"),
        ],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
        timeout=_SUBPROCESS_TIMEOUT_SECONDS,
    )


def _validate_boundary(
    repo_root: Path,
    boundary_checker: BoundaryChecker,
) -> str:
    try:
        result = boundary_checker(repo_root)
    except subprocess.TimeoutExpired as exc:
        raise ValueError("core boundary checker timed out") from exc
    if not isinstance(result, subprocess.CompletedProcess):
        raise ValueError("boundary checker did not return process evidence")
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "no diagnostic output").strip()
        raise ValueError(f"core boundary checker failed: {detail}")
    return (result.stderr or result.stdout or "boundary checker passed").strip()


def _readiness_commands(repo_root: Path) -> list[tuple[str, list[str]]]:
    return [
        (
            "matcher",
            [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "tests/lexical_concept/test_matcher.py",
                "tests/lexical_concept/test_matcher_caps.py",
            ],
        ),
        (
            "resolver",
            [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "tests/lexical_concept/test_resolver.py",
                "tests/lexical_concept/test_resolver_output_schema.py",
            ],
        ),
        (
            "evaluate",
            [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "tests/dict_calibration/test_evaluate_bundles.py",
            ],
        ),
        (
            "export",
            [
                sys.executable,
                "-m",
                "tools.dict_calibration.resolved_export",
                "--help",
            ],
        ),
    ]


def _validate_readiness(
    repo_root: Path,
    subprocess_runner: ProcessRunner,
) -> dict[str, str]:
    evidence: dict[str, str] = {}
    for name, command in _readiness_commands(repo_root):
        try:
            result = subprocess_runner(
                command,
                cwd=str(repo_root),
                capture_output=True,
                text=True,
                check=False,
                timeout=_SUBPROCESS_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired as exc:
            raise ValueError(f"{name} readiness evidence timed out") from exc
        if not isinstance(result, subprocess.CompletedProcess):
            raise ValueError(f"{name} readiness probe returned no process evidence")
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "no diagnostic output").strip()
            raise ValueError(f"{name} readiness evidence failed: {detail}")
        evidence[name] = (result.stdout or result.stderr or "passed").strip()
    return evidence


def _check(
    check_id: str,
    passed: bool,
    reason: str,
    evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "pass": passed,
        "reason": reason,
        "evidence": dict(evidence or {}),
    }


def _failed_verdict(
    check_id: str,
    reason: str,
    *,
    candidate_bundle_id: str | None = None,
    report_sha256: str | None = None,
    limits_sha256: str | None = None,
    checks: Sequence[dict[str, Any]] = (),
) -> dict[str, Any]:
    verdict = {
        "schema_version": GATE_SCHEMA,
        "pass": False,
        "candidate": {"bundle_id": candidate_bundle_id},
        "evaluation": {"report_sha256": report_sha256},
        "limits_sha256": limits_sha256,
        "checks": sorted(
            [*checks, _check(check_id, False, reason)],
            key=lambda item: item["check_id"],
        ),
    }
    verdict["verdict_sha256"] = _sha256_bytes(_canonical_bytes(verdict))
    return verdict


def evaluate_core_pack(
    *,
    bundle: Path | str,
    evaluation: Path | str,
    limits: Path | str,
    expected_limits_sha256: str,
    repo_root: Path | str,
    subprocess_runner: ProcessRunner = _default_subprocess_runner,
    boundary_checker: BoundaryChecker = _default_boundary_checker,
    require_manifest_v2: bool = False,
) -> dict[str, Any]:
    """Evaluate one immutable candidate pack and return a deterministic verdict."""
    bundle_path = Path(bundle)
    evaluation_path = Path(evaluation)
    limits_path = Path(limits)
    repo_path = Path(repo_root)
    checks: list[dict[str, Any]] = []
    candidate_bundle_id: str | None = None
    report_sha256: str | None = None
    limits_sha256: str | None = None
    candidate_snapshot: dict[str, str] | None = None

    try:
        manifest, artifact_paths = _validate_manifest(
            bundle_path,
            require_manifest_v2=require_manifest_v2,
        )
        candidate_bundle_id = manifest["bundle_id"]
        checks.append(
            _check(
                "01_manifest",
                True,
                "manifest identity, sidecar, roles, paths, and hashes passed",
                {"artifact_roles": sorted(artifact_paths)},
            )
        )
    except (OSError, TypeError, ValueError) as exc:
        return _failed_verdict("01_manifest", str(exc))

    try:
        validation_paths = artifact_paths
        if manifest["schema_version"] == MANIFEST_V2:
            validation_paths = {
                role: path
                for role, path in artifact_paths.items()
                if role in _REQUIRED_ROLES or role == "evaluation_metrics"
            }
        row_counts = _validate_artifacts(validation_paths)
        candidate_snapshot = _candidate_snapshot(bundle_path, artifact_paths)
        checks.append(
            _check(
                "02_artifacts",
                True,
                "artifact schemas, uniqueness, and reference closure passed",
                {"row_counts": row_counts},
            )
        )
    except (OSError, TypeError, ValueError) as exc:
        return _failed_verdict(
            "02_artifacts",
            str(exc),
            candidate_bundle_id=candidate_bundle_id,
            checks=checks,
        )

    try:
        report = _validate_evaluation(evaluation_path, candidate_bundle_id)
        report_sha256 = report["report_sha256"]
        checks.append(
            _check(
                "03_evaluation",
                True,
                "evaluation binding, identity, samples, metrics, and hash passed",
                {
                    "report_sha256": report_sha256,
                    "sample_count": len(report["samples"]),
                },
            )
        )
    except (OSError, TypeError, ValueError) as exc:
        return _failed_verdict(
            "03_evaluation",
            str(exc),
            candidate_bundle_id=candidate_bundle_id,
            checks=checks,
        )

    try:
        frozen_limits, limits_sha256 = _validate_limits(
            limits_path,
            candidate_bundle_id,
            report_sha256,
            expected_limits_sha256,
        )
        checks.append(
            _check(
                "04_limits",
                True,
                "frozen limits schema and finite inclusive maxima passed",
                {
                    "limits_sha256": limits_sha256,
                    "metrics": sorted(frozen_limits),
                },
            )
        )
    except (OSError, TypeError, ValueError) as exc:
        return _failed_verdict(
            "04_limits",
            str(exc),
            candidate_bundle_id=candidate_bundle_id,
            report_sha256=report_sha256,
            limits_sha256=limits_sha256,
            checks=checks,
        )

    try:
        _validate_deltas(report, frozen_limits)
        checks.append(
            _check(
                "05_deltas",
                True,
                "all scalar and per-family deltas are within inclusive limits",
            )
        )
    except (TypeError, ValueError) as exc:
        return _failed_verdict(
            "05_deltas",
            str(exc),
            candidate_bundle_id=candidate_bundle_id,
            report_sha256=report_sha256,
            limits_sha256=limits_sha256,
            checks=checks,
        )

    try:
        boundary_evidence = _validate_boundary(repo_path, boundary_checker)
        checks.append(
            _check(
                "06_boundary",
                True,
                "dedicated core/default boundary checker passed",
                {"output": boundary_evidence},
            )
        )
    except (OSError, TypeError, ValueError) as exc:
        return _failed_verdict(
            "06_boundary",
            str(exc),
            candidate_bundle_id=candidate_bundle_id,
            report_sha256=report_sha256,
            limits_sha256=limits_sha256,
            checks=checks,
        )

    try:
        readiness_evidence = _validate_readiness(repo_path, subprocess_runner)
        checks.append(
            _check(
                "07_readiness",
                True,
                "matcher, resolver, evaluation, and export readiness evidence passed",
                readiness_evidence,
            )
        )
    except (OSError, TypeError, ValueError) as exc:
        return _failed_verdict(
            "07_readiness",
            str(exc),
            candidate_bundle_id=candidate_bundle_id,
            report_sha256=report_sha256,
            limits_sha256=limits_sha256,
            checks=checks,
        )

    try:
        final_manifest, final_paths = _validate_manifest(
            bundle_path,
            require_manifest_v2=require_manifest_v2,
        )
        final_validation_paths = final_paths
        if final_manifest["schema_version"] == MANIFEST_V2:
            final_validation_paths = {
                role: path
                for role, path in final_paths.items()
                if role in _REQUIRED_ROLES or role == "evaluation_metrics"
            }
        _validate_artifacts(final_validation_paths)
        final_snapshot = _candidate_snapshot(bundle_path, final_paths)
        if (
            final_manifest["bundle_id"] != candidate_bundle_id
            or candidate_snapshot != final_snapshot
        ):
            raise ValueError(
                "candidate manifest or artifact snapshot changed during callbacks"
            )
        final_report = _validate_evaluation(evaluation_path, candidate_bundle_id)
        if final_report != report:
            raise ValueError("evaluation report changed during callbacks")
        _validate_limits(
            limits_path,
            candidate_bundle_id,
            report_sha256,
            expected_limits_sha256,
        )
        checks.append(
            _check(
                "08_revalidation",
                True,
                "final candidate, evaluation, and limits revalidation passed",
            )
        )
    except (OSError, TypeError, ValueError) as exc:
        return _failed_verdict(
            "08_revalidation",
            f"candidate revalidation failed: {exc}",
            candidate_bundle_id=candidate_bundle_id,
            report_sha256=report_sha256,
            limits_sha256=limits_sha256,
            checks=checks,
        )

    verdict = {
        "schema_version": GATE_SCHEMA,
        "pass": all(check["pass"] for check in checks),
        "candidate": {"bundle_id": candidate_bundle_id},
        "evaluation": {"report_sha256": report_sha256},
        "limits_sha256": limits_sha256,
        "checks": sorted(checks, key=lambda item: item["check_id"]),
    }
    verdict["verdict_sha256"] = _sha256_bytes(_canonical_bytes(verdict))
    return verdict
