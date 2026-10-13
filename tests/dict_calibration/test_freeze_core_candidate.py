# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from tools.dict_calibration import release_freeze
from tools.dict_calibration.core_pack_gate import _validate_manifest
from tools.dict_calibration.core_candidate import PRODUCER_FILES, canonical_bytes
from tools.dict_calibration.evaluate import _read_bundle
from tools.dict_calibration.generation_ledger import (
    GENERATION_ENV_KEYS,
    validate_generation_ledger,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.write_bytes(canonical_bytes(value))


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_bytes(b"".join(canonical_bytes(row) for row in rows))


@pytest.fixture()
def release_case(tmp_path: Path) -> dict[str, Any]:
    producer = tmp_path / "generation"
    producer.mkdir()
    draft = {"concept_id": "proposal-alpha", "labels": ["alpha"]}
    _write_jsonl(producer / "dict_b_draft.jsonl", [draft])
    _write_jsonl(
        producer / "dict_b_anchored.jsonl",
        [
            {
                "concept_id": "C-001",
                "related_concept_ids": [],
                "calibration_draft_id": "proposal-alpha",
                "calibration_bind_score": 1.0,
                "calibration_bind_reason": "exact_id",
            }
        ],
    )
    _write_jsonl(producer / "dict_b_rejected.jsonl", [])
    _write_jsonl(
        producer / "dict_a_to_b_links.jsonl",
        [{"lexical": "alpha", "concept_id": "C-001", "match_type": "exact", "priority": 1.0}],
    )
    _write_jsonl(
        producer / "dict_a_engine.jsonl",
        [
            {
                "entry_id": "CAL-00001",
                "surface_form": "alpha",
                "normalized_form": "alpha",
                "match_type": "exact",
                "candidate_concept_ids": ["C-001"],
                "priority": 10,
                "version": "v",
            }
        ],
    )
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    source = corpus / "book.md"
    source.write_text("alpha\n", encoding="utf-8")
    prompt = tmp_path / "prompt.txt"
    prompt.write_text("prompt\n", encoding="utf-8")
    code_paths = {
        "producer": tmp_path / "code/tools/dict_calibration/run_pipeline.py",
        "materializer": tmp_path / "code/tools/dict_calibration/core_candidate.py",
        "evaluator": tmp_path / "code/tools/dict_calibration/evaluate.py",
        "gate": tmp_path / "code/tools/dict_calibration/core_pack_gate.py",
        "exporter": tmp_path / "code/tools/dict_calibration/resolved_export.py",
        "resolver": tmp_path / "code/core/engine/lexical_concept/pipeline.py",
    }
    for role, path in code_paths.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f'ROLE = "{role}"\n', encoding="utf-8")
    configuration_file = tmp_path / "config/core-generation.json"
    configuration_file.parent.mkdir(parents=True)
    configuration_file.write_text('{"domain":"core"}\n', encoding="utf-8")
    evaluation = tmp_path / "evaluation.json"
    _write_json(evaluation, {"schema": "fixture", "accepted": 1})
    source_hashes = {"book.md": _sha256(source)}
    ledger_payload = {
        "schema": "hesperia.dict_calibration.generation_ledger.v1",
        "corpus_root": corpus.resolve().as_posix(),
        "source_hashes": source_hashes,
        "source_count": 1,
        "source_map_sha256": hashlib.sha256(canonical_bytes(source_hashes)).hexdigest(),
        "git_commit": "a" * 40,
        "git_tree_clean": True,
        "code_file_sha256": {
            role: {
                "path": path.resolve().as_posix(),
                "sha256": _sha256(path),
            }
            for role, path in code_paths.items()
        },
        "model_provider": "openai",
        "model_id": "gpt-5-mini",
        "checkpoint_id": "none",
        "prompt_path": prompt.resolve().as_posix(),
        "prompt_sha256": _sha256(prompt),
        "configuration": {
            "resolver_version": "core-lexical-resolver-v1",
            "resolver_configuration_sha256": "4" * 64,
            "segmentation_rule": "frozen-paragraph-segmentation-v1",
            "statistical_rule": "paragraph-cooccurrence-npmi-g2-v1",
            "complete": True,
            "files": {
                "core_config": {
                    "path": configuration_file.resolve().as_posix(),
                    "sha256": _sha256(configuration_file),
                }
            },
            "values": {"domain": "core"},
        },
        "environment": {
            "complete": True,
            "values": {key: "" for key in GENERATION_ENV_KEYS},
        },
        "random_seed": 17,
        "worker_count": 2,
        "batch_size": 40,
        "batch_ordering_rule": "source_path_then_ordinal",
        "retry_policy": {"attempts": 3, "backoff": "deterministic"},
        "generation_started_at": "2026-09-16T10:00:00Z",
    }
    identity_payload = dict(ledger_payload)
    identity_payload.pop("generation_started_at")
    ledger = {
        **ledger_payload,
        "generation_id": hashlib.sha256(canonical_bytes(identity_payload)).hexdigest(),
    }
    ledger_path = producer / "generation_ledger.json"
    _write_json(ledger_path, ledger)
    return {
        "producer": producer,
        "ledger": ledger_path,
        "ledger_sha256": _sha256(ledger_path),
        "evaluation": evaluation,
        "destination": tmp_path / "candidate",
        "git": ("a" * 40, True),
        "code_paths": code_paths,
    }


def test_release_freeze_writes_manifest_v2_counts_and_independent_bindings(
    release_case: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(release_freeze, "_git_snapshot", lambda: release_case["git"])

    result = release_freeze.freeze_core_candidate(
        producer_dir=release_case["producer"],
        generation_ledger=release_case["ledger"],
        expected_ledger_sha256=release_case["ledger_sha256"],
        evaluation_metrics=release_case["evaluation"],
        destination=release_case["destination"],
    )

    manifest_path = release_case["destination"] / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "hesperia.dict_calibration.freeze_manifest.v2"
    assert manifest["generation"]["generation_id"] == result["generation_id"]
    assert manifest["generation"]["ledger_sha256"] == release_case["ledger_sha256"]
    assert all("row_count" in descriptor for descriptor in manifest["artifacts"].values())
    edge = manifest["artifacts"]["dict_b_authored_edge_provenance"]
    assert edge["row_count"] == 0
    assert edge["evidence_status"] == "truthful_zero"
    assert edge["sha256"] == hashlib.sha256(b"").hexdigest()
    assert result["manifest_sha256"] == _sha256(manifest_path)
    assert _read_bundle(release_case["destination"])["bundle_id"] == result["bundle_id"]
    validated, paths = _validate_manifest(
        release_case["destination"],
        require_manifest_v2=True,
    )
    assert validated["bundle_id"] == result["bundle_id"]
    assert set(paths) == set(manifest["artifacts"])


@pytest.mark.parametrize("binding", ["code", "configuration", "environment"])
def test_generation_ledger_requires_complete_named_bindings(
    release_case: dict[str, Any],
    binding: str,
) -> None:
    ledger = json.loads(release_case["ledger"].read_text(encoding="utf-8"))
    if binding == "code":
        del ledger["code_file_sha256"]["exporter"]
    elif binding == "configuration":
        ledger["configuration"]["complete"] = False
    else:
        ledger["environment"]["complete"] = False
    identity = {
        key: value
        for key, value in ledger.items()
        if key not in {"generation_id", "generation_started_at"}
    }
    ledger["generation_id"] = hashlib.sha256(canonical_bytes(identity)).hexdigest()

    with pytest.raises(ValueError, match=binding):
        validate_generation_ledger(ledger, git_snapshot=release_case["git"])


def test_generation_ledger_rejects_empty_environment_map(
    release_case: dict[str, Any],
) -> None:
    ledger = json.loads(release_case["ledger"].read_text(encoding="utf-8"))
    ledger["environment"]["values"] = {}
    identity = {
        key: value
        for key, value in ledger.items()
        if key not in {"generation_id", "generation_started_at"}
    }
    ledger["generation_id"] = hashlib.sha256(canonical_bytes(identity)).hexdigest()

    with pytest.raises(ValueError, match="environment key set"):
        validate_generation_ledger(ledger, git_snapshot=release_case["git"])


def test_generation_ledger_rejects_one_file_for_all_code_roles(
    release_case: dict[str, Any],
) -> None:
    ledger = json.loads(release_case["ledger"].read_text(encoding="utf-8"))
    reused = ledger["code_file_sha256"]["producer"]
    ledger["code_file_sha256"] = {
        role: dict(reused)
        for role in ledger["code_file_sha256"]
    }
    identity = {
        key: value
        for key, value in ledger.items()
        if key not in {"generation_id", "generation_started_at"}
    }
    ledger["generation_id"] = hashlib.sha256(canonical_bytes(identity)).hexdigest()

    with pytest.raises(ValueError, match="six distinct paths"):
        validate_generation_ledger(ledger, git_snapshot=release_case["git"])


def test_generation_ledger_rejects_unknown_observable_generation_env(
    release_case: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ledger = json.loads(release_case["ledger"].read_text(encoding="utf-8"))
    monkeypatch.setenv("HESPERIA_CALIB_UNDECLARED_SWITCH", "1")

    with pytest.raises(ValueError, match="unknown undeclared"):
        validate_generation_ledger(ledger, git_snapshot=release_case["git"])


@pytest.mark.parametrize("mutation", ["ledger-pin", "producer", "evaluation"])
def test_release_freeze_rejects_mutation_without_publication(
    release_case: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    monkeypatch.setattr(release_freeze, "_git_snapshot", lambda: release_case["git"])
    if mutation == "ledger-pin":
        release_case["ledger_sha256"] = "f" * 64
    elif mutation == "producer":
        path = release_case["producer"] / PRODUCER_FILES[0]
        path.write_bytes(path.read_bytes() + b"\n")
    else:
        release_case["evaluation"].write_text('{"accepted":NaN}\n', encoding="utf-8")

    with pytest.raises(ValueError):
        release_freeze.freeze_core_candidate(
            producer_dir=release_case["producer"],
            generation_ledger=release_case["ledger"],
            expected_ledger_sha256=release_case["ledger_sha256"],
            evaluation_metrics=release_case["evaluation"],
            destination=release_case["destination"],
        )

    assert not release_case["destination"].exists() or not any(
        release_case["destination"].iterdir()
    )
    assert not list(release_case["destination"].parent.glob(".candidate.freeze-*"))


def test_post_rename_validation_failure_rolls_back_publication(
    release_case: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(release_freeze, "_git_snapshot", lambda: release_case["git"])
    real_validate = release_freeze._validate_built_bundle
    calls = 0

    def fail_second_validation(bundle: Path) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise ValueError("post-rename validation failure")
        return real_validate(bundle)

    monkeypatch.setattr(release_freeze, "_validate_built_bundle", fail_second_validation)

    with pytest.raises(ValueError, match="post-rename"):
        release_freeze.freeze_core_candidate(
            producer_dir=release_case["producer"],
            generation_ledger=release_case["ledger"],
            expected_ledger_sha256=release_case["ledger_sha256"],
            evaluation_metrics=release_case["evaluation"],
            destination=release_case["destination"],
        )

    assert not release_case["destination"].exists()


def test_semantically_equal_metrics_byte_mutation_fails_closed(
    release_case: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(release_freeze, "_git_snapshot", lambda: release_case["git"])
    real_write = release_freeze._write

    def mutate_metrics_after_snapshot(path: Path, content: bytes) -> None:
        real_write(path, content)
        if path.name == "metrics.json":
            release_case["evaluation"].write_text(
                '{ "accepted": 1, "schema": "fixture" }\n',
                encoding="utf-8",
            )

    monkeypatch.setattr(release_freeze, "_write", mutate_metrics_after_snapshot)

    with pytest.raises(ValueError, match="metrics.*mutated"):
        release_freeze.freeze_core_candidate(
            producer_dir=release_case["producer"],
            generation_ledger=release_case["ledger"],
            expected_ledger_sha256=release_case["ledger_sha256"],
            evaluation_metrics=release_case["evaluation"],
            destination=release_case["destination"],
        )

    assert not release_case["destination"].exists()
