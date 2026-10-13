# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

from __future__ import annotations

import hashlib
import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from core.lexical.normalization import normalize_text
from tools.dict_calibration import evaluate, resolved_export


SHA_A = "a" * 64
SHA_B = "b" * 64
SHA_C = "c" * 64
SHA_D = "d" * 64
SHA_E = "e" * 64
REPO = Path(__file__).resolve().parents[2]
_release_export_resolved_sources = resolved_export.export_resolved_sources


@pytest.fixture(autouse=True)
def _route_custom_runners_through_private_test_seam(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def test_dispatch(**kwargs: Any) -> dict[str, Any]:
        runner = kwargs.get("runner", resolved_export.run_dlcr_pipeline)
        if runner is resolved_export.run_dlcr_pipeline:
            return _release_export_resolved_sources(**kwargs)
        return resolved_export._export_resolved_sources_for_test(**kwargs)

    monkeypatch.setattr(
        resolved_export,
        "export_resolved_sources",
        test_dispatch,
    )


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _resolver_trace(weight: float | None) -> dict[str, Any]:
    return {"resolver_trace": {"dict_d_effective_weight": weight}}


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(
            json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
            for row in rows
        ),
        encoding="utf-8",
    )


def _write_bundle(
    bundle: Path,
    *,
    match_type: str = "exact",
    specificity_rank: int = 50,
) -> Path:
    bundle.mkdir()
    dict_a = bundle / "dict_a.jsonl"
    dict_b = bundle / "dict_b.jsonl"
    dict_c = bundle / "dict_c.jsonl"
    _write_jsonl(
        dict_a,
        [
            {
                "entry_id": "A-CANDIDATE",
                "normalized_form": "alpha",
                "match_type": match_type,
                "candidate_concept_ids": ["C-CANDIDATE"],
            }
        ],
    )
    _write_jsonl(
        dict_b,
        [
            {
                "concept_id": "C-CANDIDATE",
                "preferred_label": "Candidate",
                "definition": "Candidate concept from the supplied frozen bundle.",
                "family_ids": ["F00"],
                "area_ids": ["A00"],
                "specificity_rank": specificity_rank,
                "related_concept_ids": [],
                "hex_anchor": "HX-0001",
            }
        ],
    )
    _write_jsonl(
        dict_c,
        [{"concept_id": "C-CANDIDATE", "runtime_label": "Candidate"}],
    )
    corpus_evidence = bundle / "source.md"
    corpus_evidence.write_text("alpha\n", encoding="utf-8")
    manifest_payload = {
        "schema_version": "hesperia.dict_calibration.freeze_manifest.v1",
        "state": "candidate",
        "supersedes": None,
        "artifacts": {
            "dict_a_matcher": {
                "path": dict_a.name,
                "sha256": _sha256(dict_a),
                "status": "matcher_ready",
            },
            "dict_b_canonical": {
                "path": dict_b.name,
                "sha256": _sha256(dict_b),
                "status": "canonical",
            },
            "dict_c_runtime_conversion": {
                "path": dict_c.name,
                "sha256": _sha256(dict_c),
                "status": "runtime_ready",
            },
        },
        "provenance": {
            "corpus": {
                "path": ".",
                "source_hashes": {
                    corpus_evidence.name: _sha256(corpus_evidence),
                },
            },
            "model": "gpt-5-mini-2025-08-07",
            "prompt_sha256": SHA_C,
            "checkpoint": "core-d2-041-test",
            "resolver": {
                "version": "core-lexical-resolver-v1",
                "configuration_sha256": SHA_D,
            },
            "segmentation_rule": "frozen-paragraph-segmentation-v1",
            "statistical_rule": "paragraph-cooccurrence-npmi-g2-v1",
            "builder_revision": "core-d2-041-test-r1",
        },
    }
    manifest = {
        **manifest_payload,
        "bundle_id": _sha256_bytes(_canonical_bytes(manifest_payload)),
    }
    manifest_path = bundle / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (bundle / "manifest.json.sha256").write_text(
        f"{_sha256(manifest_path)}  manifest.json\n",
        encoding="ascii",
    )
    return bundle


class RecordingRunner:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def __call__(
        self,
        text: str,
        *,
        repo_root: Path,
        dict_a_paths: list[Path],
        dict_b_paths: list[Path],
        anchors_path: Path,
        mode: str,
        empirical_weight_override: float | None = None,
    ) -> dict[str, Any]:
        self.calls.append(
            {
                "text": text,
                "repo_root": repo_root,
                "dict_a_paths": dict_a_paths,
                "dict_b_paths": dict_b_paths,
                "dict_a_bytes": dict_a_paths[0].read_bytes(),
                "dict_b_bytes": dict_b_paths[0].read_bytes(),
                "anchors": json.loads(anchors_path.read_text(encoding="utf-8")),
                "mode": mode,
                "empirical_weight_override": empirical_weight_override,
            }
        )
        canonical_text = normalize_text(text)["canonical_text"]
        return {
            "canonical_text": canonical_text,
            "span_resolutions": [
                {
                    "source_char_start": 0,
                    "source_char_end": len(canonical_text),
                    "source_text_span": canonical_text,
                    "candidate_scores": {"C-CANDIDATE": 1.0},
                    "winning_concept_id": "C-CANDIDATE",
                    "rejected_reason_codes": [],
                }
            ],
            "unresolved_span_resolutions": [],
            "resolver_trace": {
                "dict_d_effective_weight": empirical_weight_override,
            },
        }


class CanonicalSpanRunner:
    def __init__(
        self,
        canonical_text: str,
        spans: list[tuple[int, int]],
    ) -> None:
        self.canonical_text = canonical_text
        self.spans = spans

    def __call__(
        self,
        text: str,
        *,
        repo_root: Path,
        dict_a_paths: list[Path],
        dict_b_paths: list[Path],
        anchors_path: Path,
        mode: str,
        empirical_weight_override: float | None = None,
    ) -> dict[str, Any]:
        return {
            "canonical_text": self.canonical_text,
            "span_resolutions": [
                {
                    "source_char_start": start,
                    "source_char_end": end,
                    "source_text_span": self.canonical_text[start:end],
                    "candidate_scores": {"C-CANDIDATE": 1.0},
                    "winning_concept_id": "C-CANDIDATE",
                    "rejected_reason_codes": [],
                }
                for start, end in self.spans
            ],
            "unresolved_span_resolutions": [],
            **_resolver_trace(empirical_weight_override),
        }


class IdentityRoundTripRunner:
    def __call__(
        self,
        text: str,
        *,
        repo_root: Path,
        dict_a_paths: list[Path],
        dict_b_paths: list[Path],
        anchors_path: Path,
        mode: str,
        empirical_weight_override: float | None = None,
    ) -> dict[str, Any]:
        canonical_text = normalize_text(text)["canonical_text"]
        resolutions = {
            "alpha beta alpha": [
                (0, 5, {"C-ALPHA": 1.0, "C-OTHER": 0.25}, "C-ALPHA", []),
                (6, 10, {"C-BETA": 0.8}, "C-BETA", []),
                (11, 16, {"C-ALPHA": 0.9}, "C-ALPHA", []),
            ],
            "gamma unresolved": [
                (0, 5, {"C-GAMMA": 0.4}, None, ["below_threshold"]),
            ],
            "beta alpha": [
                (0, 4, {"C-BETA": 0.75}, "C-BETA", []),
                (5, 10, {"C-ALPHA": 0.95}, "C-ALPHA", []),
            ],
            "unresolved alpha": [
                (11, 16, {"C-ALPHA": 0.49}, None, ["below_threshold"]),
            ],
        }
        span_records = [
            {
                "source_char_start": start,
                "source_char_end": end,
                "source_text_span": canonical_text[start:end],
                "candidate_scores": scores,
                "winning_concept_id": winner,
                "rejected_reason_codes": reasons,
            }
            for start, end, scores, winner, reasons in resolutions[canonical_text]
        ]
        return {
            "canonical_text": canonical_text,
            "span_resolutions": [
                record
                for record in span_records
                if record["winning_concept_id"] is not None
            ],
            "unresolved_span_resolutions": [
                record
                for record in span_records
                if record["winning_concept_id"] is None
            ],
            **_resolver_trace(empirical_weight_override),
        }


class ScoreVectorRunner:
    candidate_scores = {
        "C-FRACTION": 0.125,
        "C-NEGATIVE": -2.5,
        "C-NEGATIVE-ZERO": -0.0,
        "C-POSITIVE-INTEGER": 3,
        "C-POSITIVE-WHOLE-FLOAT": 4.0,
        "C-ZERO": 0,
    }

    def __call__(
        self,
        text: str,
        *,
        repo_root: Path,
        dict_a_paths: list[Path],
        dict_b_paths: list[Path],
        anchors_path: Path,
        mode: str,
        empirical_weight_override: float | None = None,
    ) -> dict[str, Any]:
        canonical_text = normalize_text(text)["canonical_text"]
        return {
            "canonical_text": canonical_text,
            "span_resolutions": [
                {
                    "source_char_start": 0,
                    "source_char_end": 5,
                    "source_text_span": canonical_text[:5],
                    "candidate_scores": dict(self.candidate_scores),
                    "winning_concept_id": "C-FRACTION",
                    "rejected_reason_codes": [],
                }
            ],
            "unresolved_span_resolutions": [
                {
                    "source_char_start": 6,
                    "source_char_end": 10,
                    "source_text_span": canonical_text[6:10],
                    "candidate_scores": dict(self.candidate_scores),
                    "winning_concept_id": None,
                    "rejected_reason_codes": ["below_threshold"],
                },
            ],
            **_resolver_trace(empirical_weight_override),
        }


class MixedResolutionRunner:
    def __call__(
        self,
        text: str,
        *,
        repo_root: Path,
        dict_a_paths: list[Path],
        dict_b_paths: list[Path],
        anchors_path: Path,
        mode: str,
        empirical_weight_override: float | None = None,
    ) -> dict[str, Any]:
        canonical_text = normalize_text(text)["canonical_text"]
        spans = {
            "alpha beta gamma": [
                (0, 5, {"C-ALPHA": 1.0}, "C-ALPHA", []),
                (
                    6,
                    10,
                    {"C-BETA": 0.49, "C-OTHER": 0.25},
                    None,
                    ["candidate_rejected:C-BETA", "below_threshold"],
                ),
                (11, 16, {}, None, ["no_candidates"]),
            ],
            "delta epsilon": [
                (6, 13, {"C-EPSILON": 0.4}, None, ["below_threshold"]),
                (0, 5, {"C-DELTA": 0.9}, "C-DELTA", []),
            ],
        }
        span_records = [
            {
                "source_char_start": start,
                "source_char_end": end,
                "source_text_span": canonical_text[start:end],
                "candidate_scores": scores,
                "winning_concept_id": winner,
                "rejected_reason_codes": reasons,
            }
            for start, end, scores, winner, reasons in spans[canonical_text]
        ]
        return {
            "canonical_text": canonical_text,
            "span_resolutions": [
                record
                for record in span_records
                if record["winning_concept_id"] is not None
            ],
            "unresolved_span_resolutions": [
                record
                for record in span_records
                if record["winning_concept_id"] is None
            ],
            **_resolver_trace(empirical_weight_override),
        }


class AlternateRecordingRunner:
    def __init__(self) -> None:
        self.delegate = RecordingRunner()

    def __call__(
        self,
        text: str,
        *,
        repo_root: Path,
        dict_a_paths: list[Path],
        dict_b_paths: list[Path],
        anchors_path: Path,
        mode: str,
        empirical_weight_override: float | None = None,
    ) -> dict[str, Any]:
        return self.delegate(
            text,
            repo_root=repo_root,
            dict_a_paths=dict_a_paths,
            dict_b_paths=dict_b_paths,
            anchors_path=anchors_path,
            mode=mode,
            empirical_weight_override=empirical_weight_override,
        )


class CodeMutatingRunner:
    def __init__(self) -> None:
        self.delegate = RecordingRunner()

    def __call__(
        self,
        text: str,
        *,
        repo_root: Path,
        dict_a_paths: list[Path],
        dict_b_paths: list[Path],
        anchors_path: Path,
        mode: str,
        empirical_weight_override: float | None = None,
    ) -> dict[str, Any]:
        output = self.delegate(
            text,
            repo_root=repo_root,
            dict_a_paths=dict_a_paths,
            dict_b_paths=dict_b_paths,
            anchors_path=anchors_path,
            mode=mode,
            empirical_weight_override=empirical_weight_override,
        )
        type(self).__call__.__code__ = type(self).replacement.__code__
        return output

    def replacement(
        self,
        text: str,
        *,
        repo_root: Path,
        dict_a_paths: list[Path],
        dict_b_paths: list[Path],
        anchors_path: Path,
        mode: str,
        empirical_weight_override: float | None = None,
    ) -> dict[str, Any]:
        raise AssertionError("mutated callback implementation must never run")


def _paragraph_id(book_sha256: str, ordinal: int, text: str) -> str:
    identity = f"{book_sha256}\0{ordinal}\0{text}".encode()
    return hashlib.sha256(identity).hexdigest()


def _valid_export() -> dict[str, Any]:
    first_text = "alpha beta"
    second_text = "gamma"
    first_id = _paragraph_id(SHA_D, 0, first_text)
    second_id = _paragraph_id(SHA_D, 1, second_text)
    return {
        "schema": "hesperia.dict_d.resolved_corpus.v1",
        "provenance": {
            "candidate_bundle_id": SHA_A,
            "candidate_manifest_sha256": SHA_B,
            "corpus_snapshot_sha256": SHA_C,
            "resolver_version": "lexical-concept-resolver-v1",
            "resolver_implementation_sha256": SHA_A,
            "resolver_authority": "canonical-run-dlcr-pipeline",
            "resolver_configuration_sha256": SHA_E,
            "segmentation_rule": "frozen-paragraph-segmentation-v1",
            "export_rule": "resolved-corpus-export-v1",
            "dict_d_enabled": False,
            "dict_d_effective_weight": 0.0,
        },
        "books": [
            {
                "book_id": "book-001",
                "source_path": "001-alpha.md",
                "source_sha256": SHA_D,
                "paragraphs": [
                    {
                        "paragraph_id": first_id,
                        "source_ordinal": 0,
                        "text": first_text,
                        "resolved_spans": [
                            {
                                "span_position": 0,
                                "span_end": 5,
                                "surface": "alpha",
                                "winning_concept_id": "C-0001",
                                "candidate_scores": [
                                    {"concept_id": "C-0001", "score": 1.0},
                                    {"concept_id": "C-0002", "score": 0.25},
                                ],
                            },
                            {
                                "span_position": 6,
                                "span_end": 10,
                                "surface": "beta",
                                "winning_concept_id": "C-0002",
                                "candidate_scores": [
                                    {"concept_id": "C-0002", "score": 0.75}
                                ],
                            },
                        ],
                    },
                    {
                        "paragraph_id": second_id,
                        "source_ordinal": 1,
                        "text": second_text,
                        "resolved_spans": [],
                    },
                ],
            }
        ],
        "unresolved": [
            {
                "book_id": "book-001",
                "paragraph_id": second_id,
                "span_position": 0,
                "span_end": 5,
                "surface": "gamma",
                "reason_codes": ["no_candidates"],
                "candidate_scores": [],
            }
        ],
    }


def test_valid_export_has_stable_canonical_bytes() -> None:
    payload = _valid_export()
    reordered = {
        key: payload[key]
        for key in ("unresolved", "books", "provenance", "schema")
    }

    first = resolved_export.canonicalize_resolved_export(payload)
    second = resolved_export.canonicalize_resolved_export(reordered)

    assert first == second
    assert first.endswith(b"\n")
    assert json.loads(first) == payload


def test_exporter_uses_supplied_bundle_not_process_global_dictionaries(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle = _write_bundle(tmp_path / "candidate")
    source = tmp_path / "input.md"
    source.write_text("alpha", encoding="utf-8")
    explicit_repo = tmp_path / "repo"
    runner = RecordingRunner()
    monkeypatch.setenv("HESPERIA_DICT_A_PATH", "/must/not/load/global-a.jsonl")
    monkeypatch.setenv("HESPERIA_DICT_B_PATH", "/must/not/load/global-b.jsonl")

    export = resolved_export.export_resolved_sources(
        bundle_path=bundle,
        source_files=[source],
        repo_path=explicit_repo,
        runner=runner,
    )

    assert len(runner.calls) == 1
    call = runner.calls[0]
    assert call["dict_a_paths"] != [bundle / "dict_a.jsonl"]
    assert call["dict_b_paths"] != [bundle / "dict_b.jsonl"]
    assert call["dict_a_bytes"] == (bundle / "dict_a.jsonl").read_bytes()
    assert call["dict_b_bytes"] == (bundle / "dict_b.jsonl").read_bytes()
    assert call["anchors"] == {"C-CANDIDATE": "HX-0001"}
    assert call["repo_root"] == explicit_repo
    assert call["mode"] == "core"
    assert call["empirical_weight_override"] == 0.0
    assert export["provenance"]["candidate_bundle_id"] == json.loads(
        (bundle / "manifest.json").read_text(encoding="utf-8")
    )["bundle_id"]
    assert export["provenance"]["dict_d_enabled"] is False
    assert export["provenance"]["dict_d_effective_weight"] == 0.0
    assert export["books"][0]["paragraphs"][0]["resolved_spans"][0][
        "winning_concept_id"
    ] == "C-CANDIDATE"
    resolved_export._validate_resolved_export(
        export,
        allow_test_authority=True,
    )


def test_exporter_rejects_runner_without_empirical_override_contract(
    tmp_path: Path,
) -> None:
    bundle = _write_bundle(tmp_path / "candidate")
    source = tmp_path / "input.md"
    source.write_text("alpha", encoding="utf-8")

    def runner_without_override(
        text: str,
        *,
        repo_root: Path,
        dict_a_paths: list[Path],
        dict_b_paths: list[Path],
        anchors_path: Path,
        mode: str,
    ) -> dict[str, Any]:
        raise AssertionError("incompatible runner must not execute")

    with pytest.raises(ValueError, match="empirical_weight_override"):
        resolved_export.export_resolved_sources(
            bundle_path=bundle,
            source_files=[source],
            repo_path=tmp_path / "repo",
            runner=runner_without_override,
        )


def test_exporter_rejects_runner_that_ignores_empirical_override(
    tmp_path: Path,
) -> None:
    bundle = _write_bundle(tmp_path / "candidate")
    source = tmp_path / "input.md"
    source.write_text("alpha", encoding="utf-8")

    def ignoring_runner(text: str, **_kwargs: Any) -> dict[str, Any]:
        return {
            "canonical_text": text,
            "span_resolutions": [],
            "unresolved_span_resolutions": [],
        }

    with pytest.raises(ValueError, match="Dict D off override"):
        resolved_export.export_resolved_sources(
            bundle_path=bundle,
            source_files=[source],
            repo_path=tmp_path / "repo",
            runner=ignoring_runner,
        )


def test_exporter_rejects_boolean_claim_as_dict_d_off_proof(
    tmp_path: Path,
) -> None:
    bundle = _write_bundle(tmp_path / "candidate")
    source = tmp_path / "input.md"
    source.write_text("alpha", encoding="utf-8")

    def false_claim_runner(text: str, **_kwargs: Any) -> dict[str, Any]:
        return {
            "canonical_text": text,
            "span_resolutions": [],
            "unresolved_span_resolutions": [],
            "resolver_trace": {"dict_d_effective_weight": False},
        }

    with pytest.raises(ValueError, match="Dict D off override"):
        resolved_export.export_resolved_sources(
            bundle_path=bundle,
            source_files=[source],
            repo_path=tmp_path / "repo",
            runner=false_claim_runner,
        )


def test_release_export_rejects_caller_supplied_runner_before_execution(
    tmp_path: Path,
) -> None:
    bundle = _write_bundle(tmp_path / "candidate")
    source = tmp_path / "input.md"
    source.write_text("alpha", encoding="utf-8")
    called = False

    def lying_runner(text: str, **_kwargs: Any) -> dict[str, Any]:
        nonlocal called
        called = True
        return {
            "canonical_text": text,
            "span_resolutions": [],
            "unresolved_span_resolutions": [],
            "resolver_trace": {"dict_d_effective_weight": 0.0},
        }

    with pytest.raises(ValueError, match="canonical run_dlcr_pipeline"):
        _release_export_resolved_sources(
            bundle_path=bundle,
            source_files=[source],
            repo_path=tmp_path / "repo",
            runner=lying_runner,
        )

    assert called is False


def test_private_runner_output_is_marked_test_only(
    tmp_path: Path,
) -> None:
    bundle = _write_bundle(tmp_path / "candidate")
    source = tmp_path / "input.md"
    source.write_text("alpha", encoding="utf-8")

    export = resolved_export._export_resolved_sources_for_test(
        bundle_path=bundle,
        source_files=[source],
        repo_path=tmp_path / "repo",
        runner=RecordingRunner(),
    )

    assert export["provenance"]["resolver_authority"] == "private-test-runner"


def test_public_validation_and_canonicalization_reject_test_authority() -> None:
    private_export = _valid_export()
    private_export["provenance"]["resolver_authority"] = "private-test-runner"

    with pytest.raises(ValueError, match="canonical resolver authority"):
        resolved_export.validate_resolved_export(private_export)
    with pytest.raises(ValueError, match="canonical resolver authority"):
        resolved_export.canonicalize_resolved_export(private_export)


def test_private_validation_helpers_explicitly_allow_test_authority() -> None:
    private_export = _valid_export()
    private_export["provenance"]["resolver_authority"] = "private-test-runner"

    resolved_export._validate_resolved_export(
        private_export,
        allow_test_authority=True,
    )
    assert json.loads(
        resolved_export._canonicalize_resolved_export(
            private_export,
            allow_test_authority=True,
        )
    ) == private_export


def test_exporter_resolves_with_real_pipeline_from_supplied_bundle(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle = _write_bundle(tmp_path / "candidate")
    source = tmp_path / "input.md"
    source.write_text("alpha", encoding="utf-8")
    monkeypatch.setenv("HESPERIA_DICT_A_PATH", "/must/not/load/global-a.jsonl")
    monkeypatch.setenv("HESPERIA_DICT_B_PATH", "/must/not/load/global-b.jsonl")

    export = resolved_export.export_resolved_sources(
        bundle_path=bundle,
        source_files=[source],
        repo_path=REPO,
    )

    spans = export["books"][0]["paragraphs"][0]["resolved_spans"]
    assert [span["winning_concept_id"] for span in spans] == ["C-CANDIDATE"]
    assert (
        export["provenance"]["resolver_authority"]
        == "canonical-run-dlcr-pipeline"
    )


def test_real_pipeline_threshold_rejection_emits_one_unresolved_record(
    tmp_path: Path,
) -> None:
    bundle = _write_bundle(
        tmp_path / "candidate",
        match_type="pattern",
        specificity_rank=0,
    )
    source = tmp_path / "input.md"
    source.write_text("alpha", encoding="utf-8")
    anchors = tmp_path / "anchors.json"
    anchors.write_text(
        json.dumps({"C-CANDIDATE": "HX-0001"}),
        encoding="utf-8",
    )

    with resolved_export._isolated_pipeline_environment():
        pipeline_output = resolved_export.run_dlcr_pipeline(
            "alpha",
            repo_root=REPO,
            dict_a_paths=[bundle / "dict_a.jsonl"],
            dict_b_paths=[bundle / "dict_b.jsonl"],
            anchors_path=anchors,
            mode="core",
        )

    assert pipeline_output["span_resolutions"] == []
    assert len(pipeline_output["unresolved_span_resolutions"]) == 1
    unresolved_span = pipeline_output["unresolved_span_resolutions"][0]
    assert unresolved_span["winning_concept_id"] is None
    assert unresolved_span["rejected_reason_codes"] == [
        "below_threshold",
        "candidate_rejected:C-CANDIDATE",
    ]
    evaluation_view = evaluate._evaluation_view(pipeline_output)
    assert evaluation_view["coverage"] == 0.0
    assert _canonical_bytes(
        {
            "concept_weights": evaluation_view["concept_weights"],
            "family_activation": evaluation_view["family_activation"],
            "span_resolutions": evaluation_view["span_resolutions"],
        }
    ) == _canonical_bytes(
        {
            "concept_weights": {},
            "family_activation": {},
            "span_resolutions": [],
        }
    )

    export = resolved_export.export_resolved_sources(
        bundle_path=bundle,
        source_files=[source],
        repo_path=REPO,
    )

    paragraph = export["books"][0]["paragraphs"][0]
    assert paragraph["resolved_spans"] == []
    assert export["books"][0]["paragraphs"][0]["text"] == "alpha"
    assert export["unresolved"] == [
        {
            "book_id": export["books"][0]["book_id"],
            "paragraph_id": paragraph["paragraph_id"],
            "span_position": 0,
            "span_end": 5,
            "surface": "alpha",
            "reason_codes": [
                "below_threshold",
                "candidate_rejected:C-CANDIDATE",
            ],
            "candidate_scores": [
                {"concept_id": "C-CANDIDATE", "score": 0.175},
            ],
        }
    ]
    assert export["provenance"]["dict_d_enabled"] is False


def test_exporter_segments_normalized_lines_at_blank_boundaries(
    tmp_path: Path,
) -> None:
    bundle = _write_bundle(tmp_path / "candidate")
    source = tmp_path / "input.md"
    source_bytes = (
        b"\r\nalpha\r\nbeta\r\n \t \r\n\r\n"
        b"gamma\ndelta\r\r\n"
    )
    source.write_bytes(source_bytes)
    runner = RecordingRunner()

    export = resolved_export.export_resolved_sources(
        bundle_path=bundle,
        source_files=[source],
        repo_path=tmp_path / "repo",
        runner=runner,
    )

    paragraphs = export["books"][0]["paragraphs"]
    assert [call["text"] for call in runner.calls] == [
        "alpha\nbeta",
        "gamma\ndelta",
    ]
    assert [paragraph["text"] for paragraph in paragraphs] == [
        "alpha\nbeta",
        "gamma\ndelta",
    ]
    assert [paragraph["source_ordinal"] for paragraph in paragraphs] == [0, 1]
    assert export["books"][0]["source_sha256"] == _sha256_bytes(source_bytes)


def test_exporter_discards_empty_segments_and_preserves_unicode_and_whitespace(
    tmp_path: Path,
) -> None:
    bundle = _write_bundle(tmp_path / "candidate")
    source = tmp_path / "input.md"
    paragraph_texts = ["  café e\u0301  ", "漢字\n🙂\ttext"]
    source.write_text(
        "\n \t\n" + paragraph_texts[0] + "\n\t\n\n" + paragraph_texts[1] + "\n  \n",
        encoding="utf-8",
    )
    runner = RecordingRunner()

    export = resolved_export.export_resolved_sources(
        bundle_path=bundle,
        source_files=[source],
        repo_path=tmp_path / "repo",
        runner=runner,
    )

    paragraphs = export["books"][0]["paragraphs"]
    assert [call["text"] for call in runner.calls] == paragraph_texts
    assert [paragraph["text"] for paragraph in paragraphs] == paragraph_texts
    assert len(paragraphs) == 2


def test_exporter_paragraph_ids_and_offsets_are_stable_and_local(
    tmp_path: Path,
) -> None:
    bundle = _write_bundle(tmp_path / "candidate")
    source = tmp_path / "input.md"
    source.write_text("alpha one\n\nbeta two", encoding="utf-8")
    runner = RecordingRunner()

    export = resolved_export.export_resolved_sources(
        bundle_path=bundle,
        source_files=[source],
        repo_path=tmp_path / "repo",
        runner=runner,
    )

    book = export["books"][0]
    assert [
        (paragraph["source_ordinal"], paragraph["paragraph_id"])
        for paragraph in book["paragraphs"]
    ] == [
        (0, _paragraph_id(book["source_sha256"], 0, "alpha one")),
        (1, _paragraph_id(book["source_sha256"], 1, "beta two")),
    ]
    assert [
        (
            paragraph["resolved_spans"][0]["span_position"],
            paragraph["resolved_spans"][0]["span_end"],
            paragraph["resolved_spans"][0]["surface"],
        )
        for paragraph in book["paragraphs"]
    ] == [
        (0, len("alpha one"), "alpha one"),
        (0, len("beta two"), "beta two"),
    ]


def test_exporter_round_trip_preserves_all_source_and_resolution_identities(
    tmp_path: Path,
) -> None:
    bundle = _write_bundle(tmp_path / "candidate")
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    source_texts = {
        "book-one.md": "ALPHA beta alpha\n\ngamma unresolved",
        "book-two.txt": "beta ALPHA\n\nunresolved alpha",
    }
    for source_path, text in source_texts.items():
        (corpus / source_path).write_text(text, encoding="utf-8")

    exported = resolved_export.export_resolved_sources(
        bundle_path=bundle,
        source_files=[corpus],
        repo_path=tmp_path / "repo",
        runner=IdentityRoundTripRunner(),
    )
    round_tripped = json.loads(
        resolved_export._canonicalize_resolved_export(
            exported,
            allow_test_authority=True,
        )
    )

    resolved_export._validate_resolved_export(
        round_tripped,
        allow_test_authority=True,
    )
    assert round_tripped == exported
    assert [
        (
            book["source_path"],
            book["book_id"],
            book["source_sha256"],
        )
        for book in round_tripped["books"]
    ] == [
        (
            source_path,
            _sha256_bytes(source_path.encode("utf-8")),
            _sha256_bytes(text.encode("utf-8")),
        )
        for source_path, text in source_texts.items()
    ]

    paragraphs = [
        (book, paragraph)
        for book in round_tripped["books"]
        for paragraph in book["paragraphs"]
    ]
    assert [
        (
            book["source_path"],
            paragraph["source_ordinal"],
            paragraph["text"],
            paragraph["paragraph_id"],
        )
        for book, paragraph in paragraphs
    ] == [
        (
            "book-one.md",
            0,
            "ALPHA beta alpha",
            _paragraph_id(
                _sha256_bytes(source_texts["book-one.md"].encode("utf-8")),
                0,
                "ALPHA beta alpha",
            ),
        ),
        (
            "book-one.md",
            1,
            "gamma unresolved",
            _paragraph_id(
                _sha256_bytes(source_texts["book-one.md"].encode("utf-8")),
                1,
                "gamma unresolved",
            ),
        ),
        (
            "book-two.txt",
            0,
            "beta ALPHA",
            _paragraph_id(
                _sha256_bytes(source_texts["book-two.txt"].encode("utf-8")),
                0,
                "beta ALPHA",
            ),
        ),
        (
            "book-two.txt",
            1,
            "unresolved alpha",
            _paragraph_id(
                _sha256_bytes(source_texts["book-two.txt"].encode("utf-8")),
                1,
                "unresolved alpha",
            ),
        ),
    ]

    resolved_spans = [
        (book, paragraph, span)
        for book, paragraph in paragraphs
        for span in paragraph["resolved_spans"]
    ]
    assert [
        (
            book["source_path"],
            paragraph["source_ordinal"],
            span["span_position"],
            span["span_end"],
            span["surface"],
            span["winning_concept_id"],
        )
        for book, paragraph, span in resolved_spans
    ] == [
        ("book-one.md", 0, 0, 5, "ALPHA", "C-ALPHA"),
        ("book-one.md", 0, 6, 10, "beta", "C-BETA"),
        ("book-one.md", 0, 11, 16, "alpha", "C-ALPHA"),
        ("book-two.txt", 0, 0, 4, "beta", "C-BETA"),
        ("book-two.txt", 0, 5, 10, "ALPHA", "C-ALPHA"),
    ]
    assert all(
        span["surface"]
        == paragraph["text"][span["span_position"]:span["span_end"]]
        for _book, paragraph, span in resolved_spans
    )
    assert all(
        span["winning_concept_id"]
        in {candidate["concept_id"] for candidate in span["candidate_scores"]}
        for _book, _paragraph, span in resolved_spans
    )
    unresolved_records = round_tripped["unresolved"]
    assert [
        (
            unresolved["book_id"],
            unresolved["paragraph_id"],
            unresolved["span_position"],
            unresolved["span_end"],
            unresolved["surface"],
            [candidate["concept_id"] for candidate in unresolved["candidate_scores"]],
        )
        for unresolved in unresolved_records
    ] == [
        (
            round_tripped["books"][0]["book_id"],
            round_tripped["books"][0]["paragraphs"][1]["paragraph_id"],
            0,
            5,
            "gamma",
            ["C-GAMMA"],
        ),
        (
            round_tripped["books"][1]["book_id"],
            round_tripped["books"][1]["paragraphs"][1]["paragraph_id"],
            11,
            16,
            "alpha",
            ["C-ALPHA"],
        ),
    ]
    paragraphs_by_id = {
        paragraph["paragraph_id"]: paragraph
        for _book, paragraph in paragraphs
    }
    assert all(
        unresolved["surface"]
        == paragraphs_by_id[unresolved["paragraph_id"]]["text"][
            unresolved["span_position"]:unresolved["span_end"]
        ]
        for unresolved in unresolved_records
    )


def test_exporter_emits_every_unresolved_span_once_with_truthful_reason_codes(
    tmp_path: Path,
) -> None:
    bundle = _write_bundle(tmp_path / "candidate")
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "book-b.md").write_text("delta epsilon", encoding="utf-8")
    (corpus / "book-a.md").write_text("alpha beta gamma", encoding="utf-8")

    export = resolved_export.export_resolved_sources(
        bundle_path=bundle,
        source_files=[corpus],
        repo_path=tmp_path / "repo",
        runner=MixedResolutionRunner(),
    )

    resolved = [
        (
            book["book_id"],
            paragraph["paragraph_id"],
            span["span_position"],
            span["span_end"],
        )
        for book in export["books"]
        for paragraph in book["paragraphs"]
        for span in paragraph["resolved_spans"]
    ]
    unresolved = [
        (
            record["book_id"],
            record["paragraph_id"],
            record["span_position"],
            record["span_end"],
        )
        for record in export["unresolved"]
    ]
    assert len(resolved) == 2
    assert len(unresolved) == 3
    assert len(unresolved) == len(set(unresolved))
    assert set(resolved).isdisjoint(unresolved)
    assert [
        (
            next(
                book["source_path"]
                for book in export["books"]
                if book["book_id"] == record["book_id"]
            ),
            record["span_position"],
            record["span_end"],
            record["surface"],
            record["candidate_scores"],
            record["reason_codes"],
        )
        for record in export["unresolved"]
    ] == [
        (
            "book-a.md",
            6,
            10,
            "beta",
            [
                {"concept_id": "C-BETA", "score": 0.49},
                {"concept_id": "C-OTHER", "score": 0.25},
            ],
            ["below_threshold", "candidate_rejected:C-BETA"],
        ),
        (
            "book-a.md",
            11,
            16,
            "gamma",
            [],
            ["no_candidates"],
        ),
        (
            "book-b.md",
            6,
            13,
            "epsilon",
            [{"concept_id": "C-EPSILON", "score": 0.4}],
            ["below_threshold"],
        ),
    ]
    resolved_export._validate_resolved_export(
        export,
        allow_test_authority=True,
    )


@pytest.mark.parametrize(
    "reasons",
    [
        None,
        [],
        "below_threshold",
        [1],
        [""],
        [" below_threshold"],
        ["below-threshold"],
        ["below_threshold", "below_threshold"],
    ],
)
def test_exporter_rejects_missing_malformed_or_noncanonical_unresolved_reasons(
    tmp_path: Path,
    reasons: Any,
) -> None:
    bundle = _write_bundle(tmp_path / "candidate")
    source = tmp_path / "input.md"
    source.write_text("alpha", encoding="utf-8")

    def runner(
        text: str,
        **_kwargs: Any,
    ) -> dict[str, Any]:
        return {
            "canonical_text": text,
            "span_resolutions": [],
            "unresolved_span_resolutions": [
                {
                    "source_char_start": 0,
                    "source_char_end": 5,
                    "source_text_span": "alpha",
                    "candidate_scores": {"C-ALPHA": 0.4},
                    "winning_concept_id": None,
                    "rejected_reason_codes": reasons,
                }
            ],
            **_resolver_trace(_kwargs["empirical_weight_override"]),
        }

    with pytest.raises(ValueError, match="reason"):
        resolved_export.export_resolved_sources(
            bundle_path=bundle,
            source_files=[source],
            repo_path=tmp_path / "repo",
            runner=runner,
        )


@pytest.mark.parametrize(
    "field, value",
    [
        ("span_resolutions", None),
        ("span_resolutions", {"not": "a list"}),
        ("unresolved_span_resolutions", None),
        ("unresolved_span_resolutions", {"not": "a list"}),
    ],
)
def test_exporter_rejects_missing_or_malformed_pipeline_span_collection(
    tmp_path: Path,
    field: str,
    value: Any,
) -> None:
    bundle = _write_bundle(tmp_path / "candidate")
    source = tmp_path / "input.md"
    source.write_text("alpha", encoding="utf-8")

    def runner(text: str, **_kwargs: Any) -> dict[str, Any]:
        output = {
            "canonical_text": text,
            "span_resolutions": [],
            "unresolved_span_resolutions": [],
            **_resolver_trace(_kwargs["empirical_weight_override"]),
        }
        if value is None:
            del output[field]
        else:
            output[field] = value
        return output

    with pytest.raises(ValueError, match=rf"{field}.*list"):
        resolved_export.export_resolved_sources(
            bundle_path=bundle,
            source_files=[source],
            repo_path=tmp_path / "repo",
            runner=runner,
        )


def test_exporter_rejects_cross_field_duplicate_span_evidence(
    tmp_path: Path,
) -> None:
    bundle = _write_bundle(tmp_path / "candidate")
    source = tmp_path / "input.md"
    source.write_text("alpha", encoding="utf-8")
    resolved = {
        "source_char_start": 0,
        "source_char_end": 5,
        "source_text_span": "alpha",
        "candidate_scores": {"C-ALPHA": 0.9},
        "winning_concept_id": "C-ALPHA",
        "rejected_reason_codes": [],
    }
    unresolved = {
        **resolved,
        "candidate_scores": {"C-ALPHA": 0.4},
        "winning_concept_id": None,
        "rejected_reason_codes": [
            "below_threshold",
            "candidate_rejected:C-ALPHA",
        ],
    }

    def runner(text: str, **_kwargs: Any) -> dict[str, Any]:
        return {
            "canonical_text": text,
            "span_resolutions": [resolved],
            "unresolved_span_resolutions": [unresolved],
            **_resolver_trace(_kwargs["empirical_weight_override"]),
        }

    with pytest.raises(ValueError, match="resolved/unresolved overlap"):
        resolved_export.export_resolved_sources(
            bundle_path=bundle,
            source_files=[source],
            repo_path=tmp_path / "repo",
            runner=runner,
        )


@pytest.mark.parametrize(
    "field, winning_concept_id",
    [
        ("span_resolutions", None),
        ("unresolved_span_resolutions", "C-ALPHA"),
    ],
)
def test_exporter_rejects_resolution_state_in_wrong_pipeline_field(
    tmp_path: Path,
    field: str,
    winning_concept_id: str | None,
) -> None:
    bundle = _write_bundle(tmp_path / "candidate")
    source = tmp_path / "input.md"
    source.write_text("alpha", encoding="utf-8")
    record = {
        "source_char_start": 0,
        "source_char_end": 5,
        "source_text_span": "alpha",
        "candidate_scores": {"C-ALPHA": 0.4},
        "winning_concept_id": winning_concept_id,
        "rejected_reason_codes": ["below_threshold"],
    }

    def runner(text: str, **_kwargs: Any) -> dict[str, Any]:
        output = {
            "canonical_text": text,
            "span_resolutions": [],
            "unresolved_span_resolutions": [],
            **_resolver_trace(_kwargs["empirical_weight_override"]),
        }
        output[field] = [record]
        return output

    with pytest.raises(ValueError, match="resolution state"):
        resolved_export.export_resolved_sources(
            bundle_path=bundle,
            source_files=[source],
            repo_path=tmp_path / "repo",
            runner=runner,
        )


def test_exporter_paragraph_segmentation_is_deterministic(tmp_path: Path) -> None:
    bundle = _write_bundle(tmp_path / "candidate")
    source = tmp_path / "input.md"
    source.write_bytes(b"alpha\r\nline\r\n\r\nbeta\n\n\nunicode \xf0\x9f\x99\x82")

    first = resolved_export.export_resolved_sources(
        bundle_path=bundle,
        source_files=[source],
        repo_path=tmp_path / "repo",
        runner=RecordingRunner(),
    )
    second = resolved_export.export_resolved_sources(
        bundle_path=bundle,
        source_files=[source],
        repo_path=tmp_path / "repo",
        runner=RecordingRunner(),
    )

    assert resolved_export._canonicalize_resolved_export(
        first,
        allow_test_authority=True,
    ) == resolved_export._canonicalize_resolved_export(
        second,
        allow_test_authority=True,
    )


def test_exporter_maps_canonical_spans_to_exact_source_text(tmp_path: Path) -> None:
    bundle = _write_bundle(tmp_path / "candidate")
    source = tmp_path / "input.md"
    paragraph_text = "  Cafe\u0301  Straße\ncan’t ALPHA alpha  "
    source.write_text(paragraph_text, encoding="utf-8")
    canonical_text = "café strasse can't alpha alpha"
    canonical_surfaces = ["café", "strasse", "can't", "alpha", "alpha"]
    starts = [canonical_text.index(surface) for surface in canonical_surfaces]
    starts[4] = canonical_text.rindex("alpha")
    runner = CanonicalSpanRunner(
        canonical_text,
        [
            (start, start + len(surface))
            for start, surface in zip(starts, canonical_surfaces, strict=True)
        ],
    )

    export = resolved_export.export_resolved_sources(
        bundle_path=bundle,
        source_files=[source],
        repo_path=tmp_path / "repo",
        runner=runner,
    )

    paragraph = export["books"][0]["paragraphs"][0]
    assert paragraph["text"] == paragraph_text
    assert [
        (
            span["span_position"],
            span["span_end"],
            span["surface"],
            paragraph["text"][span["span_position"]:span["span_end"]],
        )
        for span in paragraph["resolved_spans"]
    ] == [
        (2, 7, "Cafe\u0301", "Cafe\u0301"),
        (9, 15, "Straße", "Straße"),
        (16, 21, "can’t", "can’t"),
        (22, 27, "ALPHA", "ALPHA"),
        (28, 33, "alpha", "alpha"),
    ]


def test_exporter_fails_closed_when_canonical_span_splits_expansion(
    tmp_path: Path,
) -> None:
    bundle = _write_bundle(tmp_path / "candidate")
    source = tmp_path / "input.md"
    source.write_text("ß", encoding="utf-8")
    runner = CanonicalSpanRunner("ss", [(0, 1)])

    with pytest.raises(ValueError, match="ambiguous canonical span"):
        resolved_export.export_resolved_sources(
            bundle_path=bundle,
            source_files=[source],
            repo_path=tmp_path / "repo",
            runner=runner,
        )


def test_exporter_real_pipeline_maps_mixed_case_spacing_and_newlines(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle = _write_bundle(tmp_path / "candidate")
    source = tmp_path / "input.md"
    paragraph_text = "  ALPHA   alpha\nALPHA  "
    source.write_text(paragraph_text, encoding="utf-8")
    monkeypatch.setenv("HESPERIA_DICT_A_PATH", "/must/not/load/global-a.jsonl")
    monkeypatch.setenv("HESPERIA_DICT_B_PATH", "/must/not/load/global-b.jsonl")

    export = resolved_export.export_resolved_sources(
        bundle_path=bundle,
        source_files=[source],
        repo_path=REPO,
    )

    paragraph = export["books"][0]["paragraphs"][0]
    assert paragraph["text"] == paragraph_text
    assert [
        (
            span["span_position"],
            span["span_end"],
            span["surface"],
            paragraph["text"][span["span_position"]:span["span_end"]],
        )
        for span in paragraph["resolved_spans"]
    ] == [
        (2, 7, "ALPHA", "ALPHA"),
        (10, 15, "alpha", "alpha"),
        (16, 21, "ALPHA", "ALPHA"),
    ]


@pytest.mark.parametrize("source_bytes", [b"", b"\r\n \t\r\n\n"])
def test_exporter_preserves_empty_source_books(
    tmp_path: Path,
    source_bytes: bytes,
) -> None:
    bundle = _write_bundle(tmp_path / "candidate")
    source = tmp_path / "input.md"
    source.write_bytes(source_bytes)
    runner = RecordingRunner()

    export = resolved_export.export_resolved_sources(
        bundle_path=bundle,
        source_files=[source],
        repo_path=tmp_path / "repo",
        runner=runner,
    )

    assert runner.calls == []
    assert export["books"] == [
        {
            "book_id": _sha256_bytes(b"input.md"),
            "source_path": "input.md",
            "source_sha256": _sha256_bytes(source_bytes),
            "paragraphs": [],
        }
    ]
    resolved_export._validate_resolved_export(
        export,
        allow_test_authority=True,
    )


def test_exporter_recursively_discovers_supported_text_files_from_directory_roots(
    tmp_path: Path,
) -> None:
    bundle = _write_bundle(tmp_path / "candidate")
    corpus = tmp_path / "corpus"
    (corpus / "nested").mkdir(parents=True)
    (corpus / "root.md").write_text("root", encoding="utf-8")
    (corpus / "nested" / "book.txt").write_text("nested", encoding="utf-8")

    export = resolved_export.export_resolved_sources(
        bundle_path=bundle,
        source_files=[corpus],
        repo_path=tmp_path / "repo",
        runner=RecordingRunner(),
    )

    assert [book["source_path"] for book in export["books"]] == [
        "nested/book.txt",
        "root.md",
    ]


def test_exporter_order_is_independent_of_caller_and_filesystem_order(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle = _write_bundle(tmp_path / "candidate")
    first_root = tmp_path / "a"
    second_root = tmp_path / "b"
    first_root.mkdir()
    second_root.mkdir()
    (first_root / "z.md").write_text("zeta", encoding="utf-8")
    (first_root / "a.md").write_text("alpha", encoding="utf-8")
    (second_root / "b.md").write_text("beta", encoding="utf-8")
    real_walk = os.walk

    def reversed_walk(*args: Any, **kwargs: Any) -> Any:
        for directory, directory_names, file_names in real_walk(*args, **kwargs):
            yield directory, list(reversed(directory_names)), list(reversed(file_names))

    monkeypatch.setattr(resolved_export.os, "walk", reversed_walk)
    forward = resolved_export.export_resolved_sources(
        bundle_path=bundle,
        source_files=[first_root, second_root],
        repo_path=tmp_path / "repo",
        runner=RecordingRunner(),
    )
    reverse = resolved_export.export_resolved_sources(
        bundle_path=bundle,
        source_files=[second_root, first_root],
        repo_path=tmp_path / "repo",
        runner=RecordingRunner(),
    )

    assert resolved_export._canonicalize_resolved_export(
        forward,
        allow_test_authority=True,
    ) == resolved_export._canonicalize_resolved_export(
        reverse,
        allow_test_authority=True,
    )
    assert [book["source_path"] for book in forward["books"]] == [
        "a/a.md",
        "a/z.md",
        "b/b.md",
    ]


def test_exporter_deduplicates_duplicate_and_overlapping_roots(
    tmp_path: Path,
) -> None:
    bundle = _write_bundle(tmp_path / "candidate")
    corpus = tmp_path / "corpus"
    nested = corpus / "nested"
    nested.mkdir(parents=True)
    source = nested / "book.md"
    source.write_text("alpha", encoding="utf-8")
    runner = RecordingRunner()

    export = resolved_export.export_resolved_sources(
        bundle_path=bundle,
        source_files=[corpus, nested, source, corpus],
        repo_path=tmp_path / "repo",
        runner=runner,
    )

    assert [book["source_path"] for book in export["books"]] == ["nested/book.md"]
    assert len(runner.calls) == 1


@pytest.mark.parametrize("symlink_kind", ["root", "file", "nested_directory"])
def test_exporter_rejects_symlinked_corpus_inputs(
    tmp_path: Path,
    symlink_kind: str,
) -> None:
    bundle = _write_bundle(tmp_path / "candidate")
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    target = tmp_path / "target"
    target.mkdir()
    (target / "book.md").write_text("alpha", encoding="utf-8")
    if symlink_kind == "root":
        corpus_input = tmp_path / "corpus-link"
        corpus_input.symlink_to(target, target_is_directory=True)
    elif symlink_kind == "file":
        corpus_input = corpus
        (corpus / "book.md").symlink_to(target / "book.md")
    else:
        corpus_input = corpus
        (corpus / "nested").symlink_to(target, target_is_directory=True)

    with pytest.raises(ValueError) as exc_info:
        resolved_export.export_resolved_sources(
            bundle_path=bundle,
            source_files=[corpus_input],
            repo_path=tmp_path / "repo",
            runner=RecordingRunner(),
        )
    assert "must not be a symlink" in str(exc_info.value)


def test_exporter_rejects_symlinked_ancestor_of_corpus_root(
    tmp_path: Path,
) -> None:
    bundle = _write_bundle(tmp_path / "candidate")
    target = tmp_path / "target"
    target.mkdir()
    (target / "book.md").write_text("alpha", encoding="utf-8")
    ancestor = tmp_path / "ancestor-link"
    ancestor.symlink_to(target, target_is_directory=True)

    with pytest.raises(ValueError, match="ancestor.*symlink"):
        resolved_export.export_resolved_sources(
            bundle_path=bundle,
            source_files=[ancestor / "book.md"],
            repo_path=tmp_path / "repo",
            runner=RecordingRunner(),
        )


def test_exporter_rejects_supported_file_identity_replacement_during_traversal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle = _write_bundle(tmp_path / "candidate")
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    source = corpus / "book.md"
    source.write_text("alpha", encoding="utf-8")
    real_walk = os.walk
    replaced = False

    def replacing_walk(*args: Any, **kwargs: Any) -> Any:
        nonlocal replaced
        for item in real_walk(*args, **kwargs):
            yield item
            if not replaced:
                replaced = True
                source.unlink()
                source.write_text("alpha", encoding="utf-8")

    monkeypatch.setattr(resolved_export.os, "walk", replacing_walk)

    with pytest.raises(ValueError, match="identity.*traversal"):
        resolved_export.export_resolved_sources(
            bundle_path=bundle,
            source_files=[corpus],
            repo_path=tmp_path / "repo",
            runner=RecordingRunner(),
        )


def test_exporter_revalidates_sources_before_first_runner_call(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle = _write_bundle(tmp_path / "candidate")
    source = tmp_path / "book.md"
    replacement = tmp_path / "replacement.md"
    source.write_text("alpha", encoding="utf-8")
    replacement.write_text("alpha", encoding="utf-8")
    real_load = resolved_export._load_stable_bundle_generation
    runner = RecordingRunner()

    def replacing_load(bundle_path: Path) -> Any:
        loaded = real_load(bundle_path)
        source.unlink()
        source.symlink_to(replacement)
        return loaded

    monkeypatch.setattr(
        resolved_export,
        "_load_stable_bundle_generation",
        replacing_load,
    )

    with pytest.raises(ValueError, match="symlink|identity"):
        resolved_export.export_resolved_sources(
            bundle_path=bundle,
            source_files=[source],
            repo_path=tmp_path / "repo",
            runner=runner,
        )
    assert runner.calls == []


def test_exporter_propagates_os_walk_errors_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle = _write_bundle(tmp_path / "candidate")
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "book.md").write_text("alpha", encoding="utf-8")

    def failing_walk(*_args: Any, **kwargs: Any) -> Any:
        onerror = kwargs.get("onerror")
        assert onerror is not None
        onerror(PermissionError("walk denied"))
        yield

    monkeypatch.setattr(resolved_export.os, "walk", failing_walk)

    with pytest.raises(ValueError, match="walk denied"):
        resolved_export.export_resolved_sources(
            bundle_path=bundle,
            source_files=[corpus],
            repo_path=tmp_path / "repo",
            runner=RecordingRunner(),
        )


def test_exporter_rejects_unreadable_corpus_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle = _write_bundle(tmp_path / "candidate")
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "book.md").write_text("alpha", encoding="utf-8")
    real_access = os.access

    def denied_access(path: str | Path, mode: int) -> bool:
        if Path(path) == corpus and mode == os.R_OK | os.X_OK:
            return False
        return real_access(path, mode)

    monkeypatch.setattr(resolved_export.os, "access", denied_access)

    with pytest.raises(ValueError, match="readable"):
        resolved_export.export_resolved_sources(
            bundle_path=bundle,
            source_files=[corpus],
            repo_path=tmp_path / "repo",
            runner=RecordingRunner(),
        )


@pytest.mark.parametrize("mutation", ["addition", "removal", "rename"])
def test_exporter_rejects_supported_membership_mutation_by_runner(
    tmp_path: Path,
    mutation: str,
) -> None:
    bundle = _write_bundle(tmp_path / "candidate")
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    source = corpus / "book.md"
    source.write_text("alpha", encoding="utf-8")
    delegate = RecordingRunner()

    def mutating_runner(*args: Any, **kwargs: Any) -> dict[str, Any]:
        output = delegate(*args, **kwargs)
        if mutation == "addition":
            (corpus / "added.md").write_text("added", encoding="utf-8")
        elif mutation == "removal":
            source.unlink()
        else:
            source.rename(corpus / "renamed.md")
        return output

    with pytest.raises(ValueError, match="membership|identity|missing"):
        resolved_export.export_resolved_sources(
            bundle_path=bundle,
            source_files=[corpus],
            repo_path=tmp_path / "repo",
            runner=mutating_runner,
        )


def test_exporter_rejects_directory_identity_replacement_with_same_source_inode(
    tmp_path: Path,
) -> None:
    bundle = _write_bundle(tmp_path / "candidate")
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    source = corpus / "book.md"
    source.write_text("alpha", encoding="utf-8")
    delegate = RecordingRunner()

    def replacing_runner(*args: Any, **kwargs: Any) -> dict[str, Any]:
        output = delegate(*args, **kwargs)
        moved = tmp_path / "moved-corpus"
        corpus.rename(moved)
        corpus.mkdir()
        os.link(moved / "book.md", corpus / "book.md")
        return output

    with pytest.raises(ValueError, match="(root|directory) identity"):
        resolved_export.export_resolved_sources(
            bundle_path=bundle,
            source_files=[corpus],
            repo_path=tmp_path / "repo",
            runner=replacing_runner,
        )


def test_exporter_ignores_unsupported_files_and_rejects_non_utf8_text(
    tmp_path: Path,
) -> None:
    bundle = _write_bundle(tmp_path / "candidate")
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "book.md").write_text("alpha", encoding="utf-8")
    (corpus / "cover.jpg").write_bytes(b"\xff\xfe")

    export = resolved_export.export_resolved_sources(
        bundle_path=bundle,
        source_files=[corpus],
        repo_path=tmp_path / "repo",
        runner=RecordingRunner(),
    )
    assert [book["source_path"] for book in export["books"]] == ["book.md"]

    (corpus / "broken.txt").write_bytes(b"\xff\xfe")
    with pytest.raises(ValueError, match="UTF-8"):
        resolved_export.export_resolved_sources(
            bundle_path=bundle,
            source_files=[corpus],
            repo_path=tmp_path / "repo",
            runner=RecordingRunner(),
        )


def test_exporter_source_paths_preserve_source_root_identity(
    tmp_path: Path,
) -> None:
    bundle = _write_bundle(tmp_path / "candidate")
    first_root = tmp_path / "first"
    second_root = tmp_path / "second"
    (first_root / "chapters").mkdir(parents=True)
    second_root.mkdir()
    (first_root / "chapters" / "book.md").write_text("first", encoding="utf-8")
    (second_root / "book.md").write_text("second", encoding="utf-8")

    single_root = resolved_export.export_resolved_sources(
        bundle_path=bundle,
        source_files=[first_root],
        repo_path=tmp_path / "repo",
        runner=RecordingRunner(),
    )
    sibling_roots = resolved_export.export_resolved_sources(
        bundle_path=bundle,
        source_files=[second_root, first_root],
        repo_path=tmp_path / "repo",
        runner=RecordingRunner(),
    )

    assert [book["source_path"] for book in single_root["books"]] == [
        "chapters/book.md"
    ]
    assert [book["source_path"] for book in sibling_roots["books"]] == [
        "first/chapters/book.md",
        "second/book.md",
    ]


@pytest.mark.parametrize(
    "mutated_name",
    ["manifest.json", "dict_a.jsonl", "dict_b.jsonl", "dict_c.jsonl"],
)
def test_exporter_rejects_bundle_mutation_by_runner_callback(
    tmp_path: Path,
    mutated_name: str,
) -> None:
    bundle = _write_bundle(tmp_path / "candidate")
    source = tmp_path / "input.md"
    source.write_text("alpha", encoding="utf-8")
    delegate = RecordingRunner()

    def mutating_runner(*args: Any, **kwargs: Any) -> dict[str, Any]:
        output = delegate(*args, **kwargs)
        (bundle / mutated_name).write_bytes(b"mutated during resolution\n")
        return output

    with pytest.raises(ValueError, match="bundle.*(changed|mutated|identity)"):
        resolved_export.export_resolved_sources(
            bundle_path=bundle,
            source_files=[source],
            repo_path=tmp_path / "repo",
            runner=mutating_runner,
        )


def test_exporter_rejects_runner_mutation_of_snapshot_artifacts(
    tmp_path: Path,
) -> None:
    bundle = _write_bundle(tmp_path / "candidate")
    source = tmp_path / "input.md"
    source.write_text("alpha", encoding="utf-8")
    delegate = RecordingRunner()

    def mutating_runner(*args: Any, **kwargs: Any) -> dict[str, Any]:
        output = delegate(*args, **kwargs)
        kwargs["dict_a_paths"][0].write_bytes(b"mutated snapshot\n")
        return output

    with pytest.raises(ValueError, match="bundle.*(changed|mutated|identity)"):
        resolved_export.export_resolved_sources(
            bundle_path=bundle,
            source_files=[source],
            repo_path=tmp_path / "repo",
            runner=mutating_runner,
        )


def test_bundle_generation_cannot_mix_old_parse_with_new_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle = _write_bundle(tmp_path / "candidate")
    source = tmp_path / "input.md"
    source.write_text("alpha", encoding="utf-8")
    real_read_bundle = resolved_export._read_bundle
    raced = False

    def racing_read_bundle(bundle_path: Path) -> dict[str, Any]:
        nonlocal raced
        parsed = real_read_bundle(bundle_path)
        if Path(bundle_path) == bundle and not raced:
            raced = True
            manifest_path = bundle / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["provenance"]["checkpoint"] = "new-generation"
            unsigned = {
                key: value for key, value in manifest.items() if key != "bundle_id"
            }
            manifest["bundle_id"] = _sha256_bytes(_canonical_bytes(unsigned))
            manifest_path.write_text(
                json.dumps(
                    manifest,
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
            (bundle / "manifest.json.sha256").write_text(
                f"{_sha256(manifest_path)}  manifest.json\n",
                encoding="ascii",
            )
        return parsed

    monkeypatch.setattr(resolved_export, "_read_bundle", racing_read_bundle)

    with pytest.raises(ValueError, match="bundle.*(generation|changed|identity)"):
        resolved_export.export_resolved_sources(
            bundle_path=bundle,
            source_files=[source],
            repo_path=tmp_path / "repo",
            runner=RecordingRunner(),
        )


@pytest.mark.parametrize("mutation", ["content", "symlink"])
def test_exporter_rejects_source_mutation_during_runner_calls(
    tmp_path: Path,
    mutation: str,
) -> None:
    bundle = _write_bundle(tmp_path / "candidate")
    source = tmp_path / "input.md"
    source.write_text("alpha", encoding="utf-8")
    delegate = RecordingRunner()

    def mutating_runner(*args: Any, **kwargs: Any) -> dict[str, Any]:
        output = delegate(*args, **kwargs)
        if mutation == "content":
            source.write_text("changed", encoding="utf-8")
        else:
            replacement = tmp_path / "replacement.md"
            replacement.write_text("alpha", encoding="utf-8")
            source.unlink()
            source.symlink_to(replacement)
        return output

    with pytest.raises(ValueError, match="source.*(changed|identity|regular|symlink)"):
        resolved_export.export_resolved_sources(
            bundle_path=bundle,
            source_files=[source],
            repo_path=tmp_path / "repo",
            runner=mutating_runner,
        )


def test_min_resolve_score_env_cannot_change_frozen_export(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle = _write_bundle(tmp_path / "candidate")
    source = tmp_path / "input.md"
    source.write_text("alpha", encoding="utf-8")

    monkeypatch.setenv("HESPERIA_DLCR_MIN_RESOLVE_SCORE", "0")
    low_threshold = resolved_export.export_resolved_sources(
        bundle_path=bundle,
        source_files=[source],
        repo_path=REPO,
    )
    monkeypatch.setenv("HESPERIA_DLCR_MIN_RESOLVE_SCORE", "999")
    high_threshold = resolved_export.export_resolved_sources(
        bundle_path=bundle,
        source_files=[source],
        repo_path=REPO,
    )

    assert resolved_export.canonicalize_resolved_export(
        low_threshold
    ) == resolved_export.canonicalize_resolved_export(high_threshold)
    assert low_threshold["provenance"] == high_threshold["provenance"]


def test_effective_configuration_hash_tracks_policy_bytes(
    tmp_path: Path,
) -> None:
    bundle = _write_bundle(tmp_path / "candidate")
    source = tmp_path / "input.md"
    source.write_text("alpha", encoding="utf-8")
    repo = tmp_path / "repo"
    policy = repo / "assets/data/engine_dynamics_v060/dlcr_policy.yaml"
    policy.parent.mkdir(parents=True)
    policy.write_text("cooc_window: 4\n", encoding="utf-8")

    first = resolved_export.export_resolved_sources(
        bundle_path=bundle,
        source_files=[source],
        repo_path=repo,
        runner=RecordingRunner(),
    )
    policy.write_text("cooc_window: 8\n", encoding="utf-8")
    second = resolved_export.export_resolved_sources(
        bundle_path=bundle,
        source_files=[source],
        repo_path=repo,
        runner=RecordingRunner(),
    )

    assert first["provenance"]["resolver_configuration_sha256"] != second[
        "provenance"
    ]["resolver_configuration_sha256"]


def test_exporter_preserves_complete_finite_candidate_score_vector_exactly(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle = _write_bundle(tmp_path / "candidate")
    source = tmp_path / "input.md"
    source.write_text("alpha beta", encoding="utf-8")
    pinned_environment = dict(resolved_export._PINNED_PIPELINE_ENV)
    pinned_environment["HESPERIA_DLCR_MIN_RESOLVE_SCORE"] = "5"
    monkeypatch.setattr(
        resolved_export,
        "_PINNED_PIPELINE_ENV",
        pinned_environment,
    )

    export = resolved_export.export_resolved_sources(
        bundle_path=bundle,
        source_files=[source],
        repo_path=tmp_path / "repo",
        runner=ScoreVectorRunner(),
    )
    expected_scores = [
        {"concept_id": concept_id, "score": score}
        for concept_id, score in sorted(ScoreVectorRunner.candidate_scores.items())
    ]
    score_vectors = [
        export["books"][0]["paragraphs"][0]["resolved_spans"][0][
            "candidate_scores"
        ],
        export["unresolved"][0]["candidate_scores"],
    ]
    assert score_vectors == [expected_scores, expected_scores]

    round_tripped = json.loads(
        resolved_export._canonicalize_resolved_export(
            export,
            allow_test_authority=True,
        )
    )
    round_tripped_vectors = [
        round_tripped["books"][0]["paragraphs"][0]["resolved_spans"][0][
            "candidate_scores"
        ],
        round_tripped["unresolved"][0]["candidate_scores"],
    ]
    assert round_tripped_vectors == score_vectors
    for round_tripped_scores in round_tripped_vectors:
        negative_zero = next(
            candidate["score"]
            for candidate in round_tripped_scores
            if candidate["concept_id"] == "C-NEGATIVE-ZERO"
        )
        assert negative_zero == 0.0


def test_exporter_binds_exact_manifest_bundle_resolver_and_configuration_identity(
    tmp_path: Path,
) -> None:
    bundle = _write_bundle(tmp_path / "candidate")
    source = tmp_path / "input.md"
    source.write_text("alpha", encoding="utf-8")
    manifest_bytes = (bundle / "manifest.json").read_bytes()
    manifest = json.loads(manifest_bytes)
    repo = tmp_path / "repo"

    export = resolved_export.export_resolved_sources(
        bundle_path=bundle,
        source_files=[source],
        repo_path=repo,
        runner=RecordingRunner(),
    )

    expected_configuration_hash = _sha256_bytes(
        _canonical_bytes(
            {
                "manifest_resolver_configuration_sha256": (
                    manifest["provenance"]["resolver"]["configuration_sha256"]
                ),
                "resolver_implementation_sha256": (
                    export["provenance"]["resolver_implementation_sha256"]
                ),
                "pipeline_environment": resolved_export._PINNED_PIPELINE_ENV,
                "empirical_weight_override": (
                    resolved_export.DICT_D_EXPORT_WEIGHT
                ),
                "configuration_files": resolved_export._configuration_file_hashes(
                    repo
                ),
            }
        )
    )
    assert export["provenance"] == {
        "candidate_bundle_id": manifest["bundle_id"],
        "candidate_manifest_sha256": _sha256_bytes(manifest_bytes),
        "corpus_snapshot_sha256": export["provenance"][
            "corpus_snapshot_sha256"
        ],
        "resolver_version": manifest["provenance"]["resolver"]["version"],
        "resolver_implementation_sha256": export["provenance"][
            "resolver_implementation_sha256"
        ],
        "resolver_authority": "private-test-runner",
        "resolver_configuration_sha256": expected_configuration_hash,
        "segmentation_rule": manifest["provenance"]["segmentation_rule"],
        "export_rule": "resolved-corpus-export-v1",
        "dict_d_enabled": False,
        "dict_d_effective_weight": 0.0,
    }


def test_effective_configuration_hash_is_deterministic_and_env_sensitive(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle = _write_bundle(tmp_path / "candidate")
    source = tmp_path / "input.md"
    source.write_text("alpha", encoding="utf-8")
    repo = tmp_path / "repo"

    first = resolved_export.export_resolved_sources(
        bundle_path=bundle,
        source_files=[source],
        repo_path=repo,
        runner=RecordingRunner(),
    )
    repeated = resolved_export.export_resolved_sources(
        bundle_path=bundle,
        source_files=[source],
        repo_path=repo,
        runner=RecordingRunner(),
    )
    changed_environment = dict(resolved_export._PINNED_PIPELINE_ENV)
    changed_environment["HESPERIA_DLCR_MIN_RESOLVE_SCORE"] = "0.625"
    monkeypatch.setattr(
        resolved_export,
        "_PINNED_PIPELINE_ENV",
        changed_environment,
    )
    changed = resolved_export.export_resolved_sources(
        bundle_path=bundle,
        source_files=[source],
        repo_path=repo,
        runner=RecordingRunner(),
    )

    assert first["provenance"]["resolver_configuration_sha256"] == repeated[
        "provenance"
    ]["resolver_configuration_sha256"]
    assert first["provenance"]["resolver_configuration_sha256"] != changed[
        "provenance"
    ]["resolver_configuration_sha256"]


def test_all_pipeline_ambient_env_is_isolated_from_output_and_hash(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle = _write_bundle(tmp_path / "candidate")
    source = tmp_path / "input.md"
    source.write_text("alpha", encoding="utf-8")
    repo = tmp_path / "repo"

    for key in resolved_export._PINNED_PIPELINE_ENV:
        monkeypatch.setenv(key, f"ambient-first-{key}")
    first = resolved_export.export_resolved_sources(
        bundle_path=bundle,
        source_files=[source],
        repo_path=repo,
        runner=RecordingRunner(),
    )
    for key in resolved_export._PINNED_PIPELINE_ENV:
        monkeypatch.setenv(key, f"ambient-second-{key}")
    second = resolved_export.export_resolved_sources(
        bundle_path=bundle,
        source_files=[source],
        repo_path=repo,
        runner=RecordingRunner(),
    )

    assert resolved_export._canonicalize_resolved_export(
        first,
        allow_test_authority=True,
    ) == resolved_export._canonicalize_resolved_export(
        second,
        allow_test_authority=True,
    )


def test_exporter_rejects_runner_mutation_of_effective_environment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle = _write_bundle(tmp_path / "candidate")
    source = tmp_path / "input.md"
    source.write_text("alpha", encoding="utf-8")
    key = "HESPERIA_DLCR_MIN_RESOLVE_SCORE"
    monkeypatch.setenv(key, "ambient-value")
    delegate = RecordingRunner()

    def mutating_runner(*args: Any, **kwargs: Any) -> dict[str, Any]:
        output = delegate(*args, **kwargs)
        os.environ[key] = "mutated-by-callback"
        return output

    with pytest.raises(ValueError, match="callback mutated.*environment"):
        resolved_export.export_resolved_sources(
            bundle_path=bundle,
            source_files=[source],
            repo_path=tmp_path / "repo",
            runner=mutating_runner,
        )
    assert os.environ[key] == "ambient-value"


def test_runner_implementation_identity_is_deterministic_and_bound_to_config(
    tmp_path: Path,
) -> None:
    bundle = _write_bundle(tmp_path / "candidate")
    source = tmp_path / "input.md"
    source.write_text("alpha", encoding="utf-8")
    repo = tmp_path / "repo"

    first = resolved_export.export_resolved_sources(
        bundle_path=bundle,
        source_files=[source],
        repo_path=repo,
        runner=RecordingRunner(),
    )
    repeated = resolved_export.export_resolved_sources(
        bundle_path=bundle,
        source_files=[source],
        repo_path=repo,
        runner=RecordingRunner(),
    )
    alternate = resolved_export.export_resolved_sources(
        bundle_path=bundle,
        source_files=[source],
        repo_path=repo,
        runner=AlternateRecordingRunner(),
    )

    first_identity = first["provenance"]["resolver_implementation_sha256"]
    assert first_identity == repeated["provenance"][
        "resolver_implementation_sha256"
    ]
    assert len(first_identity) == 64
    assert first_identity != alternate["provenance"][
        "resolver_implementation_sha256"
    ]
    assert first["provenance"]["resolver_configuration_sha256"] == repeated[
        "provenance"
    ]["resolver_configuration_sha256"]
    assert first["provenance"]["resolver_configuration_sha256"] != alternate[
        "provenance"
    ]["resolver_configuration_sha256"]


def test_default_runner_identity_tracks_pipeline_source_bytes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_path = Path(resolved_export.run_dlcr_pipeline.__code__.co_filename).resolve()
    real_read_bytes = Path.read_bytes
    before = resolved_export._runner_implementation_sha256(
        resolved_export.run_dlcr_pipeline
    )

    def changed_pipeline_bytes(path: Path) -> bytes:
        content = real_read_bytes(path)
        if path.resolve() == source_path:
            return content + b"\n# simulated resolver revision\n"
        return content

    monkeypatch.setattr(Path, "read_bytes", changed_pipeline_bytes)

    assert resolved_export._runner_implementation_sha256(
        resolved_export.run_dlcr_pipeline
    ) != before


def test_release_resolver_digest_binds_stable_semantic_source_paths() -> None:
    source_hashes = resolved_export._resolver_semantic_source_hashes()

    assert set(source_hashes) >= {
        "core/engine/lexical_concept/pipeline.py",
        "core/resolver/resolver.py",
        "core/resolver/score_rules.py",
        "core/resolver/context.py",
        "core/pipeline/lexical.py",
        "core/lexical/analysis_input.py",
        "core/lexical/normalization.py",
    }
    assert list(source_hashes) == sorted(source_hashes)
    assert all(len(digest) == 64 for digest in source_hashes.values())


@pytest.mark.parametrize(
    "mutated_relative_path",
    [
        "core/engine/lexical_concept/pipeline.py",
        "core/resolver/resolver.py",
        "core/resolver/score_rules.py",
        "core/resolver/context.py",
        "core/pipeline/lexical.py",
        "core/lexical/analysis_input.py",
        "core/lexical/normalization.py",
    ],
)
def test_exporter_revalidates_semantic_source_bytes_after_runner(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutated_relative_path: str,
) -> None:
    bundle = _write_bundle(tmp_path / "candidate")
    source = tmp_path / "input.md"
    source.write_text("alpha", encoding="utf-8")
    delegate = RecordingRunner()
    runner_called = False
    real_read_bytes = Path.read_bytes

    def runner(*args: Any, **kwargs: Any) -> dict[str, Any]:
        nonlocal runner_called
        output = delegate(*args, **kwargs)
        runner_called = True
        return output

    def changed_after_runner(path: Path) -> bytes:
        content = real_read_bytes(path)
        if (
            runner_called
            and path.resolve()
            == (REPO / mutated_relative_path).resolve()
        ):
            return content + b"\n# simulated semantic mutation\n"
        return content

    monkeypatch.setattr(Path, "read_bytes", changed_after_runner)

    with pytest.raises(ValueError, match="semantic source.*changed"):
        resolved_export._export_resolved_sources_for_test(
            bundle_path=bundle,
            source_files=[source],
            repo_path=tmp_path / "repo",
            runner=runner,
        )


def test_exporter_rejects_callback_code_identity_mutation(
    tmp_path: Path,
) -> None:
    bundle = _write_bundle(tmp_path / "candidate")
    source = tmp_path / "input.md"
    source.write_text("alpha", encoding="utf-8")
    original_code = CodeMutatingRunner.__call__.__code__

    try:
        with pytest.raises(ValueError, match="runner implementation changed"):
            resolved_export.export_resolved_sources(
                bundle_path=bundle,
                source_files=[source],
                repo_path=tmp_path / "repo",
                runner=CodeMutatingRunner(),
            )
    finally:
        CodeMutatingRunner.__call__.__code__ = original_code


def test_cli_writes_canonical_export_for_supplied_source_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle = tmp_path / "bundle"
    first = tmp_path / "first.md"
    second = tmp_path / "second.md"
    output = tmp_path / "resolved.json"
    calls: list[dict[str, Any]] = []

    def fake_export(**kwargs: Any) -> dict[str, Any]:
        calls.append(kwargs)
        return _valid_export()

    monkeypatch.setattr(
        resolved_export,
        "export_resolved_sources",
        fake_export,
        raising=False,
    )

    assert (
        resolved_export.main(
            [
                "--bundle",
                str(bundle),
                "--corpus",
                str(first),
                str(second),
                "--output",
                str(output),
            ]
        )
        == 0
    )
    assert calls == [
        {
            "bundle_path": bundle,
            "source_files": [first, second],
        }
    ]
    assert output.read_bytes() == resolved_export.canonicalize_resolved_export(
        _valid_export()
    )


@pytest.mark.parametrize("destination_kind", ["file", "directory", "symlink"])
def test_cli_refuses_existing_or_indirect_destination(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    destination_kind: str,
) -> None:
    output = tmp_path / "resolved.json"
    protected = tmp_path / "protected.json"
    protected.write_text("protected", encoding="utf-8")
    if destination_kind == "file":
        output.write_text("existing", encoding="utf-8")
    elif destination_kind == "directory":
        output.mkdir()
    else:
        output.symlink_to(protected)
    monkeypatch.setattr(
        resolved_export,
        "export_resolved_sources",
        lambda **_kwargs: _valid_export(),
    )

    with pytest.raises(ValueError, match="output.*(exist|regular|symlink|destination)"):
        resolved_export.main(
            [
                "--bundle",
                str(tmp_path / "bundle"),
                "--corpus",
                str(tmp_path / "input.md"),
                "--output",
                str(output),
            ]
        )

    assert protected.read_text(encoding="utf-8") == "protected"


def test_cli_fsyncs_and_atomically_installs_new_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "resolved.json"
    fsynced: list[int] = []
    replacements: list[tuple[Path, Path]] = []
    real_replace = os.replace
    monkeypatch.setattr(
        resolved_export,
        "export_resolved_sources",
        lambda **_kwargs: _valid_export(),
    )
    monkeypatch.setattr(resolved_export.os, "fsync", lambda fd: fsynced.append(fd))

    def recording_replace(source: str | Path, destination: str | Path) -> None:
        source_path = Path(source)
        destination_path = Path(destination)
        assert source_path.parent == output.parent
        assert source_path.is_file()
        replacements.append((source_path, destination_path))
        real_replace(source_path, destination_path)

    monkeypatch.setattr(resolved_export.os, "replace", recording_replace)

    assert (
        resolved_export.main(
            [
                "--bundle",
                str(tmp_path / "bundle"),
                "--corpus",
                str(tmp_path / "input.md"),
                "--output",
                str(output),
            ]
        )
        == 0
    )

    assert fsynced
    assert len(replacements) == 1
    assert replacements[0][1] == output
    assert output.read_bytes() == resolved_export.canonicalize_resolved_export(
        _valid_export()
    )


def test_cli_cleans_destination_temp_when_atomic_install_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "resolved.json"
    monkeypatch.setattr(
        resolved_export,
        "export_resolved_sources",
        lambda **_kwargs: _valid_export(),
    )
    monkeypatch.setattr(
        resolved_export.os,
        "replace",
        lambda *_args: (_ for _ in ()).throw(OSError("replace failed")),
    )

    with pytest.raises(OSError, match="replace failed"):
        resolved_export.main(
            [
                "--bundle",
                str(tmp_path / "bundle"),
                "--corpus",
                str(tmp_path / "input.md"),
                "--output",
                str(output),
            ]
        )

    assert not output.exists()
    assert list(tmp_path.glob(f".{output.name}.*.tmp")) == []


def test_mathematically_equal_scores_have_identical_canonical_bytes() -> None:
    integer_score = _valid_export()
    float_score = _valid_export()
    integer_score["books"][0]["paragraphs"][0]["resolved_spans"][0][
        "candidate_scores"
    ][0]["score"] = 1
    integer_score["provenance"]["dict_d_effective_weight"] = 0
    negative_zero_score = _valid_export()
    positive_zero_score = _valid_export()
    negative_zero_score["books"][0]["paragraphs"][0]["resolved_spans"][0][
        "candidate_scores"
    ][1]["score"] = -0.0
    positive_zero_score["books"][0]["paragraphs"][0]["resolved_spans"][0][
        "candidate_scores"
    ][1]["score"] = 0.0

    integer_bytes = resolved_export.canonicalize_resolved_export(integer_score)
    float_bytes = resolved_export.canonicalize_resolved_export(float_score)
    negative_zero_bytes = resolved_export.canonicalize_resolved_export(
        negative_zero_score
    )
    positive_zero_bytes = resolved_export.canonicalize_resolved_export(
        positive_zero_score
    )

    assert integer_bytes == float_bytes
    assert negative_zero_bytes == positive_zero_bytes


def test_unresolved_records_reference_books_in_declared_order() -> None:
    payload = _valid_export()
    text = "delta"
    paragraph_id = _paragraph_id(SHA_A, 0, text)
    payload["books"].append(
        {
            "book_id": "book-002",
            "source_path": "002-delta.md",
            "source_sha256": SHA_A,
            "paragraphs": [
                {
                    "paragraph_id": paragraph_id,
                    "source_ordinal": 0,
                    "text": text,
                    "resolved_spans": [],
                }
            ],
        }
    )
    payload["unresolved"].append(
        {
            "book_id": "book-002",
            "paragraph_id": paragraph_id,
            "span_position": 0,
            "span_end": 5,
            "surface": text,
            "reason_codes": ["no_candidates"],
            "candidate_scores": [],
        }
    )

    resolved_export.validate_resolved_export(payload)


@pytest.mark.parametrize(
    "mutation, message",
    [
        (
            lambda value: value["provenance"].__setitem__(
                "resolver_configuration_sha256", "not-a-hash"
            ),
            "resolver_configuration_sha256",
        ),
        (
            lambda value: value["provenance"].__setitem__(
                "resolver_implementation_sha256", "not-a-hash"
            ),
            "resolver_implementation_sha256",
        ),
        (
            lambda value: value["provenance"].__setitem__(
                "dict_d_enabled", True
            ),
            "dict_d_enabled",
        ),
        (
            lambda value: value["provenance"].__setitem__(
                "dict_d_effective_weight", 0.01
            ),
            "dict_d_effective_weight",
        ),
        (
            lambda value: value["provenance"].__setitem__(
                "dict_d_effective_weight", float("nan")
            ),
            "dict_d_effective_weight",
        ),
        (
            lambda value: value["books"][0].__setitem__(
                "source_path", "../escape.md"
            ),
            "source_path",
        ),
        (
            lambda value: value["books"][0]["paragraphs"][0].__setitem__(
                "paragraph_id", SHA_A
            ),
            "paragraph_id",
        ),
        (
            lambda value: value["books"][0]["paragraphs"][0][
                "resolved_spans"
            ][0]["candidate_scores"][0].__setitem__("score", float("inf")),
            "score",
        ),
        (
            lambda value: value["books"][0]["paragraphs"][0][
                "resolved_spans"
            ][0].__setitem__("span_end", 50),
            "span",
        ),
        (
            lambda value: value["unresolved"][0].__setitem__(
                "paragraph_id", SHA_A
            ),
            "paragraph_id",
        ),
        (
            lambda value: value["unresolved"][0].__setitem__(
                "reason_codes", []
            ),
            "reason_codes",
        ),
    ],
)
def test_malformed_or_nonfinite_export_fails_closed(
    mutation: Any, message: str
) -> None:
    payload = _valid_export()
    mutation(payload)

    with pytest.raises(ValueError, match=message):
        resolved_export.validate_resolved_export(payload)


@pytest.mark.parametrize(
    "candidate_scores, reason_codes",
    [
        ([], ["unknown_reason"]),
        ([{"concept_id": "C-GAMMA", "score": 0.4}], ["no_candidates"]),
        ([{"concept_id": "C-GAMMA", "score": 0.5}], ["below_threshold"]),
        (
            [{"concept_id": "C-GAMMA", "score": 0.4}],
            ["candidate_rejected:C-GAMMA"],
        ),
        (
            [{"concept_id": "C-GAMMA", "score": 0.4}],
            ["below_threshold", "candidate_rejected:C-GHOST"],
        ),
        ([], ["candidate_rejected:C-GAMMA", "no_candidates"]),
    ],
)
def test_unresolved_reason_codes_must_match_scores_and_decision_state(
    candidate_scores: list[dict[str, Any]],
    reason_codes: list[str],
) -> None:
    payload = _valid_export()
    payload["unresolved"][0]["candidate_scores"] = candidate_scores
    payload["unresolved"][0]["reason_codes"] = reason_codes

    with pytest.raises(ValueError, match="reason_codes"):
        resolved_export.validate_resolved_export(payload)


@pytest.mark.parametrize(
    "source_path",
    [
        "folder//book.md",
        "folder/./book.md",
        "folder/",
    ],
)
def test_noncanonical_source_path_aliases_fail_closed(source_path: str) -> None:
    payload = _valid_export()
    payload["books"][0]["source_path"] = source_path

    with pytest.raises(ValueError, match="source_path"):
        resolved_export.validate_resolved_export(payload)


def test_resolved_and_unresolved_same_paragraph_span_fails_closed() -> None:
    payload = _valid_export()
    first_paragraph = payload["books"][0]["paragraphs"][0]
    payload["unresolved"].insert(
        0,
        {
            "book_id": "book-001",
            "paragraph_id": first_paragraph["paragraph_id"],
            "span_position": 0,
            "span_end": 5,
            "surface": "alpha",
            "reason_codes": ["candidate_rejected:C-0001"],
            "candidate_scores": [
                {"concept_id": "C-0001", "score": 1.0},
            ],
        },
    )

    with pytest.raises(ValueError, match="resolved/unresolved overlap"):
        resolved_export.validate_resolved_export(payload)


def test_duplicate_candidate_and_span_records_fail_closed() -> None:
    duplicate_candidate = _valid_export()
    scores = duplicate_candidate["books"][0]["paragraphs"][0][
        "resolved_spans"
    ][0]["candidate_scores"]
    scores.append(deepcopy(scores[0]))
    with pytest.raises(ValueError, match="duplicate candidate"):
        resolved_export.validate_resolved_export(duplicate_candidate)

    duplicate_span = _valid_export()
    spans = duplicate_span["books"][0]["paragraphs"][0]["resolved_spans"]
    spans.append(deepcopy(spans[0]))
    with pytest.raises(ValueError, match="duplicate resolved span"):
        resolved_export.validate_resolved_export(duplicate_span)


@pytest.mark.parametrize(
    "mutation, message",
    [
        (
            lambda value: value["books"].insert(
                0,
                {
                    "book_id": "book-002",
                    "source_path": "002-zeta.md",
                    "source_sha256": SHA_A,
                    "paragraphs": [],
                },
            ),
            "source_path order",
        ),
        (
            lambda value: value["books"][0]["paragraphs"].reverse(),
            "source_ordinal order",
        ),
        (
            lambda value: value["books"][0]["paragraphs"][0][
                "resolved_spans"
            ].reverse(),
            "resolved span order",
        ),
        (
            lambda value: value["unresolved"].insert(
                0,
                {
                    **deepcopy(value["unresolved"][0]),
                    "span_position": 1,
                    "span_end": 2,
                    "surface": "a",
                },
            ),
            "unresolved order",
        ),
    ],
)
def test_out_of_order_export_fails_closed(
    mutation: Any, message: str
) -> None:
    payload = _valid_export()
    mutation(payload)

    with pytest.raises(ValueError, match=message):
        resolved_export.validate_resolved_export(payload)


def test_duplicate_book_paragraph_and_unresolved_identities_fail_closed() -> None:
    duplicate_book = _valid_export()
    duplicate_book["books"].append(deepcopy(duplicate_book["books"][0]))
    with pytest.raises(ValueError, match="duplicate book"):
        resolved_export.validate_resolved_export(duplicate_book)

    duplicate_paragraph = _valid_export()
    paragraphs = duplicate_paragraph["books"][0]["paragraphs"]
    duplicate = deepcopy(paragraphs[1])
    duplicate["source_ordinal"] = 0
    duplicate["paragraph_id"] = paragraphs[0]["paragraph_id"]
    paragraphs.append(duplicate)
    with pytest.raises(ValueError, match="duplicate paragraph"):
        resolved_export.validate_resolved_export(duplicate_paragraph)

    duplicate_unresolved = _valid_export()
    duplicate_unresolved["unresolved"].append(
        deepcopy(duplicate_unresolved["unresolved"][0])
    )
    with pytest.raises(ValueError, match="duplicate unresolved"):
        resolved_export.validate_resolved_export(duplicate_unresolved)


def test_unknown_or_missing_fields_fail_closed() -> None:
    unknown = _valid_export()
    unknown["unexpected"] = True
    with pytest.raises(ValueError, match="fields"):
        resolved_export.validate_resolved_export(unknown)

    missing = _valid_export()
    del missing["provenance"]["candidate_bundle_id"]
    with pytest.raises(ValueError, match="provenance fields"):
        resolved_export.validate_resolved_export(missing)
