# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""Fsync-backed atomic release freeze for CORE-D2 candidates."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from .core_candidate import (
    _no_duplicate_keys,
    _reject_constant,
    canonical_bytes,
    materialize_candidate,
    sha256_bytes,
    sha256_file,
)
from .generation_ledger import load_generation_ledger


MANIFEST_SCHEMA = "hesperia.dict_calibration.freeze_manifest.v2"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
ROLE_STATUS = {
    "dict_a_matcher": "matcher_ready",
    "dict_b_canonical": "canonical",
    "dict_b_proposal_evidence": "proposal_evidence",
    "dict_b_authored_edge_provenance": "authored_edge_provenance",
    "dict_c_source": "source_evidence",
    "dict_c_intermediate": "intermediate_evidence",
    "dict_c_runtime_conversion": "matcher_ready",
}


def _identity_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _git_snapshot() -> tuple[str, bool]:
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return commit, not bool(status)


def _validate_digest(value: str, label: str) -> None:
    if len(value) != 64 or value != value.casefold():
        raise ValueError(f"{label} must be a lowercase SHA-256 digest")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ValueError(f"{label} must be a lowercase SHA-256 digest") from exc


def _load_metrics_bytes(raw: bytes) -> dict[str, Any]:
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_no_duplicate_keys,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError("evaluation metrics are malformed") from exc
    if not isinstance(value, dict) or not value:
        raise ValueError("evaluation metrics must be a non-empty object")
    canonical_bytes(value)
    return value


def _load_metrics(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise ValueError("evaluation metrics must be a regular non-symlink file")
    return _load_metrics_bytes(path.read_bytes())


def _write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())


def _write_sidecar(path: Path) -> None:
    _write(
        path.with_name(f"{path.name}.sha256"),
        f"{sha256_file(path)}  {path.name}\n".encode("ascii"),
    )


def _fsync_tree(root: Path) -> None:
    directories = [root, *(path for path in root.rglob("*") if path.is_dir())]
    for directory in sorted(directories, key=lambda path: len(path.parts), reverse=True):
        descriptor = os.open(directory, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


def _immutable_tree(root: Path) -> None:
    for path in root.rglob("*"):
        path.chmod(0o555 if path.is_dir() else 0o444)
    root.chmod(0o555)


def _provenance(ledger: dict[str, Any], ledger_sha256: str) -> dict[str, Any]:
    configuration = ledger["configuration"]
    required = (
        "resolver_version",
        "resolver_configuration_sha256",
        "segmentation_rule",
        "statistical_rule",
    )
    if any(not isinstance(configuration.get(key), str) or not configuration[key] for key in required):
        raise ValueError("generation ledger configuration lacks release identities")
    _validate_digest(
        configuration["resolver_configuration_sha256"],
        "resolver_configuration_sha256",
    )
    return {
        "generation_id": ledger["generation_id"],
        "generation_ledger_sha256": ledger_sha256,
        "corpus": {
            "path": ledger["corpus_root"],
            "source_hashes": ledger["source_hashes"],
        },
        "model": f"{ledger['model_provider']}:{ledger['model_id']}",
        "checkpoint": ledger["checkpoint_id"],
        "prompt_sha256": ledger["prompt_sha256"],
        "resolver": {
            "version": configuration["resolver_version"],
            "configuration_sha256": configuration[
                "resolver_configuration_sha256"
            ],
        },
        "segmentation_rule": configuration["segmentation_rule"],
        "statistical_rule": configuration["statistical_rule"],
        "builder_revision": ledger["git_commit"],
    }


def _validate_built_bundle(bundle: Path) -> dict[str, Any]:
    manifest_path = bundle / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != MANIFEST_SCHEMA:
        raise ValueError("release manifest v2 is required")
    unsigned = {key: value for key, value in manifest.items() if key != "bundle_id"}
    if manifest.get("bundle_id") != sha256_bytes(_identity_bytes(unsigned)):
        raise ValueError("release bundle identity does not recompute")
    if (
        bundle / "manifest.json.sha256"
    ).read_text(encoding="ascii").split()[0] != sha256_file(manifest_path):
        raise ValueError("release manifest sidecar does not match")
    for role, descriptor in manifest["artifacts"].items():
        path = bundle / descriptor["path"]
        if path.is_symlink() or not path.is_file() or sha256_file(path) != descriptor["sha256"]:
            raise ValueError(f"{role} artifact digest does not recompute")
        actual_rows = (
            1
            if path.suffix == ".json"
            else len(path.read_text(encoding="utf-8").splitlines())
        )
        if descriptor["row_count"] != actual_rows:
            raise ValueError(f"{role} row_count does not recompute")
        if role == "dict_b_authored_edge_provenance":
            status = descriptor.get("evidence_status")
            if actual_rows == 0 and (
                status != "truthful_zero"
                or path.read_bytes()
                or descriptor["sha256"] != sha256_bytes(b"")
            ):
                raise ValueError("truthful-zero authored-edge descriptor is false")
            if actual_rows > 0 and status != "present":
                raise ValueError("non-zero authored-edge evidence status is false")
    return manifest


def freeze_core_candidate(
    *,
    producer_dir: Path,
    generation_ledger: Path,
    expected_ledger_sha256: str,
    evaluation_metrics: Path,
    destination: Path,
) -> dict[str, Any]:
    """Build and atomically publish one immutable manifest-v2 candidate."""
    producer_dir = producer_dir.resolve(strict=True)
    generation_ledger = generation_ledger.resolve(strict=True)
    evaluation_metrics = evaluation_metrics.resolve(strict=True)
    destination = destination.absolute()
    _validate_digest(expected_ledger_sha256, "generation-ledger-sha256")
    if sha256_file(generation_ledger) != expected_ledger_sha256:
        raise ValueError("generation ledger digest does not match independent pin")
    if destination.exists() and (
        not destination.is_dir() or any(destination.iterdir())
    ):
        raise ValueError("release destination must be absent or empty")
    destination.parent.mkdir(parents=True, exist_ok=True)
    git_snapshot = _git_snapshot()
    ledger = load_generation_ledger(generation_ledger, git_snapshot=git_snapshot)
    metrics_source_bytes = evaluation_metrics.read_bytes()
    _load_metrics_bytes(metrics_source_bytes)
    ledger_bytes = generation_ledger.read_bytes()
    producer_initial = {
        path.name: sha256_file(path)
        for path in producer_dir.iterdir()
        if path.is_file() and not path.is_symlink()
    }
    staging = Path(
        tempfile.mkdtemp(
            prefix=f".{destination.name}.freeze-",
            dir=destination.parent,
        )
    )
    published_destination = False
    try:
        materialized = materialize_candidate(producer_dir, staging)
        ledger_target = staging / "evidence/generation_ledger.json"
        metrics_target = staging / "metrics.json"
        _write(ledger_target, ledger_bytes)
        _write(metrics_target, metrics_source_bytes)
        artifacts: dict[str, dict[str, Any]] = {}
        for role, descriptor in materialized["artifacts"].items():
            artifacts[role] = {
                **descriptor,
                "status": ROLE_STATUS[role],
            }
        edge = artifacts["dict_b_authored_edge_provenance"]
        edge["evidence_status"] = materialized["authored_edge_evidence_status"]
        artifacts["generation_ledger"] = {
            "path": "evidence/generation_ledger.json",
            "row_count": 1,
            "sha256": sha256_file(ledger_target),
            "status": "generation_evidence",
        }
        artifacts["evaluation_metrics"] = {
            "path": "metrics.json",
            "row_count": 1,
            "sha256": sha256_file(metrics_target),
            "status": "evaluation_evidence",
        }
        for descriptor in artifacts.values():
            _write_sidecar(staging / descriptor["path"])
        manifest_payload = {
            "schema_version": MANIFEST_SCHEMA,
            "state": "candidate",
            "supersedes": None,
            "generation": {
                "generation_id": ledger["generation_id"],
                "ledger_sha256": expected_ledger_sha256,
            },
            "artifacts": dict(sorted(artifacts.items())),
            "provenance": _provenance(ledger, expected_ledger_sha256),
        }
        manifest = {
            **manifest_payload,
            "bundle_id": sha256_bytes(_identity_bytes(manifest_payload)),
        }
        manifest_path = staging / "manifest.json"
        _write(manifest_path, canonical_bytes(manifest))
        _write_sidecar(manifest_path)

        if sha256_file(generation_ledger) != expected_ledger_sha256:
            raise ValueError("generation ledger mutated during freeze")
        load_generation_ledger(generation_ledger, git_snapshot=_git_snapshot())
        final_metrics_bytes = evaluation_metrics.read_bytes()
        if final_metrics_bytes != metrics_source_bytes:
            raise ValueError("evaluation metrics mutated during freeze")
        _load_metrics_bytes(final_metrics_bytes)
        producer_final = {
            path.name: sha256_file(path)
            for path in producer_dir.iterdir()
            if path.is_file() and not path.is_symlink()
        }
        if producer_final != producer_initial:
            raise ValueError("producer generation mutated during release freeze")
        _validate_built_bundle(staging)
        _fsync_tree(staging)
        if destination.exists():
            destination.rmdir()
        os.replace(staging, destination)
        published_destination = True
        parent_descriptor = os.open(destination.parent, os.O_RDONLY)
        try:
            os.fsync(parent_descriptor)
        finally:
            os.close(parent_descriptor)
        _immutable_tree(destination)
        published = _validate_built_bundle(destination)
        return {
            "generation_id": ledger["generation_id"],
            "bundle_id": published["bundle_id"],
            "manifest_sha256": sha256_file(destination / "manifest.json"),
            "artifacts": {
                role: {
                    "row_count": descriptor["row_count"],
                    "sha256": descriptor["sha256"],
                }
                for role, descriptor in published["artifacts"].items()
            },
        }
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        if published_destination and destination.exists():
            for path in destination.rglob("*"):
                path.chmod(0o755 if path.is_dir() else 0o644)
            destination.chmod(0o755)
            shutil.rmtree(destination)
            if destination.exists():
                raise RuntimeError("failed to roll back published candidate")
        raise
