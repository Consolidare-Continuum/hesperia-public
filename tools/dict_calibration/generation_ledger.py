# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""Strict validation for CORE-D2 generation ledgers."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from .core_candidate import (
    _no_duplicate_keys,
    _reject_constant,
    canonical_bytes,
    sha256_file,
)


SCHEMA = "hesperia.dict_calibration.generation_ledger.v1"
CODE_FILE_ROLES = frozenset(
    {"producer", "materializer", "evaluator", "gate", "exporter", "resolver"}
)
CODE_ROLE_SUFFIXES = {
    "producer": ("tools", "dict_calibration", "run_pipeline.py"),
    "materializer": ("tools", "dict_calibration", "core_candidate.py"),
    "evaluator": ("tools", "dict_calibration", "evaluate.py"),
    "gate": ("tools", "dict_calibration", "core_pack_gate.py"),
    "exporter": ("tools", "dict_calibration", "resolved_export.py"),
    "resolver": ("core", "engine", "lexical_concept", "pipeline.py"),
}
GENERATION_ENV_KEYS = frozenset(
    {
        "PYTHONHASHSEED",
        "HESPERIA_LEGACY_RESEARCH_CORPUS",
        "HESPERIA_DICT_CALIB_OFFLINE",
        "HESPERIA_DICT_CALIB_WORKERS",
        "HESPERIA_CALIB_MOCK_OPENAI",
        "HESPERIA_CALIB_CALL_LEDGER",
        "HESPERIA_CALIB_USE_MAX_COMPLETION_TOKENS",
        "HESPERIA_CALIB_OPENAI_MODEL",
        "HESPERIA_CALIB_MAX_OUTPUT_TOKENS",
        "HESPERIA_CALIB_NORMALIZE_INPUT_TEXT_CAP",
        "HESPERIA_CALIB_LINKS_SKIP_FUZZY",
        "HESPERIA_CALIB_LINKS_FUZZY",
        "OPENAI_BASE_URL",
        "OPENAI_ORG_ID",
        "OPENAI_PROJECT_ID",
        "OPENAI_MAX_RETRIES",
        "OPENAI_TIMEOUT",
        "OPENAI_API_KEY_SHA256",
    }
)
_OBSERVABLE_ENV_KEYS = (GENERATION_ENV_KEYS - {"OPENAI_API_KEY_SHA256"}) | {
    "OPENAI_API_KEY"
}
CONFIGURATION_FIELDS = frozenset(
    {
        "resolver_version",
        "resolver_configuration_sha256",
        "segmentation_rule",
        "statistical_rule",
        "complete",
        "files",
        "values",
    }
)
FIELDS = frozenset(
    {
        "schema",
        "generation_id",
        "corpus_root",
        "source_hashes",
        "source_count",
        "source_map_sha256",
        "git_commit",
        "git_tree_clean",
        "code_file_sha256",
        "model_provider",
        "model_id",
        "checkpoint_id",
        "prompt_path",
        "prompt_sha256",
        "configuration",
        "environment",
        "random_seed",
        "worker_count",
        "batch_size",
        "batch_ordering_rule",
        "retry_policy",
        "generation_started_at",
    }
)


def _is_sha256(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64 or value != value.casefold():
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"generation ledger {label} must be non-empty text")
    return value


def _absolute_regular_file(value: Any, label: str) -> Path:
    path = Path(_text(value, label))
    if not path.is_absolute() or path.is_symlink() or not path.is_file():
        raise ValueError(f"generation ledger {label} must be an absolute regular file")
    return path


def _validate_named_file_bindings(
    value: Any,
    *,
    label: str,
    required_names: frozenset[str] | None = None,
) -> dict[str, Path]:
    if (
        not isinstance(value, dict)
        or not value
        or (required_names is not None and set(value) != required_names)
    ):
        raise ValueError(f"generation ledger {label} named bindings are incomplete")
    paths: dict[str, Path] = {}
    for name, raw_descriptor in value.items():
        if (
            not isinstance(name, str)
            or not name
            or not isinstance(raw_descriptor, dict)
            or set(raw_descriptor) != {"path", "sha256"}
        ):
            raise ValueError(f"generation ledger {label} named descriptor is invalid")
        path = _absolute_regular_file(raw_descriptor["path"], f"{label}.{name}.path")
        digest = raw_descriptor["sha256"]
        if not _is_sha256(digest) or sha256_file(path) != digest:
            raise ValueError(f"generation ledger {label} file digest changed: {name}")
        if path.resolve() != path:
            raise ValueError(f"generation ledger {label} path is not canonical: {name}")
        paths[name] = path
    return paths


def _validate_environment(value: Any) -> None:
    if (
        not isinstance(value, dict)
        or set(value) != {"complete", "values"}
        or value["complete"] is not True
        or not isinstance(value["values"], dict)
        or set(value["values"]) != GENERATION_ENV_KEYS
        or not all(isinstance(item, str) for item in value["values"].values())
    ):
        raise ValueError("generation ledger environment key set is incomplete")
    declared = value["values"]
    for key in GENERATION_ENV_KEYS - {"OPENAI_API_KEY_SHA256"}:
        if declared[key] != os.environ.get(key, ""):
            raise ValueError(f"generation ledger environment changed: {key}")
    api_key = os.environ.get("OPENAI_API_KEY", "")
    expected_key_digest = hashlib.sha256(api_key.encode("utf-8")).hexdigest() if api_key else ""
    if declared["OPENAI_API_KEY_SHA256"] != expected_key_digest:
        raise ValueError("generation ledger environment changed: OPENAI_API_KEY")
    unknown = sorted(
        key
        for key in os.environ
        if (
            key.startswith(("HESPERIA_CALIB_", "HESPERIA_DICT_CALIB_", "OPENAI_"))
            or key == "HESPERIA_LEGACY_RESEARCH_CORPUS"
        )
        and key not in _OBSERVABLE_ENV_KEYS
    )
    if unknown:
        raise ValueError(
            "unknown undeclared generation-affecting environment keys: "
            + ", ".join(unknown)
        )


def _corpus_membership(root: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for directory, directory_names, file_names in os.walk(root, followlinks=False):
        directory_path = Path(directory)
        if directory_path.is_symlink():
            raise ValueError("generation ledger corpus contains a symlinked directory")
        for name in directory_names:
            if (directory_path / name).is_symlink():
                raise ValueError("generation ledger corpus contains a symlinked directory")
        for name in sorted(file_names):
            path = directory_path / name
            if path.is_symlink() or not path.is_file():
                raise ValueError("generation ledger corpus contains an unsafe source")
            result[path.relative_to(root).as_posix()] = sha256_file(path)
    return dict(sorted(result.items()))


def validate_generation_ledger(
    ledger: dict[str, Any],
    *,
    git_snapshot: tuple[str, bool],
) -> None:
    if set(ledger) != FIELDS or ledger.get("schema") != SCHEMA:
        raise ValueError("generation ledger schema and fields must be exact")
    identity_payload = {
        key: value
        for key, value in ledger.items()
        if key not in {"generation_id", "generation_started_at"}
    }
    expected_id = hashlib.sha256(canonical_bytes(identity_payload)).hexdigest()
    if ledger.get("generation_id") != expected_id:
        raise ValueError("generation ledger generation_id does not recompute")

    corpus_root = Path(_text(ledger["corpus_root"], "corpus_root"))
    if (
        not corpus_root.is_absolute()
        or corpus_root.is_symlink()
        or not corpus_root.is_dir()
        or corpus_root.resolve() != corpus_root
    ):
        raise ValueError("generation ledger corpus_root must be absolute and non-symlink")
    source_hashes = ledger["source_hashes"]
    if not isinstance(source_hashes, dict) or not source_hashes:
        raise ValueError("generation ledger source_hashes must be non-empty")
    if (
        any(
            not isinstance(key, str)
            or not key
            or Path(key).is_absolute()
            or ".." in Path(key).parts
            or not _is_sha256(digest)
            for key, digest in source_hashes.items()
        )
        or source_hashes != dict(sorted(source_hashes.items()))
    ):
        raise ValueError("generation ledger source_hashes are unsafe or non-canonical")
    if ledger["source_count"] != len(source_hashes):
        raise ValueError("generation ledger source_count does not recompute")
    if ledger["source_map_sha256"] != hashlib.sha256(
        canonical_bytes(source_hashes)
    ).hexdigest():
        raise ValueError("generation ledger source_map_sha256 does not recompute")
    if _corpus_membership(corpus_root) != source_hashes:
        raise ValueError("generation ledger corpus membership or digest changed")

    code_files = ledger["code_file_sha256"]
    code_paths = _validate_named_file_bindings(
        code_files,
        label="named code",
        required_names=CODE_FILE_ROLES,
    )
    if len({path.resolve() for path in code_paths.values()}) != len(CODE_FILE_ROLES):
        raise ValueError("generation ledger six code roles require six distinct paths")
    for role, expected_suffix in CODE_ROLE_SUFFIXES.items():
        if code_paths[role].parts[-len(expected_suffix) :] != expected_suffix:
            raise ValueError(
                f"generation ledger code role {role} requires "
                + "/".join(expected_suffix)
            )

    prompt_path = _absolute_regular_file(ledger["prompt_path"], "prompt_path")
    if not _is_sha256(ledger["prompt_sha256"]) or sha256_file(prompt_path) != ledger[
        "prompt_sha256"
    ]:
        raise ValueError("generation ledger prompt digest changed")
    for field in (
        "model_provider",
        "model_id",
        "checkpoint_id",
        "batch_ordering_rule",
        "generation_started_at",
    ):
        _text(ledger[field], field)
    configuration = ledger["configuration"]
    if not isinstance(configuration, dict) or set(configuration) != CONFIGURATION_FIELDS:
        raise ValueError("generation ledger configuration binding is incomplete")
    for field in (
        "resolver_version",
        "resolver_configuration_sha256",
        "segmentation_rule",
        "statistical_rule",
    ):
        _text(configuration[field], f"configuration.{field}")
    if configuration["complete"] is not True:
        raise ValueError("generation ledger configuration completeness is not asserted")
    if not _is_sha256(configuration["resolver_configuration_sha256"]):
        raise ValueError("generation ledger resolver configuration digest is invalid")
    configuration_paths = _validate_named_file_bindings(
        configuration["files"],
        label="named configuration",
    )
    if len({path.resolve() for path in configuration_paths.values()}) != len(
        configuration_paths
    ):
        raise ValueError("generation ledger configuration files must be distinct")
    if set(configuration_paths.values()) & set(code_paths.values()):
        raise ValueError("generation ledger configuration files must be separate")
    if not isinstance(configuration["values"], dict):
        raise ValueError("generation ledger configuration.values must be an object")
    _validate_environment(ledger["environment"])
    if not isinstance(ledger["retry_policy"], dict) or not ledger["retry_policy"]:
        raise ValueError("generation ledger retry_policy must be non-empty")
    for field in ("random_seed", "worker_count", "batch_size"):
        value = ledger[field]
        if (
            not isinstance(value, int)
            or isinstance(value, bool)
            or (field != "random_seed" and value <= 0)
        ):
            raise ValueError(f"generation ledger {field} is invalid")
    git_commit, clean = git_snapshot
    if (
        not ledger["git_tree_clean"]
        or not clean
        or ledger["git_commit"] != git_commit
    ):
        raise ValueError("generation ledger Git commit or clean-tree assertion changed")
    canonical_bytes(ledger)


def load_generation_ledger(
    path: Path,
    *,
    git_snapshot: tuple[str, bool],
) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise ValueError("generation ledger must be a regular non-symlink file")
    try:
        ledger = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_no_duplicate_keys,
            parse_constant=_reject_constant,
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError("generation ledger is malformed") from exc
    if not isinstance(ledger, dict):
        raise ValueError("generation ledger must be an object")
    validate_generation_ledger(ledger, git_snapshot=git_snapshot)
    return ledger
