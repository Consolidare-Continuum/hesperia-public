# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""Task 10 — Freeze calibrated dicts + metrics under assets/calibration/dicts/vX/."""

from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .jsonl_util import write_json


SCHEMA_VERSION = "hesperia.dict_calibration.freeze_manifest.v1"

ArtifactSpec = tuple[str, str, str, str]

REQUIRED_ARTIFACTS: tuple[ArtifactSpec, ...] = (
    ("dict_a_matcher", "dict_a_engine.jsonl", "dict_a.jsonl", "matcher_ready"),
    (
        "dict_a_proposal_evidence",
        "dict_a_candidates.jsonl",
        "evidence/dict_a_candidates.jsonl",
        "proposal_evidence",
    ),
    (
        "dict_a_anchor_evidence",
        "dict_a_normalized.jsonl",
        "evidence/dict_a_normalized.jsonl",
        "anchor_evidence",
    ),
    ("dict_b_canonical", "dict_b_anchored.jsonl", "dict_b.jsonl", "canonical"),
    (
        "dict_b_proposal_evidence",
        "dict_b_draft.jsonl",
        "evidence/dict_b_draft.jsonl",
        "proposal_evidence",
    ),
    (
        "dict_b_authored_edge_provenance",
        "dict_b_authored_edges.jsonl",
        "evidence/dict_b_authored_edges.jsonl",
        "authored_edge_provenance",
    ),
    (
        "dict_c_source",
        "dict_c_source.jsonl",
        "evidence/dict_c_source.jsonl",
        "source_evidence",
    ),
    (
        "dict_c_intermediate",
        "dict_c_intermediate.jsonl",
        "evidence/dict_c_intermediate.jsonl",
        "intermediate_evidence",
    ),
    (
        "dict_c_runtime_conversion",
        "dict_c_runtime.jsonl",
        "dict_c.jsonl",
        "matcher_ready",
    ),
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_sha256(path: Path) -> None:
    sidecar = path.with_name(f"{path.name}.sha256")
    sidecar.write_text(f"{_sha256(path)}  {path.name}\n", encoding="ascii")


def _write_canonical_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _is_sha256(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def _require_text(provenance: dict[str, Any], key: str) -> None:
    if not isinstance(provenance.get(key), str) or not provenance[key].strip():
        raise ValueError(f"provenance.{key} must be non-empty text")


def _safe_relative_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute() or not path.parts or ".." in path.parts:
        raise ValueError(f"provenance.corpus.source_hashes path is unsafe: {value}")
    return path


def _validate_provenance(provenance: dict[str, Any]) -> None:
    if not isinstance(provenance, dict) or not provenance:
        raise ValueError("provenance must be a non-empty object")
    for key in (
        "model",
        "checkpoint",
        "segmentation_rule",
        "statistical_rule",
        "builder_revision",
    ):
        _require_text(provenance, key)
    if not _is_sha256(provenance.get("prompt_sha256")):
        raise ValueError("provenance.prompt_sha256 must be a SHA-256 digest")

    corpus = provenance.get("corpus")
    if not isinstance(corpus, dict):
        raise ValueError("provenance.corpus must be an object")
    _require_text(corpus, "path")
    source_hashes = corpus.get("source_hashes")
    if not isinstance(source_hashes, dict) or not source_hashes:
        raise ValueError("provenance.corpus.source_hashes must be non-empty")
    if not all(
        isinstance(path, str) and path and _is_sha256(digest)
        for path, digest in source_hashes.items()
    ):
        raise ValueError("provenance.corpus.source_hashes contains an invalid entry")
    corpus_path = Path(corpus["path"])
    if not corpus_path.is_dir():
        raise ValueError(f"provenance.corpus.path is not a directory: {corpus_path}")
    corpus_root = corpus_path.resolve()
    for source_key, expected_sha256 in source_hashes.items():
        relative_path = _safe_relative_path(source_key)
        source_path = corpus_root / relative_path
        if (
            not source_path.is_file()
            or source_path.is_symlink()
            or not source_path.resolve().is_relative_to(corpus_root)
        ):
            raise ValueError(
                f"provenance corpus source path is invalid: {source_key}"
            )
        actual_sha256 = _sha256(source_path)
        if actual_sha256 != expected_sha256:
            raise ValueError(
                f"{source_key} source hash/digest mismatch: "
                f"expected {expected_sha256}, got {actual_sha256}"
            )

    resolver = provenance.get("resolver")
    if not isinstance(resolver, dict):
        raise ValueError("provenance.resolver must be an object")
    _require_text(resolver, "version")
    if not _is_sha256(resolver.get("configuration_sha256")):
        raise ValueError(
            "provenance.resolver.configuration_sha256 must be a SHA-256 digest"
        )


def _non_empty_text(row: dict[str, Any], key: str) -> bool:
    return isinstance(row.get(key), str) and bool(row[key].strip())


def _non_empty_text_list(row: dict[str, Any], key: str) -> bool:
    value = row.get(key)
    return (
        isinstance(value, list)
        and bool(value)
        and all(isinstance(item, str) and bool(item.strip()) for item in value)
    )


def _text_list(row: dict[str, Any], key: str) -> bool:
    value = row.get(key)
    return isinstance(value, list) and all(
        isinstance(item, str) and bool(item.strip()) for item in value
    )


def _validate_artifact_row(role: str, row: dict[str, Any]) -> None:
    valid = {
        "dict_a_matcher": (
            _non_empty_text(row, "normalized_form")
            and _non_empty_text_list(row, "candidate_concept_ids")
        ),
        "dict_a_proposal_evidence": (
            _non_empty_text(row, "text")
            and isinstance(row.get("frequency"), (int, float))
        ),
        "dict_a_anchor_evidence": (
            _non_empty_text(row, "text") and _non_empty_text(row, "normalized")
        ),
        "dict_b_canonical": (
            _non_empty_text(row, "concept_id")
            and _text_list(row, "related_concept_ids")
        ),
        "dict_b_proposal_evidence": (
            _non_empty_text(row, "proposed_concept_id")
            and _non_empty_text(row, "anchor")
        ),
        "dict_b_authored_edge_provenance": (
            _non_empty_text(row, "source") and _non_empty_text(row, "target")
        ),
        "dict_c_source": (
            _non_empty_text(row, "phrase") and _non_empty_text(row, "source")
        ),
        "dict_c_intermediate": (
            _non_empty_text(row, "phrase") and _non_empty_text(row, "anchor")
        ),
        "dict_c_runtime_conversion": (
            _non_empty_text(row, "normalized_form")
            and _non_empty_text_list(row, "candidate_concept_ids")
        ),
        "dict_d": True,
    }.get(role, False)
    if not valid:
        raise ValueError(f"row does not satisfy the {role} schema")


def _validate_jsonl(path: Path, role: str, source_name: str) -> None:
    row_count = 0
    try:
        for line_number, raw in enumerate(
            path.read_text(encoding="utf-8").splitlines(),
            start=1,
        ):
            if not raw.strip():
                continue
            row = json.loads(raw)
            if not isinstance(row, dict):
                raise ValueError(f"line {line_number} is not an object")
            _validate_artifact_row(role, row)
            row_count += 1
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"{source_name} ({role}) is invalid JSONL: {exc}") from exc
    if row_count == 0:
        raise ValueError(f"{source_name} ({role}) is empty JSONL")


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _ensure_empty_destination(version_dir: Path) -> bool:
    if not version_dir.exists():
        return False
    if not version_dir.is_dir() or any(version_dir.iterdir()):
        raise FileExistsError(f"refusing to overwrite non-empty destination: {version_dir}")
    return True


def _copy_artifact(
    work_dir: Path,
    build_dir: Path,
    spec: ArtifactSpec,
) -> tuple[str, dict[str, str]]:
    role, source_name, destination_name, status = spec
    source = work_dir / source_name
    if not source.is_file():
        raise FileNotFoundError(f"required {role} artifact missing: {source}")
    if source.is_symlink():
        raise ValueError(f"{source_name} must not be a symlink")
    destination = build_dir / destination_name
    destination.parent.mkdir(parents=True, exist_ok=True)
    source_sha256 = _sha256(source)
    shutil.copy2(source, destination)
    if _sha256(source) != source_sha256 or _sha256(destination) != source_sha256:
        raise ValueError(f"{source_name} changed while the bundle was frozen")
    if source.suffix == ".jsonl":
        _validate_jsonl(destination, role, source_name)
    _write_sha256(destination)
    return role, {
        "path": destination_name,
        "sha256": _sha256(destination),
        "status": status,
    }


def _source_snapshot(work_dir: Path) -> dict[str, str]:
    snapshot: dict[str, str] = {}
    for role, source_name, _destination_name, _status in REQUIRED_ARTIFACTS:
        source = work_dir / source_name
        if not source.is_file():
            raise FileNotFoundError(f"required {role} artifact missing: {source}")
        if source.is_symlink():
            raise ValueError(f"{source_name} must not be a symlink")
        snapshot[source_name] = _sha256(source)
    return snapshot


def _verify_source_snapshot(work_dir: Path, snapshot: dict[str, str]) -> None:
    changed = [
        source_name
        for source_name, expected_sha256 in snapshot.items()
        if not (work_dir / source_name).is_file()
        or (work_dir / source_name).is_symlink()
        or _sha256(work_dir / source_name) != expected_sha256
    ]
    if changed:
        raise ValueError(
            "source generation changed during freeze: " + ", ".join(sorted(changed))
        )


def _corpus_snapshot(provenance: dict[str, Any]) -> dict[Path, str]:
    corpus = provenance["corpus"]
    corpus_root = Path(corpus["path"]).resolve()
    return {
        corpus_root / _safe_relative_path(source_key): expected_sha256
        for source_key, expected_sha256 in corpus["source_hashes"].items()
    }


def _verify_non_artifact_inputs(
    evaluation_source: Path,
    evaluation_sha256: str,
    corpus_sources: dict[Path, str],
) -> None:
    if (
        not evaluation_source.is_file()
        or evaluation_source.is_symlink()
        or _sha256(evaluation_source) != evaluation_sha256
    ):
        raise ValueError("evaluation input changed during freeze")
    changed_corpus = [
        path
        for path, expected_sha256 in corpus_sources.items()
        if not path.is_file()
        or path.is_symlink()
        or _sha256(path) != expected_sha256
    ]
    if changed_corpus:
        raise ValueError(
            "corpus input generation changed during freeze: "
            + ", ".join(str(path) for path in sorted(changed_corpus))
        )


def _legacy_freeze(
    work_dir: Path,
    version_dir: Path,
    evaluation_path: Path | None,
) -> None:
    version_dir.mkdir(parents=True, exist_ok=True)

    def cp(name: str, dest: str) -> None:
        src = work_dir / name
        if src.exists():
            shutil.copy2(src, version_dir / dest)

    cp("dict_a_candidates.jsonl", "dict_a_candidates.jsonl")
    cp("dict_a_normalized.jsonl", "dict_a_normalized.jsonl")
    cp("dict_b_draft.jsonl", "dict_b_draft.jsonl")
    cp("dict_b_anchored.jsonl", "dict_b.jsonl")
    cp("dict_a_to_b_links.jsonl", "links.jsonl")
    if (work_dir / "dict_a_to_b_links_patched.jsonl").exists():
        cp("dict_a_to_b_links_patched.jsonl", "links.jsonl")

    eng = work_dir / "dict_a_engine.jsonl"
    if eng.exists():
        shutil.copy2(eng, version_dir / "dict_a.jsonl")

    evp = evaluation_path or (work_dir / "evaluation_run.json")
    metrics: dict[str, Any] = {}
    if evp.exists():
        metrics = json.loads(evp.read_text(encoding="utf-8"))
    write_json(version_dir / "metrics.json", metrics)


def freeze(
    work_dir: Path,
    version_dir: Path,
    *,
    evaluation_path: Path | None = None,
    provenance: dict[str, Any] | None = None,
    dict_d_validator: Callable[[Path], bool | str] | None = None,
) -> None:
    work_dir = work_dir.resolve()
    version_dir = version_dir.resolve()
    destination_existed = _ensure_empty_destination(version_dir)
    if provenance is None:
        _legacy_freeze(work_dir, version_dir, evaluation_path)
        return

    _validate_provenance(provenance)
    evaluation_source = evaluation_path or (work_dir / "evaluation_run.json")
    if not evaluation_source.is_file():
        raise FileNotFoundError(f"required evaluation evidence missing: {evaluation_source}")
    if evaluation_source.is_symlink():
        raise ValueError("evaluation evidence must not be a symlink")
    source_snapshot = _source_snapshot(work_dir)
    evaluation_sha256 = _sha256(evaluation_source)
    corpus_sources = _corpus_snapshot(provenance)

    dict_d_source = work_dir / "dict_d.jsonl"
    validated_dict_d_sha256: str | None = None
    if dict_d_source.exists():
        if dict_d_validator is None:
            raise ValueError("Dict D requires a successful strict validator")
        before_validation = _sha256(dict_d_source)
        validation_result = dict_d_validator(dict_d_source)
        after_validation = _sha256(dict_d_source)
        if not validation_result:
            raise ValueError("Dict D requires a successful strict validator")
        if before_validation != after_validation:
            raise ValueError("Dict D changed during validator execution")
        if isinstance(validation_result, str) and validation_result != after_validation:
            raise ValueError("Dict D validator digest does not match validated bytes")
        validated_dict_d_sha256 = after_validation

    version_dir.parent.mkdir(parents=True, exist_ok=True)
    build_dir = Path(
        tempfile.mkdtemp(prefix=f".{version_dir.name}.freeze-", dir=version_dir.parent)
    )
    try:
        artifacts = dict(
            _copy_artifact(work_dir, build_dir, spec) for spec in REQUIRED_ARTIFACTS
        )

        metrics = json.loads(evaluation_source.read_text(encoding="utf-8"))
        metrics_path = build_dir / "metrics.json"
        _write_canonical_json(metrics_path, metrics)
        _write_sha256(metrics_path)
        artifacts["evaluation_metrics"] = {
            "path": "metrics.json",
            "sha256": _sha256(metrics_path),
            "status": "evaluation_evidence",
        }

        if dict_d_source.exists():
            role, entry = _copy_artifact(
                work_dir,
                build_dir,
                ("dict_d", "dict_d.jsonl", "dict_d.jsonl", "validated_optional"),
            )
            if entry["sha256"] != validated_dict_d_sha256:
                raise ValueError("Dict D changed after validation; digest mismatch")
            artifacts[role] = entry

        _verify_source_snapshot(work_dir, source_snapshot)
        _verify_non_artifact_inputs(
            evaluation_source,
            evaluation_sha256,
            corpus_sources,
        )
        manifest_payload = {
            "schema_version": SCHEMA_VERSION,
            "state": "candidate",
            "supersedes": None,
            "artifacts": artifacts,
            "provenance": provenance,
        }
        manifest = {
            **manifest_payload,
            "bundle_id": hashlib.sha256(_canonical_bytes(manifest_payload)).hexdigest(),
        }
        manifest_path = build_dir / "manifest.json"
        _write_canonical_json(manifest_path, manifest)
        _write_sha256(manifest_path)

        for directory in [build_dir, *build_dir.rglob("*")]:
            if directory.is_dir():
                directory.chmod(0o755)
        if destination_existed:
            version_dir.rmdir()
        build_dir.replace(version_dir)
    except Exception:
        shutil.rmtree(build_dir, ignore_errors=True)
        raise
