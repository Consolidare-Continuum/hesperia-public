# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

from __future__ import annotations

import hashlib
import importlib
import inspect
import json
import math
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from tools.dict_calibration.freeze_version import freeze


REPO = Path(__file__).resolve().parents[2]
GATE_SCHEMA = "hesperia.core_calibration_pack_gate.v1"
MANIFEST_SCHEMA = "hesperia.dict_calibration.freeze_manifest.v1"
EVALUATION_SCHEMA = "hesperia.dict_calibration.bundle_comparison.v1"
LIMITS_SCHEMA = "hesperia.dict_calibration.limits.v1"

ProcessRunner = Callable[..., subprocess.CompletedProcess[str]]
BoundaryChecker = Callable[[Path], subprocess.CompletedProcess[str]]


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


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(
            json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
            for row in rows
        ),
        encoding="utf-8",
    )


def _write_sidecar(path: Path) -> None:
    path.with_name(f"{path.name}.sha256").write_text(
        f"{_sha256(path)}  {path.name}\n",
        encoding="ascii",
    )


def _rewrite_manifest(
    bundle: Path,
    mutate: Callable[[dict[str, Any]], None],
    *,
    refresh_bundle_id: bool = True,
    refresh_sidecar: bool = True,
) -> None:
    path = bundle / "manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    mutate(manifest)
    if refresh_bundle_id:
        unsigned = {key: value for key, value in manifest.items() if key != "bundle_id"}
        manifest["bundle_id"] = _sha256_bytes(_canonical_bytes(unsigned))
    _write_json(path, manifest)
    if refresh_sidecar:
        _write_sidecar(path)


def _rewrite_evaluation(
    path: Path,
    mutate: Callable[[dict[str, Any]], None],
    *,
    refresh_hash: bool = True,
) -> None:
    report = json.loads(path.read_text(encoding="utf-8"))
    mutate(report)
    if refresh_hash:
        unsigned = {key: value for key, value in report.items() if key != "report_sha256"}
        report["report_sha256"] = _sha256_bytes(_canonical_bytes(unsigned))
    _write_json(path, report)


def _rewrite_limits(
    path: Path,
    mutate: Callable[[dict[str, Any]], None],
    *,
    refresh_sidecar: bool = True,
) -> None:
    limits = json.loads(path.read_text(encoding="utf-8"))
    mutate(limits)
    _write_json(path, limits)
    if refresh_sidecar:
        _write_sidecar(path)


def _bind_limits_to_case(case: dict[str, Path]) -> None:
    manifest = json.loads(
        (case["bundle"] / "manifest.json").read_text(encoding="utf-8")
    )
    report = json.loads(case["evaluation"].read_text(encoding="utf-8"))
    _rewrite_limits(
        case["limits"],
        lambda limits: limits.update(
            {
                "candidate_bundle_id": manifest["bundle_id"],
                "evaluation_report_sha256": report["report_sha256"],
            }
        ),
    )
    case["expected_limits_sha256"] = _sha256(case["limits"])


def _bind_evaluation_candidate_to_manifest(case: dict[str, Path]) -> None:
    manifest = json.loads(
        (case["bundle"] / "manifest.json").read_text(encoding="utf-8")
    )
    _rewrite_evaluation(
        case["evaluation"],
        lambda report: report["candidate"].__setitem__(
            "bundle_id", manifest["bundle_id"]
        ),
    )
    _bind_limits_to_case(case)


def _gate_module() -> Any:
    return importlib.import_module("tools.dict_calibration.core_pack_gate")


def _passing_runner(
    command: list[str],
    **_kwargs: Any,
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(command, 0, stdout="ok\n", stderr="")


def _passing_boundary(repo_root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        [sys.executable, str(repo_root / "tools/check_core_default_tfp_boundary.py")],
        0,
        stdout="",
        stderr="Core-default/TFP calibration boundary: OK\n",
    )


def _evaluate(
    case: dict[str, Path],
    *,
    subprocess_runner: ProcessRunner = _passing_runner,
    boundary_checker: BoundaryChecker = _passing_boundary,
) -> dict[str, Any]:
    return _gate_module().evaluate_core_pack(
        bundle=case["bundle"],
        evaluation=case["evaluation"],
        limits=case["limits"],
        expected_limits_sha256=case["expected_limits_sha256"],
        repo_root=case["repo_root"],
        subprocess_runner=subprocess_runner,
        boundary_checker=boundary_checker,
    )


def _assert_failed(verdict: dict[str, Any], *terms: str) -> None:
    assert verdict["schema_version"] == GATE_SCHEMA
    assert verdict["pass"] is False
    text = json.dumps(verdict, ensure_ascii=False).casefold()
    assert any(term.casefold() in text for term in terms), text


def _assert_failed_reason(verdict: dict[str, Any], *terms: str) -> None:
    failed_reasons = [
        str(check["reason"]).casefold()
        for check in verdict["checks"]
        if check["pass"] is False
    ]
    assert failed_reasons
    assert any(
        term.casefold() in reason
        for term in terms
        for reason in failed_reasons
    ), failed_reasons


def _artifact_paths(case: dict[str, Path]) -> dict[str, Path]:
    manifest = json.loads(
        (case["bundle"] / "manifest.json").read_text(encoding="utf-8")
    )
    return {
        role: case["bundle"] / descriptor["path"]
        for role, descriptor in manifest["artifacts"].items()
    }


@pytest.fixture()
def valid_case(tmp_path: Path) -> dict[str, Path]:
    bundle = tmp_path / "candidate"
    bundle.mkdir()
    artifacts = {
        "dict_a_matcher": (
            "dict_a.jsonl",
            "matcher_ready",
            [
                {
                    "entry_id": "A-001",
                    "normalized_form": "alpha",
                    "match_type": "exact",
                    "candidate_concept_ids": ["C-001"],
                }
            ],
        ),
        "dict_b_canonical": (
            "dict_b.jsonl",
            "canonical",
            [
                {
                    "concept_id": "C-001",
                    "related_concept_ids": ["C-002"],
                    "area_ids": ["A00"],
                    "family_ids": ["F00"],
                },
                {
                    "concept_id": "C-002",
                    "related_concept_ids": [],
                    "area_ids": ["A00"],
                    "family_ids": ["F01"],
                },
            ],
        ),
        "dict_c_runtime_conversion": (
            "dict_c.jsonl",
            "matcher_ready",
            [
                {
                    "normalized_form": "alpha beta",
                    "candidate_concept_ids": ["C-001", "C-002"],
                }
            ],
        ),
    }
    descriptors: dict[str, dict[str, str]] = {}
    for role, (relative, status, rows) in artifacts.items():
        path = bundle / relative
        _write_jsonl(path, rows)
        _write_sidecar(path)
        descriptors[role] = {
            "path": relative,
            "sha256": _sha256(path),
            "status": status,
        }

    corpus_dir = bundle / "evidence/corpus"
    corpus_dir.mkdir(parents=True)
    corpus_source = corpus_dir / "sample.txt"
    corpus_source.write_text("alpha beta\n", encoding="utf-8")
    manifest_payload = {
        "schema_version": MANIFEST_SCHEMA,
        "state": "candidate",
        "supersedes": None,
        "artifacts": descriptors,
        "provenance": {
            "model": "gpt-5-mini-2025-08-07",
            "prompt_sha256": "3" * 64,
            "checkpoint": "core-d2-w3-fixture",
            "resolver": {
                "version": "core-lexical-resolver-v1",
                "configuration_sha256": "4" * 64,
            },
            "segmentation_rule": "frozen-paragraph-segmentation-v1",
            "statistical_rule": "paragraph-cooccurrence-npmi-g2-v1",
            "builder_revision": "core-d2-w3-gate-fixture-r1",
            "corpus": {
                "path": corpus_dir.as_posix(),
                "source_hashes": {"sample.txt": _sha256(corpus_source)},
            },
        },
    }
    manifest = {
        **manifest_payload,
        "bundle_id": _sha256_bytes(_canonical_bytes(manifest_payload)),
    }
    manifest_path = bundle / "manifest.json"
    _write_json(manifest_path, manifest)
    _write_sidecar(manifest_path)

    sample_text = "alpha beta"
    sample = {
        "sample_id": _sha256_bytes(f"0\0{sample_text}".encode()),
        "ordinal": 0,
        "text_sha256": _sha256_bytes(sample_text.encode()),
        "baseline": {
            "accepted": 1,
            "rejected": 1,
            "coverage": 0.5,
            "concept_weights": {"C-001": 1.0},
            "family_activation": {"F00": 1.0},
            "span_resolutions": [],
        },
        "candidate": {
            "accepted": 2,
            "rejected": 1,
            "coverage": 0.6,
            "concept_weights": {"C-001": 1.0, "C-002": 1.0},
            "family_activation": {"F00": 0.9, "F01": 0.1},
            "span_resolutions": [],
        },
        "span_diffs": [],
        "ambiguous_candidate_spans": [],
    }
    report_payload = {
        "schema_version": EVALUATION_SCHEMA,
        "baseline": {"bundle_id": "b" * 64},
        "candidate": {"bundle_id": manifest["bundle_id"]},
        "samples": [sample],
        "aggregate": {
            "baseline": {
                "accepted": 1,
                "rejected": 1,
                "coverage": 0.5,
                "entropy": 0.0,
                "family_distribution": {"F00": 1.0},
            },
            "candidate": {
                "accepted": 2,
                "rejected": 1,
                "coverage": 0.6,
                "entropy": 0.1,
                "family_distribution": {"F00": 0.9, "F01": 0.1},
            },
            "delta": {
                "accepted": 1,
                "rejected": 0,
                "coverage": 0.1,
                "entropy": 0.1,
                "family_distribution": {"F00": -0.1, "F01": 0.1},
            },
        },
        "weight_zero_identity": False,
    }
    report = {
        **report_payload,
        "report_sha256": _sha256_bytes(_canonical_bytes(report_payload)),
    }
    evaluation = tmp_path / "candidate-comparison.json"
    _write_json(evaluation, report)

    limits = tmp_path / "limits.json"
    _write_json(
        limits,
        {
            "schema_version": LIMITS_SCHEMA,
            "candidate_bundle_id": manifest["bundle_id"],
            "evaluation_report_sha256": report["report_sha256"],
            "max_absolute_deltas": {
                "accepted": 1,
                "rejected": 0,
                "coverage": 0.1,
                "entropy": 0.1,
                "family_distribution": 0.1,
            },
        },
    )
    _write_sidecar(limits)
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    return {
        "bundle": bundle,
        "evaluation": evaluation,
        "limits": limits,
        "expected_limits_sha256": _sha256(limits),
        "repo_root": repo_root,
    }


def test_valid_core_pack_passes_with_required_abc_roles(
    valid_case: dict[str, Path],
) -> None:
    verdict = _evaluate(valid_case)

    assert verdict["schema_version"] == GATE_SCHEMA
    assert verdict["pass"] is True
    assert verdict["candidate"]["bundle_id"] == json.loads(
        (valid_case["bundle"] / "manifest.json").read_text(encoding="utf-8")
    )["bundle_id"]
    assert verdict["evaluation"]["report_sha256"] == json.loads(
        valid_case["evaluation"].read_text(encoding="utf-8")
    )["report_sha256"]
    assert all(check["pass"] for check in verdict["checks"])


def test_manifest_v1_remains_historical_but_is_release_ineligible(
    valid_case: dict[str, Path],
) -> None:
    manifest, _paths = _gate_module()._validate_manifest(valid_case["bundle"])
    assert manifest["schema_version"] == MANIFEST_SCHEMA

    with pytest.raises(ValueError, match="historical.*release-ineligible"):
        _gate_module()._validate_manifest(
            valid_case["bundle"],
            require_manifest_v2=True,
        )


def test_gate_accepts_finite_float_dict_c_priority() -> None:
    _gate_module()._validate_c_row(
        {
            "normalized_form": "alpha",
            "candidate_concept_ids": ["C-001"],
            "priority": 0.875,
        }
    )


@pytest.mark.parametrize("case", ["missing", "malformed"])
def test_missing_or_malformed_manifest_is_a_hard_failure(
    valid_case: dict[str, Path],
    case: str,
) -> None:
    manifest = valid_case["bundle"] / "manifest.json"
    if case == "missing":
        manifest.unlink()
    else:
        manifest.write_text('{"truncated":\n', encoding="utf-8")

    _assert_failed(_evaluate(valid_case), "manifest")


@pytest.mark.parametrize(
    "case",
    [
        "bad-sidecar",
        "bad-bundle-id",
        "bad-artifact-hash",
        "bad-artifact-sidecar",
        "absolute-path",
        "traversal-path",
        "symlink-path",
    ],
)
def test_manifest_identity_sidecars_hashes_and_safe_paths_fail_closed(
    valid_case: dict[str, Path],
    tmp_path: Path,
    case: str,
) -> None:
    bundle = valid_case["bundle"]
    if case == "bad-sidecar":
        (bundle / "manifest.json.sha256").write_text(
            f"{'0' * 64}  manifest.json\n", encoding="ascii"
        )
    elif case == "bad-bundle-id":
        _rewrite_manifest(
            bundle,
            lambda manifest: manifest.__setitem__("bundle_id", "0" * 64),
            refresh_bundle_id=False,
        )
    elif case == "bad-artifact-hash":
        (bundle / "dict_a.jsonl").write_text('{"changed":true}\n', encoding="utf-8")
    elif case == "bad-artifact-sidecar":
        (bundle / "dict_a.jsonl.sha256").write_text(
            f"{'0' * 64}  dict_a.jsonl\n", encoding="ascii"
        )
    elif case in {"absolute-path", "traversal-path"}:
        unsafe = (
            (tmp_path / "outside.jsonl").as_posix()
            if case == "absolute-path"
            else "../outside.jsonl"
        )
        _rewrite_manifest(
            bundle,
            lambda manifest: manifest["artifacts"]["dict_a_matcher"].__setitem__(
                "path", unsafe
            ),
        )
    elif case == "symlink-path":
        target = bundle / "dict_a.jsonl"
        linked = bundle / "linked-a.jsonl"
        linked.symlink_to(target)

        def point_to_symlink(manifest: dict[str, Any]) -> None:
            descriptor = manifest["artifacts"]["dict_a_matcher"]
            descriptor["path"] = linked.name
            descriptor["sha256"] = _sha256(target)

        _rewrite_manifest(bundle, point_to_symlink)
    else:
        raise AssertionError(case)

    _assert_failed(_evaluate(valid_case), "hash", "digest", "sidecar", "path", "symlink")


@pytest.mark.parametrize(
    ("case", "expected"),
    [
        ("missing-a", "dict_a_matcher"),
        ("missing-b", "dict_b_canonical"),
        ("missing-c", "dict_c_runtime_conversion"),
        ("unknown-role", "unknown"),
    ],
)
def test_required_roles_and_unknown_roles_are_enforced(
    valid_case: dict[str, Path],
    case: str,
    expected: str,
) -> None:
    def mutate(manifest: dict[str, Any]) -> None:
        artifacts = manifest["artifacts"]
        if case == "missing-a":
            del artifacts["dict_a_matcher"]
        elif case == "missing-b":
            del artifacts["dict_b_canonical"]
        elif case == "missing-c":
            del artifacts["dict_c_runtime_conversion"]
        else:
            artifacts["dict_x_unrecognized"] = dict(artifacts["dict_a_matcher"])

    _rewrite_manifest(valid_case["bundle"], mutate)

    _assert_failed(_evaluate(valid_case), expected, "role")


@pytest.mark.parametrize(
    "role",
    ["dict_a_matcher", "dict_b_canonical", "dict_c_runtime_conversion"],
)
def test_required_runtime_artifacts_must_be_nonempty_jsonl(
    valid_case: dict[str, Path],
    role: str,
) -> None:
    manifest = json.loads(
        (valid_case["bundle"] / "manifest.json").read_text(encoding="utf-8")
    )
    artifact = valid_case["bundle"] / manifest["artifacts"][role]["path"]
    artifact.write_text("\n", encoding="utf-8")
    _write_sidecar(artifact)
    _rewrite_manifest(
        valid_case["bundle"],
        lambda value: value["artifacts"][role].__setitem__(
            "sha256", _sha256(artifact)
        ),
    )

    _assert_failed(_evaluate(valid_case), role, "empty", "jsonl")


def test_optional_dict_d_is_not_required_but_is_fully_validated_when_declared(
    valid_case: dict[str, Path],
) -> None:
    path = valid_case["bundle"] / "dict_d.jsonl"
    _write_jsonl(
        path,
        [
            {
                "concept_id_a": "C-001",
                "concept_id_b": "C-002",
                "cooc_count": 3,
                "npmi": 0.5,
                "g2": 1.25,
                "source_books": ["book-001", "book-002"],
                "agreement_with_b": "agrees",
            }
        ],
    )
    _write_sidecar(path)

    def add_dict_d(manifest: dict[str, Any]) -> None:
        manifest["artifacts"]["dict_d"] = {
            "path": path.name,
            "sha256": _sha256(path),
            "status": "validated_optional",
        }

    _rewrite_manifest(valid_case["bundle"], add_dict_d)
    _bind_evaluation_candidate_to_manifest(valid_case)
    assert _gate_module()._validate_artifacts(_artifact_paths(valid_case))["dict_d"] == 1
    assert _evaluate(valid_case)["pass"] is True

    _write_jsonl(
        path,
        [
            {
                "concept_id_a": "C-001",
                "concept_id_b": "C-MISSING",
                "cooc_count": 3,
                "npmi": 0.5,
                "g2": 1.25,
                "source_books": ["book-001"],
                "agreement_with_b": "agrees",
            }
        ],
    )
    _write_sidecar(path)
    _rewrite_manifest(
        valid_case["bundle"],
        lambda manifest: manifest["artifacts"]["dict_d"].__setitem__(
            "sha256", _sha256(path)
        ),
    )
    _bind_evaluation_candidate_to_manifest(valid_case)
    _assert_failed(_evaluate(valid_case), "dict_d", "schema", "reference", "closure")


@pytest.mark.parametrize(
    ("case", "mutate"),
    [
        ("noncanonical-pair", lambda row: row.update(concept_id_a="C-002", concept_id_b="C-001")),
        ("self-pair", lambda row: row.__setitem__("concept_id_b", "C-001")),
        ("zero-cooc", lambda row: row.__setitem__("cooc_count", 0)),
        ("boolean-cooc", lambda row: row.__setitem__("cooc_count", True)),
        ("npmi-low", lambda row: row.__setitem__("npmi", -1.000001)),
        ("npmi-high", lambda row: row.__setitem__("npmi", 1.000001)),
        ("npmi-nan", lambda row: row.__setitem__("npmi", float("nan"))),
        ("negative-g2", lambda row: row.__setitem__("g2", -0.001)),
        ("infinite-g2", lambda row: row.__setitem__("g2", float("inf"))),
        ("empty-books", lambda row: row.__setitem__("source_books", [])),
        (
            "duplicate-books",
            lambda row: row.__setitem__("source_books", ["book-001", "book-001"]),
        ),
        (
            "unstable-books",
            lambda row: row.__setitem__("source_books", ["book-002", "book-001"]),
        ),
        (
            "bad-agreement",
            lambda row: row.__setitem__("agreement_with_b", "contradicts"),
        ),
    ],
)
def test_optional_dict_d_contract_schema_fails_closed(
    valid_case: dict[str, Path],
    case: str,
    mutate: Callable[[dict[str, Any]], None],
) -> None:
    row = {
        "concept_id_a": "C-001",
        "concept_id_b": "C-002",
        "cooc_count": 3,
        "npmi": 0.5,
        "g2": 1.25,
        "source_books": ["book-001", "book-002"],
        "agreement_with_b": "novel",
    }
    mutate(row)
    artifact = valid_case["bundle"] / "dict_d.jsonl"
    if case in {"npmi-nan", "infinite-g2"}:
        artifact.write_text(
            json.dumps(row, allow_nan=True, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    else:
        _write_jsonl(artifact, [row])
    _write_sidecar(artifact)

    def add_dict_d(manifest: dict[str, Any]) -> None:
        manifest["artifacts"]["dict_d"] = {
            "path": artifact.name,
            "sha256": _sha256(artifact),
            "status": "validated_optional",
        }

    _rewrite_manifest(valid_case["bundle"], add_dict_d)
    _bind_evaluation_candidate_to_manifest(valid_case)
    _assert_failed(_evaluate(valid_case), "dict_d", case, "schema")


@pytest.mark.parametrize(
    ("role", "invalid_row"),
    [
        (
            "dict_a_matcher",
            {
                "entry_id": "A-001",
                "normalized_form": "alpha",
                "match_type": "fuzzy",
                "candidate_concept_ids": ["C-001"],
            },
        ),
        (
            "dict_a_matcher",
            {
                "entry_id": "A-001",
                "normalized_form": "alpha",
                "match_type": "exact",
                "candidate_concept_ids": ["C-001"],
                "unexpected_field": "schema drift",
            },
        ),
        (
            "dict_b_canonical",
            {"concept_id": "C-001", "related_concept_ids": "C-002"},
        ),
        (
            "dict_c_runtime_conversion",
            {"normalized_form": "alpha beta", "candidate_concept_ids": []},
        ),
    ],
)
def test_abc_rows_use_strict_role_specific_schemas(
    valid_case: dict[str, Path],
    role: str,
    invalid_row: dict[str, Any],
) -> None:
    manifest = json.loads(
        (valid_case["bundle"] / "manifest.json").read_text(encoding="utf-8")
    )
    artifact = valid_case["bundle"] / manifest["artifacts"][role]["path"]
    _write_jsonl(artifact, [invalid_row])
    _write_sidecar(artifact)
    _rewrite_manifest(
        valid_case["bundle"],
        lambda value: value["artifacts"][role].__setitem__(
            "sha256", _sha256(artifact)
        ),
    )

    _assert_failed(_evaluate(valid_case), role, "schema")


@pytest.mark.parametrize(
    ("role", "rows"),
    [
        (
            "dict_a_matcher",
            [
                {
                    "entry_id": "A-001",
                    "normalized_form": "alpha",
                    "match_type": "exact",
                    "candidate_concept_ids": ["C-001"],
                },
                {
                    "entry_id": "A-001",
                    "normalized_form": "beta",
                    "match_type": "exact",
                    "candidate_concept_ids": ["C-002"],
                },
            ],
        ),
        (
            "dict_b_canonical",
            [
                {
                    "concept_id": "C-001",
                    "related_concept_ids": [],
                    "area_ids": ["A00"],
                    "family_ids": ["F00"],
                },
                {
                    "concept_id": "C-001",
                    "related_concept_ids": [],
                    "area_ids": ["A00"],
                    "family_ids": ["F01"],
                },
            ],
        ),
        (
            "dict_c_runtime_conversion",
            [
                {
                    "normalized_form": "alpha beta",
                    "candidate_concept_ids": ["C-001"],
                },
                {
                    "normalized_form": "alpha beta",
                    "candidate_concept_ids": ["C-002"],
                },
            ],
        ),
    ],
)
def test_runtime_artifact_identities_are_unique(
    valid_case: dict[str, Path],
    role: str,
    rows: list[dict[str, Any]],
) -> None:
    manifest = json.loads(
        (valid_case["bundle"] / "manifest.json").read_text(encoding="utf-8")
    )
    artifact = valid_case["bundle"] / manifest["artifacts"][role]["path"]
    _write_jsonl(artifact, rows)
    _write_sidecar(artifact)
    _rewrite_manifest(
        valid_case["bundle"],
        lambda value: value["artifacts"][role].__setitem__(
            "sha256", _sha256(artifact)
        ),
    )

    _assert_failed(_evaluate(valid_case), role, "duplicate", "unique")


@pytest.mark.parametrize(
    ("role", "rows"),
    [
        (
            "dict_a_matcher",
            [
                {
                    "entry_id": "A-001",
                    "normalized_form": "alpha",
                    "match_type": "exact",
                    "candidate_concept_ids": ["C-MISSING"],
                }
            ],
        ),
        (
            "dict_b_canonical",
            [
                {
                    "concept_id": "C-001",
                    "related_concept_ids": ["C-MISSING"],
                    "area_ids": ["A00"],
                    "family_ids": ["F00"],
                }
            ],
        ),
        (
            "dict_c_runtime_conversion",
            [
                {
                    "normalized_form": "alpha beta",
                    "candidate_concept_ids": ["C-MISSING"],
                }
            ],
        ),
    ],
)
def test_all_runtime_concept_references_close_against_dict_b(
    valid_case: dict[str, Path],
    role: str,
    rows: list[dict[str, Any]],
) -> None:
    manifest = json.loads(
        (valid_case["bundle"] / "manifest.json").read_text(encoding="utf-8")
    )
    artifact = valid_case["bundle"] / manifest["artifacts"][role]["path"]
    _write_jsonl(artifact, rows)
    _write_sidecar(artifact)
    _rewrite_manifest(
        valid_case["bundle"],
        lambda value: value["artifacts"][role].__setitem__(
            "sha256", _sha256(artifact)
        ),
    )

    _assert_failed(_evaluate(valid_case), "C-MISSING", "closure", "reference")


@pytest.mark.parametrize(
    "case",
    [
        "wrong-schema",
        "wrong-candidate",
        "bad-report-hash",
        "empty-samples",
        "unstable-sample-id",
        "unordered-ordinal",
        "nonfinite-metric",
        "same-id-not-identity",
    ],
)
def test_w2_report_binding_integrity_finite_metrics_and_identity_are_required(
    valid_case: dict[str, Path],
    case: str,
) -> None:
    manifest = json.loads(
        (valid_case["bundle"] / "manifest.json").read_text(encoding="utf-8")
    )

    def mutate(report: dict[str, Any]) -> None:
        if case == "wrong-schema":
            report["schema_version"] = "hesperia.dict_calibration.unknown.v9"
        elif case == "wrong-candidate":
            report["candidate"]["bundle_id"] = "f" * 64
        elif case == "empty-samples":
            report["samples"] = []
        elif case == "unstable-sample-id":
            report["samples"][0]["sample_id"] = "not-a-stable-id"
        elif case == "unordered-ordinal":
            report["samples"][0]["ordinal"] = 2
        elif case == "nonfinite-metric":
            report["aggregate"]["delta"]["entropy"] = float("nan")
        elif case == "same-id-not-identity":
            report["baseline"]["bundle_id"] = manifest["bundle_id"]
            report["candidate"]["bundle_id"] = manifest["bundle_id"]
            report["weight_zero_identity"] = False
        elif case == "bad-report-hash":
            report["report_sha256"] = "0" * 64
        else:
            raise AssertionError(case)

    if case == "nonfinite-metric":
        report = json.loads(valid_case["evaluation"].read_text(encoding="utf-8"))
        mutate(report)
        valid_case["evaluation"].write_text(
            json.dumps(
                report,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
                allow_nan=True,
            )
            + "\n",
            encoding="utf-8",
        )
    else:
        _rewrite_evaluation(
            valid_case["evaluation"],
            mutate,
            refresh_hash=case != "bad-report-hash",
        )

    _assert_failed(
        _evaluate(valid_case),
        "evaluation",
        "report",
        "candidate",
        "sample",
        "finite",
        "identity",
    )


@pytest.mark.parametrize(
    "case",
    [
        "wrong-schema",
        "missing-candidate-binding",
        "missing-report-binding",
        "missing-metric",
        "extra-metric",
        "negative-limit",
        "nonfinite-limit",
    ],
)
def test_frozen_limits_have_a_strict_complete_schema(
    valid_case: dict[str, Path],
    case: str,
) -> None:
    limits = json.loads(valid_case["limits"].read_text(encoding="utf-8"))
    maxima = limits["max_absolute_deltas"]
    if case == "wrong-schema":
        limits["schema_version"] = "hesperia.dict_calibration.limits.v2"
    elif case == "missing-candidate-binding":
        del limits["candidate_bundle_id"]
    elif case == "missing-report-binding":
        del limits["evaluation_report_sha256"]
    elif case == "missing-metric":
        del maxima["entropy"]
    elif case == "extra-metric":
        maxima["observed_after_candidate"] = 999
    elif case == "negative-limit":
        maxima["coverage"] = -0.1
    elif case == "nonfinite-limit":
        maxima["entropy"] = math.inf
    _write_json(valid_case["limits"], limits)
    _write_sidecar(valid_case["limits"])

    _assert_failed(_evaluate(valid_case), "limit", "schema", "finite", "complete")


@pytest.mark.parametrize(
    ("metric", "boundary_delta", "above_limit_delta"),
    [
        ("accepted", -1, -2),
        ("rejected", 0, 1),
        ("coverage", -0.1, -0.100001),
        ("entropy", 0.1, 0.100001),
    ],
)
def test_absolute_delta_limits_are_inclusive_and_fail_above_the_maximum(
    valid_case: dict[str, Path],
    metric: str,
    boundary_delta: int | float,
    above_limit_delta: int | float,
) -> None:
    maximum = json.loads(valid_case["limits"].read_text(encoding="utf-8"))[
        "max_absolute_deltas"
    ][metric]
    assert abs(boundary_delta) == maximum
    assert abs(above_limit_delta) > maximum

    def set_consistent_delta(report: dict[str, Any], delta: int | float) -> None:
        aggregate = report["aggregate"]
        aggregate["delta"][metric] = delta
        aggregate["candidate"][metric] = aggregate["baseline"][metric] + delta

    _rewrite_evaluation(
        valid_case["evaluation"],
        lambda report: set_consistent_delta(report, boundary_delta),
    )
    _bind_limits_to_case(valid_case)
    assert _evaluate(valid_case)["pass"] is True

    _rewrite_evaluation(
        valid_case["evaluation"],
        lambda report: set_consistent_delta(report, above_limit_delta),
    )
    _bind_limits_to_case(valid_case)
    _assert_failed(_evaluate(valid_case), metric, "delta", "limit")


def test_every_family_delta_is_checked_against_the_inclusive_limit(
    valid_case: dict[str, Path],
) -> None:
    def set_family_deltas(
        report: dict[str, Any],
        deltas: dict[str, float],
    ) -> None:
        aggregate = report["aggregate"]
        aggregate["delta"]["family_distribution"] = deltas
        baseline = aggregate["baseline"]["family_distribution"]
        aggregate["candidate"]["family_distribution"] = {
            family_id: round(baseline.get(family_id, 0.0) + delta, 6)
            for family_id, delta in deltas.items()
        }

    _rewrite_evaluation(
        valid_case["evaluation"],
        lambda report: set_family_deltas(
            report,
            {"F00": -0.1, "F01": 0.1},
        ),
    )
    _bind_limits_to_case(valid_case)
    assert _evaluate(valid_case)["pass"] is True

    _rewrite_evaluation(
        valid_case["evaluation"],
        lambda report: set_family_deltas(
            report,
            {"F00": -0.100001, "F01": 0.100001},
        ),
    )
    _bind_limits_to_case(valid_case)
    _assert_failed(_evaluate(valid_case), "F01", "family", "delta", "limit")


def test_reported_scalar_and_family_deltas_are_recomputed_from_aggregates(
    valid_case: dict[str, Path],
) -> None:
    def forge_zero_deltas(report: dict[str, Any]) -> None:
        report["aggregate"]["delta"] = {
            "accepted": 0,
            "rejected": 0,
            "coverage": 0.0,
            "entropy": 0.0,
            "family_distribution": {"F00": 0.0, "F01": 0.0},
        }

    _rewrite_evaluation(valid_case["evaluation"], forge_zero_deltas)
    _bind_limits_to_case(valid_case)

    candidate_id = json.loads(
        (valid_case["bundle"] / "manifest.json").read_text(encoding="utf-8")
    )["bundle_id"]
    with pytest.raises(ValueError, match="recompute|forged|delta"):
        _gate_module()._validate_evaluation(
            valid_case["evaluation"],
            candidate_id,
        )


def test_reported_delta_must_keep_candidate_minus_baseline_sign(
    valid_case: dict[str, Path],
) -> None:
    def reverse_signed_deltas(report: dict[str, Any]) -> None:
        delta = report["aggregate"]["delta"]
        delta["accepted"] = -1
        delta["coverage"] = -0.1
        delta["entropy"] = -0.1
        delta["family_distribution"] = {"F00": 0.1, "F01": -0.1}

    _rewrite_evaluation(valid_case["evaluation"], reverse_signed_deltas)
    _bind_limits_to_case(valid_case)
    candidate_id = json.loads(
        (valid_case["bundle"] / "manifest.json").read_text(encoding="utf-8")
    )["bundle_id"]

    with pytest.raises(ValueError, match="signed|candidate.*baseline|delta"):
        _gate_module()._validate_evaluation(
            valid_case["evaluation"],
            candidate_id,
        )


@pytest.mark.parametrize(
    ("case", "expected"),
    [
        ("candidate-mismatch", "candidate"),
        ("report-mismatch", "report"),
        ("edited-with-stale-sidecar", "sidecar"),
        ("missing-sidecar", "sidecar"),
        ("bad-sidecar", "sidecar"),
    ],
)
def test_limits_are_immutable_sidecar_pinned_and_identity_bound(
    valid_case: dict[str, Path],
    case: str,
    expected: str,
) -> None:
    limits_path = valid_case["limits"]
    sidecar = limits_path.with_name(f"{limits_path.name}.sha256")
    if case == "candidate-mismatch":
        _rewrite_limits(
            limits_path,
            lambda limits: limits.__setitem__("candidate_bundle_id", "f" * 64),
        )
    elif case == "report-mismatch":
        _rewrite_limits(
            limits_path,
            lambda limits: limits.__setitem__(
                "evaluation_report_sha256", "e" * 64
            ),
        )
    elif case == "edited-with-stale-sidecar":
        limits = json.loads(limits_path.read_text(encoding="utf-8"))
        limits["max_absolute_deltas"]["accepted"] = 999
        _write_json(limits_path, limits)
    elif case == "missing-sidecar":
        sidecar.unlink()
    elif case == "bad-sidecar":
        sidecar.write_text(f"{'0' * 64}  limits.json\n", encoding="ascii")
    else:
        raise AssertionError(case)

    verdict = _evaluate(valid_case)
    _assert_failed_reason(verdict, expected)


def test_passing_verdict_exposes_the_exact_limits_sha256(
    valid_case: dict[str, Path],
) -> None:
    verdict = _evaluate(valid_case)

    assert verdict["pass"] is True
    assert verdict["limits_sha256"] == _sha256(valid_case["limits"])


@pytest.mark.parametrize("case", ["wrong-expected", "stale-after-self-rewrite"])
def test_external_expected_limits_digest_is_mandatory_and_exact(
    valid_case: dict[str, Path],
    case: str,
) -> None:
    original_expected = valid_case["expected_limits_sha256"]
    if case == "wrong-expected":
        valid_case["expected_limits_sha256"] = "0" * 64
    else:
        _rewrite_limits(
            valid_case["limits"],
            lambda limits: limits["max_absolute_deltas"].__setitem__(
                "accepted", 0.75
            ),
        )
        assert _sha256(valid_case["limits"]) != original_expected

    verdict = _evaluate(valid_case)

    _assert_failed_reason(verdict, "expected", "limits", "digest")


def test_same_bundle_identity_compares_every_sample_payload(
    valid_case: dict[str, Path],
) -> None:
    candidate_id = json.loads(
        (valid_case["bundle"] / "manifest.json").read_text(encoding="utf-8")
    )["bundle_id"]

    def forge_same_bundle_aggregate_identity(report: dict[str, Any]) -> None:
        report["baseline"]["bundle_id"] = candidate_id
        report["candidate"]["bundle_id"] = candidate_id
        report["aggregate"]["candidate"] = dict(report["aggregate"]["baseline"])
        report["aggregate"]["delta"] = {
            "accepted": 0,
            "rejected": 0,
            "coverage": 0.0,
            "entropy": 0.0,
            "family_distribution": {"F00": 0.0},
        }
        report["weight_zero_identity"] = True
        assert report["samples"][0]["baseline"] != report["samples"][0]["candidate"]

    _rewrite_evaluation(
        valid_case["evaluation"],
        forge_same_bundle_aggregate_identity,
    )
    _bind_limits_to_case(valid_case)

    with pytest.raises(ValueError, match="sample|identity|payload"):
        _gate_module()._validate_evaluation(
            valid_case["evaluation"],
            candidate_id,
        )


def test_same_bundle_span_diffs_must_be_unchanged_with_equal_payloads(
    valid_case: dict[str, Path],
) -> None:
    candidate_id = json.loads(
        (valid_case["bundle"] / "manifest.json").read_text(encoding="utf-8")
    )["bundle_id"]

    def forge_changed_span_diff(report: dict[str, Any]) -> None:
        report["baseline"]["bundle_id"] = candidate_id
        report["candidate"]["bundle_id"] = candidate_id
        report["aggregate"]["candidate"] = dict(report["aggregate"]["baseline"])
        report["aggregate"]["delta"] = {
            "accepted": 0,
            "rejected": 0,
            "coverage": 0.0,
            "entropy": 0.0,
            "family_distribution": {"F00": 0.0},
        }
        report["weight_zero_identity"] = True
        sample = report["samples"][0]
        sample["candidate"] = dict(sample["baseline"])
        sample["span_diffs"] = [
            {
                "span_id": "d" * 64,
                "source_char_start": 0,
                "source_char_end": 5,
                "source_text_span": "alpha",
                "status": "changed",
                "baseline": {"winning_concept_id": "C-001"},
                "candidate": {"winning_concept_id": "C-002"},
            }
        ]

    _rewrite_evaluation(valid_case["evaluation"], forge_changed_span_diff)
    _bind_limits_to_case(valid_case)

    with pytest.raises(ValueError, match="span_diffs|unchanged|identity|payload"):
        _gate_module()._validate_evaluation(
            valid_case["evaluation"],
            candidate_id,
        )


@pytest.mark.parametrize("case", ["concept-namespace", "path-marker", "corpus-marker"])
def test_runtime_rows_reject_field_specific_markers_without_checker_help(
    valid_case: dict[str, Path],
    case: str,
) -> None:
    bundle = valid_case["bundle"]
    if case == "concept-namespace":
        for artifact_name in ("dict_a.jsonl", "dict_b.jsonl", "dict_c.jsonl"):
            path = bundle / artifact_name
            text = path.read_text(encoding="utf-8").replace("C-001", "tfp.C-001")
            path.write_text(text, encoding="utf-8")
            _write_sidecar(path)
    elif case == "path-marker":
        path = bundle / "dict_a.jsonl"
        rows = [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        rows[0]["normalized_form"] = "hesperia/modules/tfp/private-token"
        _write_jsonl(path, rows)
        _write_sidecar(path)
    else:
        path = bundle / "dict_c.jsonl"
        rows = [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        rows[0]["normalized_form"] = "tfp_v1/corpus/alpha"
        _write_jsonl(path, rows)
        _write_sidecar(path)

    def refresh_artifact_hashes(manifest: dict[str, Any]) -> None:
        for descriptor in manifest["artifacts"].values():
            artifact = bundle / descriptor["path"]
            descriptor["sha256"] = _sha256(artifact)

    _rewrite_manifest(bundle, refresh_artifact_hashes)
    _bind_evaluation_candidate_to_manifest(valid_case)

    with pytest.raises(ValueError, match="field|namespace|path|corpus|tfp"):
        _gate_module()._validate_artifacts(_artifact_paths(valid_case))


def test_core_production_concept_namespace_is_allowlisted(
    valid_case: dict[str, Path],
) -> None:
    bundle = valid_case["bundle"]
    for artifact_name in ("dict_a.jsonl", "dict_b.jsonl", "dict_c.jsonl"):
        path = bundle / artifact_name
        path.write_text(
            path.read_text(encoding="utf-8").replace("C-001", "core.alpha"),
            encoding="utf-8",
        )

    row_counts = _gate_module()._validate_artifacts(_artifact_paths(valid_case))

    assert row_counts["dict_a_matcher"] == 1
    assert row_counts["dict_b_canonical"] == 2
    assert row_counts["dict_c_runtime_conversion"] == 1


@pytest.mark.parametrize("reference_role", ["dict_a", "dict_b", "dict_c", "dict_d"])
def test_non_core_dotted_concept_namespaces_are_rejected_in_every_role(
    valid_case: dict[str, Path],
    reference_role: str,
) -> None:
    bundle = valid_case["bundle"]
    dict_a_path = bundle / "dict_a.jsonl"
    dict_b_path = bundle / "dict_b.jsonl"
    dict_c_path = bundle / "dict_c.jsonl"
    dict_a = [json.loads(line) for line in dict_a_path.read_text().splitlines()]
    dict_b = [json.loads(line) for line in dict_b_path.read_text().splitlines()]
    dict_c = [json.loads(line) for line in dict_c_path.read_text().splitlines()]
    forbidden = "mrt.private_prompt"

    if reference_role == "dict_a":
        dict_a[0]["candidate_concept_ids"] = [forbidden]
        dict_b.append(
            {
                "concept_id": forbidden,
                "related_concept_ids": [],
                "area_ids": ["A00"],
                "family_ids": ["F02"],
            }
        )
    elif reference_role == "dict_b":
        dict_b[0]["related_concept_ids"] = [forbidden]
        dict_b.append(
            {
                "concept_id": forbidden,
                "related_concept_ids": [],
                "area_ids": ["A00"],
                "family_ids": ["F02"],
            }
        )
    elif reference_role == "dict_c":
        dict_c[0]["candidate_concept_ids"] = [forbidden]
        dict_b.append(
            {
                "concept_id": forbidden,
                "related_concept_ids": [],
                "area_ids": ["A00"],
                "family_ids": ["F02"],
            }
        )
    else:
        dict_b.append(
            {
                "concept_id": forbidden,
                "related_concept_ids": [],
                "area_ids": ["A00"],
                "family_ids": ["F02"],
            }
        )
        dict_d_path = bundle / "dict_d.jsonl"
        _write_jsonl(
            dict_d_path,
            [
                {
                    "concept_id_a": "C-001",
                    "concept_id_b": forbidden,
                    "cooc_count": 2,
                    "npmi": 0.25,
                    "g2": 1.0,
                    "source_books": ["book-001"],
                    "agreement_with_b": "novel",
                }
            ],
        )

    _write_jsonl(dict_a_path, dict_a)
    _write_jsonl(dict_b_path, dict_b)
    _write_jsonl(dict_c_path, dict_c)
    paths = _artifact_paths(valid_case)
    if reference_role == "dict_d":
        paths["dict_d"] = bundle / "dict_d.jsonl"

    with pytest.raises(ValueError, match="namespace|concept|mrt.private_prompt"):
        _gate_module()._validate_artifacts(paths)


@pytest.mark.parametrize(
    "role",
    ["dict_a_matcher", "dict_b_canonical", "dict_c_runtime_conversion", "dict_d"],
)
def test_any_slash_in_runtime_artifact_strings_is_rejected(
    valid_case: dict[str, Path],
    role: str,
) -> None:
    paths = _artifact_paths(valid_case)
    if role == "dict_a_matcher":
        rows = [
            {
                "entry_id": "A-001",
                "normalized_form": "mrt/private",
                "match_type": "exact",
                "candidate_concept_ids": ["C-001"],
            }
        ]
        _write_jsonl(paths[role], rows)
    elif role == "dict_b_canonical":
        rows = [
            {
                "concept_id": "C-001",
                "related_concept_ids": ["C-002"],
                "area_ids": ["A00"],
                "family_ids": ["F/00"],
            },
            {
                "concept_id": "C-002",
                "related_concept_ids": [],
                "area_ids": ["A00"],
                "family_ids": ["F01"],
            },
        ]
        _write_jsonl(paths[role], rows)
    elif role == "dict_c_runtime_conversion":
        rows = [
            {
                "normalized_form": "mrt/private",
                "candidate_concept_ids": ["C-001"],
            }
        ]
        _write_jsonl(paths[role], rows)
    else:
        dict_d_path = valid_case["bundle"] / "dict_d.jsonl"
        _write_jsonl(
            dict_d_path,
            [
                {
                    "concept_id_a": "C-001",
                    "concept_id_b": "C-002",
                    "cooc_count": 2,
                    "npmi": 0.25,
                    "g2": 1.0,
                    "source_books": ["book/001"],
                    "agreement_with_b": "novel",
                }
            ],
        )
        paths[role] = dict_d_path

    with pytest.raises(ValueError, match="slash|path|runtime|string"):
        _gate_module()._validate_artifacts(paths)


@pytest.mark.parametrize("concept_id", ["core.", "core..", "C-"])
def test_degenerate_allowlisted_concept_ids_are_rejected(
    valid_case: dict[str, Path],
    concept_id: str,
) -> None:
    for role in ("dict_a_matcher", "dict_b_canonical", "dict_c_runtime_conversion"):
        path = _artifact_paths(valid_case)[role]
        path.write_text(
            path.read_text(encoding="utf-8").replace("C-001", concept_id),
            encoding="utf-8",
        )

    with pytest.raises(ValueError, match="concept|identifier|namespace|degenerate"):
        _gate_module()._validate_artifacts(_artifact_paths(valid_case))


def test_jsonl_duplicate_object_keys_fail_closed(
    valid_case: dict[str, Path],
) -> None:
    artifact = valid_case["bundle"] / "dict_a.jsonl"
    artifact.write_text(
        (
            '{"entry_id":"A-001","entry_id":"A-002",'
            '"normalized_form":"alpha","match_type":"exact",'
            '"candidate_concept_ids":["C-001"]}\n'
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="duplicate.*key|key.*duplicate"):
        _gate_module()._validate_artifacts(_artifact_paths(valid_case))


def test_gate_accepts_real_freeze_manifest_with_all_evidence_roles(
    valid_case: dict[str, Path],
    tmp_path: Path,
) -> None:
    work = tmp_path / "freeze-work"
    work.mkdir()
    sources = {
        "dict_a_engine.jsonl": [
            {
                "normalized_form": "alpha",
                "candidate_concept_ids": ["C-001"],
            }
        ],
        "dict_a_candidates.jsonl": [{"text": "alpha", "frequency": 3}],
        "dict_a_normalized.jsonl": [{"text": "Alpha", "normalized": "alpha"}],
        "dict_b_anchored.jsonl": [
            {
                "concept_id": "C-001",
                "related_concept_ids": [],
                "area_ids": ["A00"],
                "family_ids": ["F00"],
            }
        ],
        "dict_b_draft.jsonl": [
            {"proposed_concept_id": "proposal-1", "anchor": "C-001"}
        ],
        "dict_b_authored_edges.jsonl": [
            {"source": "C-001", "target": "C-001"}
        ],
        "dict_c_source.jsonl": [{"phrase": "alpha", "source": "book-001"}],
        "dict_c_intermediate.jsonl": [{"phrase": "alpha", "anchor": "C-001"}],
        "dict_c_runtime.jsonl": [
            {"normalized_form": "alpha", "candidate_concept_ids": ["C-001"]}
        ],
    }
    for name, rows in sources.items():
        _write_jsonl(work / name, rows)
    _write_json(work / "evaluation_run.json", {"accuracy": 1.0})
    corpus = tmp_path / "freeze-corpus"
    corpus.mkdir()
    corpus_source = corpus / "book-001.md"
    corpus_source.write_text("# Book\n\nalpha\n", encoding="utf-8")
    frozen_bundle = tmp_path / "frozen-candidate"
    freeze(
        work,
        frozen_bundle,
        provenance={
            "corpus": {
                "path": corpus.as_posix(),
                "source_hashes": {"book-001.md": _sha256(corpus_source)},
            },
            "model": "gpt-5-mini-2025-08-07",
            "prompt_sha256": "3" * 64,
            "checkpoint": "core-d2-w3-freeze-acceptance",
            "resolver": {
                "version": "core-lexical-resolver-v1",
                "configuration_sha256": "4" * 64,
            },
            "segmentation_rule": "frozen-paragraph-segmentation-v1",
            "statistical_rule": "paragraph-cooccurrence-npmi-g2-v1",
            "builder_revision": "core-d2-w3-freeze-acceptance-r1",
        },
    )
    frozen_case = {**valid_case, "bundle": frozen_bundle}
    _bind_evaluation_candidate_to_manifest(frozen_case)

    verdict = _evaluate(frozen_case)

    assert verdict["pass"] is True
    manifest_roles = set(
        json.loads((frozen_bundle / "manifest.json").read_text(encoding="utf-8"))[
            "artifacts"
        ]
    )
    assert {
        "dict_a_proposal_evidence",
        "dict_a_anchor_evidence",
        "dict_b_proposal_evidence",
        "dict_b_authored_edge_provenance",
        "dict_c_source",
        "dict_c_intermediate",
        "evaluation_metrics",
    } <= manifest_roles
    artifact_check = next(
        check for check in verdict["checks"] if check["check_id"] == "02_artifacts"
    )
    assert manifest_roles <= set(artifact_check["evidence"]["row_counts"])


@pytest.mark.parametrize("callback", ["boundary", "readiness"])
def test_candidate_is_revalidated_after_external_callbacks(
    valid_case: dict[str, Path],
    callback: str,
) -> None:
    artifact = valid_case["bundle"] / "dict_a.jsonl"
    mutated = False

    def mutate_artifact_once() -> None:
        nonlocal mutated
        if not mutated:
            artifact.write_bytes(artifact.read_bytes() + b"\n")
            mutated = True

    def boundary(repo_root: Path) -> subprocess.CompletedProcess[str]:
        if callback == "boundary":
            mutate_artifact_once()
        return _passing_boundary(repo_root)

    def runner(
        command: list[str],
        **_kwargs: Any,
    ) -> subprocess.CompletedProcess[str]:
        if callback == "readiness":
            mutate_artifact_once()
        return subprocess.CompletedProcess(command, 0, stdout="ok\n", stderr="")

    verdict = _evaluate(
        valid_case,
        boundary_checker=boundary,
        subprocess_runner=runner,
    )

    assert mutated is True
    _assert_failed_reason(verdict, "revalidation", "changed", "artifact", "manifest")


def test_boundary_checker_is_invoked_with_explicit_repo_root(
    valid_case: dict[str, Path],
) -> None:
    calls: list[Path] = []

    def checker(repo_root: Path) -> subprocess.CompletedProcess[str]:
        calls.append(repo_root)
        return _passing_boundary(repo_root)

    evidence = _gate_module()._validate_boundary(valid_case["repo_root"], checker)
    assert "OK" in evidence
    assert calls == [valid_case["repo_root"]]


def test_missing_or_failing_boundary_checker_fails_closed(
    valid_case: dict[str, Path],
) -> None:
    def failing_checker(repo_root: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            [str(repo_root / "tools/check_core_default_tfp_boundary.py")],
            1,
            stdout="",
            stderr="TFP path drift found\n",
        )

    with pytest.raises(ValueError, match="boundary|TFP path drift"):
        _gate_module()._validate_boundary(
            valid_case["repo_root"],
            failing_checker,
        )


def test_readiness_runs_focused_matcher_resolver_comparison_and_export_probes(
    valid_case: dict[str, Path],
) -> None:
    calls: list[list[str]] = []
    call_kwargs: list[dict[str, Any]] = []

    def recording_runner(
        command: list[str],
        **kwargs: Any,
    ) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        call_kwargs.append(kwargs)
        return subprocess.CompletedProcess(command, 0, stdout="ok\n", stderr="")

    evidence = _gate_module()._validate_readiness(
        valid_case["repo_root"],
        recording_runner,
    )
    assert set(evidence) == {"matcher", "resolver", "evaluate", "export"}
    rendered = [" ".join(command).casefold() for command in calls]
    assert any("matcher" in command and "pytest" in command for command in rendered)
    assert any("resolver" in command and "pytest" in command for command in rendered)
    assert any("evaluate" in command and "pytest" in command for command in rendered)
    assert any("export" in command and "--help" in command for command in rendered)
    assert call_kwargs
    assert all(
        isinstance(kwargs.get("timeout"), (int, float))
        and not isinstance(kwargs["timeout"], bool)
        and math.isfinite(float(kwargs["timeout"]))
        and float(kwargs["timeout"]) > 0
        for kwargs in call_kwargs
    )


def test_default_subprocess_runner_and_boundary_checker_use_finite_timeouts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    gate = _gate_module()
    signature = inspect.signature(gate.evaluate_core_pack)
    default_runner = signature.parameters["subprocess_runner"].default
    assert default_runner is gate._default_subprocess_runner
    calls: list[dict[str, Any]] = []

    def recording_run(
        command: list[str],
        **kwargs: Any,
    ) -> subprocess.CompletedProcess[str]:
        calls.append(kwargs)
        return subprocess.CompletedProcess(command, 0, stdout="ok\n", stderr="")

    monkeypatch.setattr(gate.subprocess, "run", recording_run)
    gate._default_boundary_checker(tmp_path)
    gate._default_subprocess_runner(
        [sys.executable, "-c", "print('ok')"],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        check=False,
    )

    assert len(calls) == 2
    assert all(
        isinstance(kwargs.get("timeout"), (int, float))
        and not isinstance(kwargs["timeout"], bool)
        and math.isfinite(float(kwargs["timeout"]))
        and float(kwargs["timeout"]) > 0
        for kwargs in calls
    )


def test_default_boundary_checker_invokes_committed_self_contained_checker(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    gate = _gate_module()
    calls: list[tuple[list[str], dict[str, Any]]] = []

    def recording_run(
        command: list[str],
        **kwargs: Any,
    ) -> subprocess.CompletedProcess[str]:
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0, stdout="OK\n", stderr="")

    monkeypatch.setattr(gate.subprocess, "run", recording_run)

    gate._default_boundary_checker(tmp_path)

    assert len(calls) == 1
    command, kwargs = calls[0]
    assert command == [
        sys.executable,
        str(tmp_path / "tools/check_core_calibration_boundary.py"),
    ]
    assert kwargs["cwd"] == str(tmp_path)
    assert kwargs["capture_output"] is True
    assert kwargs["text"] is True
    assert kwargs["check"] is False
    assert (
        isinstance(kwargs.get("timeout"), (int, float))
        and not isinstance(kwargs["timeout"], bool)
        and math.isfinite(float(kwargs["timeout"]))
        and float(kwargs["timeout"]) > 0
    )


@pytest.mark.parametrize("failed_probe", ["matcher", "resolver", "evaluate", "export"])
def test_each_required_readiness_probe_fails_closed(
    valid_case: dict[str, Path],
    failed_probe: str,
) -> None:
    def selective_runner(
        command: list[str],
        **_kwargs: Any,
    ) -> subprocess.CompletedProcess[str]:
        rendered = " ".join(command).casefold()
        return subprocess.CompletedProcess(
            command,
            1 if failed_probe in rendered else 0,
            stdout="",
            stderr=f"{failed_probe} evidence failed\n",
        )

    _assert_failed(
        _evaluate(valid_case, subprocess_runner=selective_runner),
        failed_probe,
        "readiness",
        "evidence",
    )


def test_explicit_provenance_mock_and_degraded_false_are_accepted(
    valid_case: dict[str, Path],
) -> None:
    def mark_explicitly_clean(manifest: dict[str, Any]) -> None:
        manifest["provenance"]["mock"] = False
        manifest["provenance"]["degraded"] = False

    _rewrite_manifest(valid_case["bundle"], mark_explicitly_clean)

    manifest, _paths = _gate_module()._validate_manifest(valid_case["bundle"])
    assert manifest["provenance"]["mock"] is False
    assert manifest["provenance"]["degraded"] is False


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("mock", True),
        ("mock", "true"),
        ("mock", 1),
        ("mock", "false"),
        ("degraded", True),
        ("degraded", "true"),
        ("degraded", 1),
        ("degraded", "false"),
    ],
    ids=[
        "mock-bool-true",
        "mock-string-true",
        "mock-int-one",
        "mock-string-false",
        "degraded-bool-true",
        "degraded-string-true",
        "degraded-int-one",
        "degraded-string-false",
    ],
)
def test_explicit_provenance_mock_or_degraded_requires_exact_false(
    valid_case: dict[str, Path],
    key: str,
    value: object,
) -> None:
    _rewrite_manifest(
        valid_case["bundle"],
        lambda manifest: manifest["provenance"].__setitem__(key, value),
    )

    with pytest.raises(ValueError, match=f"{key}|provenance|false"):
        _gate_module()._validate_manifest(valid_case["bundle"])


@pytest.mark.parametrize(
    ("case", "expected"),
    [
        ("mock", "mock"),
        ("quarantined", "quarant"),
        ("degraded", "degraded"),
        ("release-ineligible", "release"),
        ("corpus-path", "path"),
    ],
)
def test_mock_quarantined_degraded_and_path_drift_are_rejected(
    valid_case: dict[str, Path],
    case: str,
    expected: str,
) -> None:
    def mutate(manifest: dict[str, Any]) -> None:
        if case == "mock":
            manifest["provenance"]["model"] = "mock-fixture"
        elif case == "quarantined":
            manifest["state"] = "quarantined"
        elif case == "degraded":
            manifest["profile"] = "exploratory_allow_degraded"
        elif case == "release-ineligible":
            manifest["release_eligibility"] = False
        elif case == "corpus-path":
            manifest["provenance"]["corpus"] = {
                "path": "/data/hesperia/modules/tfp/data/tfp_v1/corpus",
                "source_hashes": {"sample.txt": "5" * 64},
            }

    _rewrite_manifest(valid_case["bundle"], mutate)

    _assert_failed(_evaluate(valid_case), expected)


def test_check_ids_and_verdict_digest_are_stable_and_canonical(
    valid_case: dict[str, Path],
) -> None:
    first = _evaluate(valid_case)
    second = _evaluate(valid_case)

    first_ids = [check["check_id"] for check in first["checks"]]
    second_ids = [check["check_id"] for check in second["checks"]]
    assert first == second
    assert first_ids == second_ids
    assert first_ids == sorted(first_ids)
    assert len(first_ids) == len(set(first_ids))
    assert all(check_id and isinstance(check_id, str) for check_id in first_ids)
    unsigned = {key: value for key, value in first.items() if key != "verdict_sha256"}
    assert first["verdict_sha256"] == _sha256_bytes(_canonical_bytes(unsigned))


def test_cli_emits_json_and_returns_nonzero_for_a_gate_failure(
    valid_case: dict[str, Path],
) -> None:
    (valid_case["bundle"] / "manifest.json").unlink()
    result = subprocess.run(
        [
            sys.executable,
            str(REPO / "tools/core_calibration_pack_gate.py"),
            "--bundle",
            str(valid_case["bundle"]),
            "--evaluation",
            str(valid_case["evaluation"]),
            "--limits",
            str(valid_case["limits"]),
            "--limits-sha256",
            valid_case["expected_limits_sha256"],
            "--repo-root",
            str(valid_case["repo_root"]),
        ],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    verdict = json.loads(result.stdout)
    assert verdict["schema_version"] == GATE_SCHEMA
    assert verdict["pass"] is False


def test_cli_requires_independent_limits_sha256_argument(
    valid_case: dict[str, Path],
) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(REPO / "tools/core_calibration_pack_gate.py"),
            "--bundle",
            str(valid_case["bundle"]),
            "--evaluation",
            str(valid_case["evaluation"]),
            "--limits",
            str(valid_case["limits"]),
            "--repo-root",
            str(valid_case["repo_root"]),
        ],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "limits-sha256" in result.stderr.casefold()
