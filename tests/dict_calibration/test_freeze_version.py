# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

from __future__ import annotations

import hashlib
import json
import shutil
import stat
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from tools.dict_calibration import freeze_version
from tools.dict_calibration.freeze_version import freeze


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n",
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


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _provenance(corpus: Path) -> dict[str, Any]:
    corpus.mkdir(parents=True, exist_ok=True)
    source_files = {
        "book-001.md": "# Book 001\n\nAlpha corpus paragraph.\n",
        "book-002.md": "# Book 002\n\nBeta corpus paragraph.\n",
    }
    for name, content in source_files.items():
        (corpus / name).write_text(content, encoding="utf-8")
    return {
        "corpus": {
            "path": corpus.as_posix(),
            "source_hashes": {
                name: _sha256(corpus / name)
                for name in source_files
            },
        },
        "model": "gpt-5-mini-2025-08-07",
        "prompt_sha256": "3" * 64,
        "checkpoint": "core-d2-w1-checkpoint-017",
        "resolver": {
            "version": "core-lexical-resolver-v1",
            "configuration_sha256": "4" * 64,
        },
        "segmentation_rule": "frozen-paragraph-segmentation-v1",
        "statistical_rule": "paragraph-cooccurrence-npmi-g2-v1",
        "builder_revision": "core-d2-freeze-builder-r1",
    }


@pytest.fixture()
def work_dir(tmp_path: Path) -> Path:
    work = tmp_path / "work"
    work.mkdir()
    _write_jsonl(
        work / "dict_a_engine.jsonl",
        [{"normalized_form": "alpha", "candidate_concept_ids": ["C-001"]}],
    )
    _write_jsonl(
        work / "dict_a_candidates.jsonl",
        [{"text": "alpha", "frequency": 7}],
    )
    _write_jsonl(
        work / "dict_a_normalized.jsonl",
        [{"text": "Alpha", "normalized": "alpha"}],
    )
    _write_jsonl(
        work / "dict_b_anchored.jsonl",
        [{"concept_id": "C-001", "related_concept_ids": ["C-002"]}],
    )
    _write_jsonl(
        work / "dict_b_draft.jsonl",
        [{"proposed_concept_id": "proposal-1", "anchor": "C-001"}],
    )
    _write_jsonl(
        work / "dict_b_authored_edges.jsonl",
        [{"source": "C-001", "target": "C-002", "authored_by": "seed"}],
    )
    _write_jsonl(
        work / "dict_c_source.jsonl",
        [{"phrase": "alpha beta", "source": "acb"}],
    )
    _write_jsonl(
        work / "dict_c_intermediate.jsonl",
        [{"phrase": "alpha beta", "anchor": "C-001"}],
    )
    _write_jsonl(
        work / "dict_c_runtime.jsonl",
        [
            {
                "normalized_form": "alpha beta",
                "candidate_concept_ids": ["C-001"],
                "priority": 99,
            }
        ],
    )
    _write_json(work / "evaluation_run.json", {"accuracy": 0.75})
    return work


def _freeze_w1(
    work_dir: Path,
    version_dir: Path,
    *,
    dict_d_validator: Callable[[Path], bool | str] | None = None,
) -> None:
    corpus = work_dir.parent / "corpus"
    corpus.mkdir(exist_ok=True)
    freeze(
        work_dir,
        version_dir,
        provenance=_provenance(corpus),
        dict_d_validator=dict_d_validator,
    )


def _manifest(version_dir: Path) -> dict[str, Any]:
    return json.loads((version_dir / "manifest.json").read_text(encoding="utf-8"))


def _canonical_manifest_payload(manifest: dict[str, Any]) -> bytes:
    payload = {key: value for key, value in manifest.items() if key != "bundle_id"}
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _output_bytes(version_dir: Path) -> dict[str, bytes]:
    return {
        path.relative_to(version_dir).as_posix(): path.read_bytes()
        for path in sorted(version_dir.rglob("*"))
        if path.is_file()
    }


def test_freeze_writes_candidate_manifest_with_exact_artifact_roles(
    work_dir: Path,
    tmp_path: Path,
) -> None:
    version_dir = tmp_path / "v1"

    _freeze_w1(work_dir, version_dir)

    manifest = _manifest(version_dir)
    assert manifest["schema_version"] == "hesperia.dict_calibration.freeze_manifest.v1"
    assert manifest["state"] == "candidate"
    assert manifest["supersedes"] is None
    assert {
        role: entry["path"]
        for role, entry in manifest["artifacts"].items()
    } == {
        "dict_a_matcher": "dict_a.jsonl",
        "dict_a_proposal_evidence": "evidence/dict_a_candidates.jsonl",
        "dict_a_anchor_evidence": "evidence/dict_a_normalized.jsonl",
        "dict_b_canonical": "dict_b.jsonl",
        "dict_b_proposal_evidence": "evidence/dict_b_draft.jsonl",
        "dict_b_authored_edge_provenance": "evidence/dict_b_authored_edges.jsonl",
        "dict_c_source": "evidence/dict_c_source.jsonl",
        "dict_c_intermediate": "evidence/dict_c_intermediate.jsonl",
        "dict_c_runtime_conversion": "dict_c.jsonl",
        "evaluation_metrics": "metrics.json",
    }


def test_freeze_separates_matcher_ready_dict_a_from_proposal_and_anchor_evidence(
    work_dir: Path,
    tmp_path: Path,
) -> None:
    version_dir = tmp_path / "v1"

    _freeze_w1(work_dir, version_dir)

    assert (version_dir / "dict_a.jsonl").read_bytes() == (
        work_dir / "dict_a_engine.jsonl"
    ).read_bytes()
    assert not (version_dir / "dict_a_candidates.jsonl").exists()
    assert not (version_dir / "dict_a_normalized.jsonl").exists()
    assert (version_dir / "evidence/dict_a_candidates.jsonl").is_file()
    assert (version_dir / "evidence/dict_a_normalized.jsonl").is_file()


def test_freeze_keeps_canonical_dict_b_and_authored_edge_provenance_distinct(
    work_dir: Path,
    tmp_path: Path,
) -> None:
    version_dir = tmp_path / "v1"

    _freeze_w1(work_dir, version_dir)

    assert (version_dir / "dict_b.jsonl").read_bytes() == (
        work_dir / "dict_b_anchored.jsonl"
    ).read_bytes()
    assert (version_dir / "evidence/dict_b_authored_edges.jsonl").read_bytes() == (
        work_dir / "dict_b_authored_edges.jsonl"
    ).read_bytes()
    assert (version_dir / "dict_b.jsonl").read_bytes() != (
        version_dir / "evidence/dict_b_authored_edges.jsonl"
    ).read_bytes()


def test_freeze_records_dict_c_source_intermediate_and_runtime_conversion_status(
    work_dir: Path,
    tmp_path: Path,
) -> None:
    version_dir = tmp_path / "v1"

    _freeze_w1(work_dir, version_dir)

    artifacts = _manifest(version_dir)["artifacts"]
    assert artifacts["dict_c_source"]["status"] == "source_evidence"
    assert artifacts["dict_c_intermediate"]["status"] == "intermediate_evidence"
    assert artifacts["dict_c_runtime_conversion"]["status"] == "matcher_ready"
    assert (version_dir / "dict_c.jsonl").read_bytes() == (
        work_dir / "dict_c_runtime.jsonl"
    ).read_bytes()


@pytest.mark.parametrize(
    "validator",
    [None, lambda _path: False],
    ids=["missing", "rejecting"],
)
def test_freeze_rejects_optional_dict_d_without_successful_strict_validator(
    work_dir: Path,
    tmp_path: Path,
    validator: Callable[[Path], bool] | None,
) -> None:
    _write_jsonl(work_dir / "dict_d.jsonl", [{"concept_id_a": "C-001", "concept_id_b": "C-002"}])

    with pytest.raises(ValueError, match="Dict D.*validator"):
        _freeze_w1(work_dir, tmp_path / "v1", dict_d_validator=validator)


def test_freeze_includes_dict_d_only_after_strict_validator_succeeds(
    work_dir: Path,
    tmp_path: Path,
) -> None:
    source = work_dir / "dict_d.jsonl"
    _write_jsonl(source, [{"concept_id_a": "C-001", "concept_id_b": "C-002"}])
    validated: list[Path] = []

    def strict_validator(path: Path) -> bool:
        validated.append(path)
        return path == source and _sha256(path) == _sha256(source)

    version_dir = tmp_path / "v1"
    _freeze_w1(work_dir, version_dir, dict_d_validator=strict_validator)

    assert validated == [source]
    assert (version_dir / "dict_d.jsonl").read_bytes() == source.read_bytes()
    assert _manifest(version_dir)["artifacts"]["dict_d"]["status"] == "validated_optional"


def test_freeze_writes_sha256_sidecars_for_every_artifact_and_manifest(
    work_dir: Path,
    tmp_path: Path,
) -> None:
    version_dir = tmp_path / "v1"

    _freeze_w1(work_dir, version_dir)

    manifest = _manifest(version_dir)
    artifact_paths = [
        version_dir / entry["path"]
        for entry in manifest["artifacts"].values()
    ]
    for artifact in artifact_paths:
        sidecar = artifact.with_name(f"{artifact.name}.sha256")
        assert sidecar.read_text(encoding="ascii") == (
            f"{_sha256(artifact)}  {artifact.name}\n"
        )
        assert manifest["artifacts"][
            next(
                role
                for role, entry in manifest["artifacts"].items()
                if entry["path"] == artifact.relative_to(version_dir).as_posix()
            )
        ]["sha256"] == _sha256(artifact)

    manifest_sidecar = version_dir / "manifest.json.sha256"
    assert manifest_sidecar.read_text(encoding="ascii") == (
        f"{_sha256(version_dir / 'manifest.json')}  manifest.json\n"
    )


def test_freeze_pins_stable_corpus_and_build_provenance(
    work_dir: Path,
    tmp_path: Path,
) -> None:
    version_dir = tmp_path / "v1"

    _freeze_w1(work_dir, version_dir)

    provenance = _manifest(version_dir)["provenance"]
    assert provenance == _provenance(work_dir.parent / "corpus")
    assert list(provenance["corpus"]["source_hashes"]) == [
        "book-001.md",
        "book-002.md",
    ]


def test_freeze_refuses_to_overwrite_any_non_empty_destination(
    work_dir: Path,
    tmp_path: Path,
) -> None:
    version_dir = tmp_path / "v1"
    version_dir.mkdir()
    sentinel = version_dir / "existing.txt"
    sentinel.write_text("immutable\n", encoding="utf-8")

    with pytest.raises(FileExistsError, match="non-empty"):
        _freeze_w1(work_dir, version_dir)

    assert sentinel.read_text(encoding="utf-8") == "immutable\n"
    assert list(version_dir.iterdir()) == [sentinel]


def test_legacy_freeze_call_remains_accepted_for_existing_callers(
    work_dir: Path,
    tmp_path: Path,
) -> None:
    version_dir = tmp_path / "legacy"

    freeze(work_dir, version_dir)

    assert (version_dir / "dict_a.jsonl").is_file()
    assert (version_dir / "dict_b.jsonl").is_file()
    assert (version_dir / "metrics.json").is_file()


@pytest.mark.parametrize(
    "missing_key",
    [
        None,
        "corpus",
        "model",
        "prompt_sha256",
        "checkpoint",
        "resolver",
        "resolver.configuration_sha256",
        "segmentation_rule",
        "statistical_rule",
        "builder_revision",
    ],
    ids=[
        "empty",
        "corpus",
        "model",
        "prompt",
        "checkpoint",
        "resolver",
        "resolver-config",
        "segmentation-rule",
        "statistical-rule",
        "builder-revision",
    ],
)
def test_candidate_freeze_rejects_empty_or_incomplete_provenance(
    work_dir: Path,
    tmp_path: Path,
    missing_key: str | None,
) -> None:
    provenance = _provenance(work_dir.parent / "corpus")
    if missing_key is None:
        provenance = {}
    elif "." in missing_key:
        parent, child = missing_key.split(".", maxsplit=1)
        del provenance[parent][child]
    else:
        del provenance[missing_key]

    with pytest.raises(ValueError, match="provenance"):
        freeze(work_dir, tmp_path / "v1", provenance=provenance)


@pytest.mark.parametrize(
    "artifact_name",
    [
        "dict_a_engine.jsonl",
        "dict_a_candidates.jsonl",
        "dict_a_normalized.jsonl",
        "dict_b_anchored.jsonl",
        "dict_b_draft.jsonl",
        "dict_b_authored_edges.jsonl",
        "dict_c_source.jsonl",
        "dict_c_intermediate.jsonl",
        "dict_c_runtime.jsonl",
    ],
)
def test_candidate_freeze_rejects_malformed_required_jsonl(
    work_dir: Path,
    tmp_path: Path,
    artifact_name: str,
) -> None:
    (work_dir / artifact_name).write_text('{"truncated":\n', encoding="utf-8")

    with pytest.raises(ValueError, match=artifact_name):
        _freeze_w1(work_dir, tmp_path / "v1")


def test_candidate_manifest_has_deterministic_bundle_identity(
    work_dir: Path,
    tmp_path: Path,
) -> None:
    version_dir = tmp_path / "v1"

    _freeze_w1(work_dir, version_dir)

    manifest = _manifest(version_dir)
    expected = hashlib.sha256(_canonical_manifest_payload(manifest)).hexdigest()
    assert manifest["bundle_id"] == expected


def test_legacy_freeze_refuses_to_overwrite_non_empty_destination(
    work_dir: Path,
    tmp_path: Path,
) -> None:
    version_dir = tmp_path / "legacy"
    version_dir.mkdir()
    sentinel = version_dir / "dict_a.jsonl"
    sentinel.write_text("existing immutable bytes\n", encoding="utf-8")

    with pytest.raises(FileExistsError, match="non-empty"):
        freeze(work_dir, version_dir)

    assert sentinel.read_text(encoding="utf-8") == "existing immutable bytes\n"
    assert list(version_dir.iterdir()) == [sentinel]


def test_candidate_freeze_rejects_missing_evaluation(
    work_dir: Path,
    tmp_path: Path,
) -> None:
    (work_dir / "evaluation_run.json").unlink()

    with pytest.raises(FileNotFoundError, match="evaluation"):
        _freeze_w1(work_dir, tmp_path / "v1")


def test_candidate_freeze_publishes_non_private_readable_directories(
    work_dir: Path,
    tmp_path: Path,
) -> None:
    version_dir = tmp_path / "v1"

    _freeze_w1(work_dir, version_dir)

    for directory in [version_dir, version_dir / "evidence"]:
        mode = stat.S_IMODE(directory.stat().st_mode)
        assert mode & 0o055 == 0o055, (
            f"{directory.relative_to(tmp_path)} must be group/other readable "
            f"and traversable, got {mode:#o}"
        )


def test_identical_candidate_freezes_are_byte_identical(
    work_dir: Path,
    tmp_path: Path,
) -> None:
    first = tmp_path / "v1-first"
    second = tmp_path / "v1-second"

    _freeze_w1(work_dir, first)
    _freeze_w1(work_dir, second)

    assert _output_bytes(first) == _output_bytes(second)


def test_validator_failure_preserves_empty_destination_and_cleans_temp_directory(
    work_dir: Path,
    tmp_path: Path,
) -> None:
    _write_jsonl(
        work_dir / "dict_d.jsonl",
        [{"concept_id_a": "C-001", "concept_id_b": "C-002"}],
    )
    version_dir = tmp_path / "v1"
    version_dir.mkdir()

    with pytest.raises(ValueError, match="Dict D.*validator"):
        _freeze_w1(work_dir, version_dir, dict_d_validator=lambda _path: False)

    assert version_dir.is_dir()
    assert list(version_dir.iterdir()) == []
    assert list(tmp_path.glob(f".{version_dir.name}.freeze-*")) == []


def test_copy_failure_preserves_empty_destination_and_cleans_temp_directory(
    work_dir: Path,
    tmp_path: Path,
) -> None:
    (work_dir / "dict_c_runtime.jsonl").unlink()
    version_dir = tmp_path / "v1"
    version_dir.mkdir()

    with pytest.raises(FileNotFoundError, match="dict_c_runtime"):
        _freeze_w1(work_dir, version_dir)

    assert version_dir.is_dir()
    assert list(version_dir.iterdir()) == []
    assert list(tmp_path.glob(f".{version_dir.name}.freeze-*")) == []


def test_dict_d_digest_validator_rejects_bytes_changed_after_validation(
    work_dir: Path,
    tmp_path: Path,
) -> None:
    source = work_dir / "dict_d.jsonl"
    _write_jsonl(
        source,
        [{"concept_id_a": "C-001", "concept_id_b": "C-002", "npmi": 0.5}],
    )
    validated_digest = _sha256(source)

    def validate_then_mutate(path: Path) -> str:
        assert _sha256(path) == validated_digest
        _write_jsonl(
            path,
            [{"concept_id_a": "C-001", "concept_id_b": "C-003", "npmi": 0.9}],
        )
        return validated_digest

    version_dir = tmp_path / "v1"
    with pytest.raises(ValueError, match="Dict D.*(changed|digest)"):
        _freeze_w1(
            work_dir,
            version_dir,
            dict_d_validator=validate_then_mutate,
        )

    assert not version_dir.exists()
    assert list(tmp_path.glob(f".{version_dir.name}.freeze-*")) == []


@pytest.mark.parametrize(
    ("artifact_name", "invalid_row"),
    [
        ("dict_a_engine.jsonl", {"candidate_concept_ids": ["C-001"]}),
        ("dict_a_engine.jsonl", {"normalized_form": "alpha", "candidate_concept_ids": []}),
        ("dict_a_candidates.jsonl", {"text": "alpha"}),
        ("dict_a_normalized.jsonl", {"text": "Alpha"}),
        ("dict_b_anchored.jsonl", {"concept_id": "C-001"}),
        (
            "dict_b_anchored.jsonl",
            {"concept_id": "C-001", "related_concept_ids": "C-002"},
        ),
        ("dict_b_draft.jsonl", {"proposed_concept_id": "proposal-1"}),
        ("dict_b_authored_edges.jsonl", {"source": "C-001"}),
        ("dict_c_source.jsonl", {"phrase": "alpha beta"}),
        ("dict_c_intermediate.jsonl", {"phrase": "alpha beta"}),
        ("dict_c_runtime.jsonl", {"normalized_form": "alpha beta"}),
        (
            "dict_c_runtime.jsonl",
            {"normalized_form": "alpha beta", "candidate_concept_ids": []},
        ),
    ],
    ids=[
        "dict-a-matcher-normalized-form",
        "dict-a-matcher-nonempty-candidates",
        "dict-a-proposal-fields",
        "dict-a-anchor-fields",
        "dict-b-canonical-related-ids",
        "dict-b-canonical-related-list",
        "dict-b-proposal-fields",
        "dict-b-authored-edge-fields",
        "dict-c-source-fields",
        "dict-c-intermediate-fields",
        "dict-c-runtime-fields",
        "dict-c-runtime-nonempty-candidates",
    ],
)
def test_candidate_freeze_rejects_role_specific_schema_violations(
    work_dir: Path,
    tmp_path: Path,
    artifact_name: str,
    invalid_row: dict[str, Any],
) -> None:
    _write_jsonl(work_dir / artifact_name, [invalid_row])

    with pytest.raises(ValueError, match=artifact_name):
        _freeze_w1(work_dir, tmp_path / "v1")


def test_candidate_freeze_rejects_nonexistent_corpus_path(
    work_dir: Path,
    tmp_path: Path,
) -> None:
    provenance = _provenance(work_dir.parent / "corpus")
    provenance["corpus"]["path"] = (tmp_path / "missing-corpus").as_posix()

    with pytest.raises(ValueError, match="corpus.*path"):
        freeze(work_dir, tmp_path / "v1", provenance=provenance)


def test_candidate_freeze_rejects_corpus_source_hash_mismatch(
    work_dir: Path,
    tmp_path: Path,
) -> None:
    provenance = _provenance(work_dir.parent / "corpus")
    provenance["corpus"]["source_hashes"]["book-001.md"] = "f" * 64

    with pytest.raises(ValueError, match="book-001.md.*(hash|digest)"):
        freeze(work_dir, tmp_path / "v1", provenance=provenance)


@pytest.mark.parametrize(
    "unsafe_source_key",
    ["/absolute/book-001.md", "../book-001.md"],
    ids=["absolute", "traversal"],
)
def test_candidate_freeze_rejects_unsafe_corpus_source_hash_keys(
    work_dir: Path,
    tmp_path: Path,
    unsafe_source_key: str,
) -> None:
    provenance = _provenance(work_dir.parent / "corpus")
    digest = provenance["corpus"]["source_hashes"].pop("book-001.md")
    provenance["corpus"]["source_hashes"][unsafe_source_key] = digest

    with pytest.raises(ValueError, match="source_hashes.*path"):
        freeze(work_dir, tmp_path / "v1", provenance=provenance)


def test_candidate_freeze_rejects_symlinked_required_artifact(
    work_dir: Path,
    tmp_path: Path,
) -> None:
    source = work_dir / "dict_a_engine.jsonl"
    external = tmp_path / "external-dict-a.jsonl"
    shutil.copy2(source, external)
    source.unlink()
    source.symlink_to(external)

    with pytest.raises(ValueError, match="dict_a_engine.jsonl.*symlink"):
        _freeze_w1(work_dir, tmp_path / "v1")


def test_candidate_freeze_rejects_cross_generation_source_mutation(
    work_dir: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    already_copied = work_dir / "dict_a_engine.jsonl"
    original_copy2 = shutil.copy2

    def copy_and_mutate_prior_source(
        source: str | Path,
        destination: str | Path,
        *args: Any,
        **kwargs: Any,
    ) -> str:
        result = original_copy2(source, destination, *args, **kwargs)
        if Path(source).name == "dict_c_runtime.jsonl":
            _write_jsonl(
                already_copied,
                [
                    {
                        "normalized_form": "changed-after-copy",
                        "candidate_concept_ids": ["C-999"],
                    }
                ],
            )
        return result

    monkeypatch.setattr(freeze_version.shutil, "copy2", copy_and_mutate_prior_source)

    with pytest.raises(ValueError, match="(generation|snapshot|changed)"):
        _freeze_w1(work_dir, tmp_path / "v1")


@pytest.mark.parametrize(
    "mutable_input",
    ["evaluation", "corpus"],
)
def test_candidate_freeze_rejects_non_artifact_input_mutation(
    work_dir: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutable_input: str,
) -> None:
    version_dir = tmp_path / "v1"
    evaluation = work_dir / "evaluation_run.json"
    corpus_source = work_dir.parent / "corpus" / "book-001.md"
    original_copy2 = shutil.copy2

    def copy_and_mutate_frozen_input(
        source: str | Path,
        destination: str | Path,
        *args: Any,
        **kwargs: Any,
    ) -> str:
        result = original_copy2(source, destination, *args, **kwargs)
        if Path(source).name == "dict_c_runtime.jsonl":
            if mutable_input == "evaluation":
                _write_json(evaluation, {"accuracy": 0.01, "mutated": True})
            else:
                corpus_source.write_text(
                    "# Book 001\n\nMutated during freeze.\n",
                    encoding="utf-8",
                )
        return result

    monkeypatch.setattr(freeze_version.shutil, "copy2", copy_and_mutate_frozen_input)

    with pytest.raises(ValueError, match="(input|generation|snapshot|changed)"):
        _freeze_w1(work_dir, version_dir)

    assert not version_dir.exists()
    assert list(tmp_path.glob(f".{version_dir.name}.freeze-*")) == []
