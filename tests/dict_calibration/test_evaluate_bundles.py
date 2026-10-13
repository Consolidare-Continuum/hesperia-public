# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from tools.dict_calibration import evaluate


Runner = Callable[..., dict[str, Any]]
REPO = Path(__file__).resolve().parents[2]


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


def _dict_a_row(
    entry_id: str,
    normalized_form: str,
    candidate_concept_ids: list[str],
    *,
    match_type: str = "exact",
) -> dict[str, Any]:
    return {
        "entry_id": entry_id,
        "normalized_form": normalized_form,
        "match_type": match_type,
        "candidate_concept_ids": candidate_concept_ids,
    }


def _dict_b_row(
    concept_id: str,
    related_concept_ids: list[str],
    *,
    hex_anchor: str | None = None,
    area_id: str = "A00",
    family_id: str = "F00",
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "concept_id": concept_id,
        "related_concept_ids": related_concept_ids,
    }
    if hex_anchor is not None:
        row["hex_anchor"] = hex_anchor
    else:
        row["area_ids"] = [area_id]
        row["family_ids"] = [family_id]
    return row


def _rewrite_manifest(
    bundle_dir: Path,
    mutate: Callable[[dict[str, Any]], None],
) -> None:
    manifest_path = bundle_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    mutate(manifest)
    payload = {key: value for key, value in manifest.items() if key != "bundle_id"}
    manifest["bundle_id"] = _sha256_bytes(_canonical_bytes(payload))
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _write_sidecar(manifest_path)


def _write_bundle(
    bundle_dir: Path,
    *,
    dict_a_rows: list[dict[str, Any]],
    dict_b_rows: list[dict[str, Any]],
    manifest_version: str = "v2",
) -> Path:
    bundle_dir.mkdir(parents=True)
    dict_a_path = bundle_dir / "dict_a.jsonl"
    dict_b_path = bundle_dir / "dict_b.jsonl"
    _write_jsonl(dict_a_path, dict_a_rows)
    _write_jsonl(dict_b_path, dict_b_rows)
    _write_sidecar(dict_a_path)
    _write_sidecar(dict_b_path)

    corpus_dir = bundle_dir / "evidence" / "corpus"
    corpus_dir.mkdir(parents=True)
    corpus_source = corpus_dir / "sample.txt"
    corpus_source.write_text("alpha beta\n\ngamma\n", encoding="utf-8")
    artifacts: dict[str, dict[str, Any]] = {
        "dict_a_matcher": {
            "path": "dict_a.jsonl",
            "sha256": _sha256(dict_a_path),
            "status": "matcher_ready",
        },
        "dict_b_canonical": {
            "path": "dict_b.jsonl",
            "sha256": _sha256(dict_b_path),
            "status": "canonical",
        },
    }
    generation_id = "5" * 64
    ledger_sha256 = "6" * 64
    if manifest_version == "v2":
        concept_id = str(dict_b_rows[0]["concept_id"])
        normalized = str(dict_a_rows[0].get("normalized_form", "fixture"))
        extra_rows = {
            "dict_b_proposal_evidence": (
                "evidence/dict_b_proposals.jsonl",
                "proposal_evidence",
                [
                    {
                        "proposal_id": "7" * 64,
                        "outcome": "anchored",
                        "proposed_concept_id": "proposal-fixture",
                        "anchor": concept_id,
                        "bind_score": 1.0,
                        "bind_reason": "fixture",
                        "source_ordinal": 0,
                    }
                ],
            ),
            "dict_c_source": (
                "evidence/dict_c_source.jsonl",
                "source_evidence",
                [
                    {
                        "link_id": "8" * 64,
                        "lexical": normalized,
                        "concept_id": concept_id,
                        "match_type": "exact",
                        "priority": 0.875,
                        "source_ordinal": 0,
                    }
                ],
            ),
            "dict_c_intermediate": (
                "evidence/dict_c_intermediate.jsonl",
                "intermediate_evidence",
                [
                    {
                        "normalized_form": normalized,
                        "candidate_concept_ids": [concept_id],
                        "priority": 0.875,
                        "source_link_ids": ["8" * 64],
                    }
                ],
            ),
            "dict_c_runtime_conversion": (
                "dict_c.jsonl",
                "matcher_ready",
                [
                    {
                        "normalized_form": normalized,
                        "candidate_concept_ids": [concept_id],
                        "priority": 0.875,
                    }
                ],
            ),
        }
        for role, (relative, status, rows) in extra_rows.items():
            path = bundle_dir / relative
            _write_jsonl(path, rows)
            _write_sidecar(path)
            artifacts[role] = {
                "path": relative,
                "sha256": _sha256(path),
                "status": status,
                "row_count": len(rows),
            }
        edges = sorted(
            {
                tuple(sorted((str(row["concept_id"]), str(target))))
                for row in dict_b_rows
                for target in row["related_concept_ids"]
            }
        )
        edge_path = bundle_dir / "evidence/dict_b_authored_edges.jsonl"
        _write_jsonl(
            edge_path,
            [{"source": source, "target": target} for source, target in edges],
        )
        _write_sidecar(edge_path)
        artifacts["dict_b_authored_edge_provenance"] = {
            "path": "evidence/dict_b_authored_edges.jsonl",
            "sha256": _sha256(edge_path),
            "status": "authored_edge_provenance",
            "row_count": len(edges),
            "evidence_status": "present" if edges else "truthful_zero",
        }
        json_artifacts = {
            "generation_ledger": (
                "evidence/generation_ledger.json",
                "generation_evidence",
                {"schema": "fixture"},
            ),
            "evaluation_metrics": (
                "metrics.json",
                "evaluation_evidence",
                {"schema": "fixture"},
            ),
        }
        for role, (relative, status, value) in json_artifacts.items():
            path = bundle_dir / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(value, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            _write_sidecar(path)
            artifacts[role] = {
                "path": relative,
                "sha256": _sha256(path),
                "status": status,
                "row_count": 1,
            }
        for role in ("dict_a_matcher", "dict_b_canonical"):
            artifacts[role]["row_count"] = (
                len(dict_a_rows) if role == "dict_a_matcher" else len(dict_b_rows)
            )
    manifest_payload = {
        "schema_version": (
            "hesperia.dict_calibration.freeze_manifest.v2"
            if manifest_version == "v2"
            else "hesperia.dict_calibration.freeze_manifest.v1"
        ),
        "state": "candidate",
        "supersedes": None,
        "artifacts": artifacts,
        "provenance": {
            "corpus": {
                "path": corpus_dir.as_posix(),
                "source_hashes": {"sample.txt": _sha256(corpus_source)},
            },
            "model": "gpt-5-mini-2025-08-07",
            "prompt_sha256": "3" * 64,
            "checkpoint": "core-d2-w1-checkpoint-020",
            "resolver": {
                "version": "core-lexical-resolver-v1",
                "configuration_sha256": "4" * 64,
            },
            "segmentation_rule": "frozen-paragraph-segmentation-v1",
            "statistical_rule": "paragraph-cooccurrence-npmi-g2-v1",
            "builder_revision": "core-d2-evaluation-fixture-r1",
            **(
                {
                    "generation_id": generation_id,
                    "generation_ledger_sha256": ledger_sha256,
                }
                if manifest_version == "v2"
                else {}
            ),
        },
        **(
            {
                "generation": {
                    "generation_id": generation_id,
                    "ledger_sha256": ledger_sha256,
                }
            }
            if manifest_version == "v2"
            else {}
        ),
    }
    manifest = {
        **manifest_payload,
        "bundle_id": _sha256_bytes(_canonical_bytes(manifest_payload)),
    }
    manifest_path = bundle_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _write_sidecar(manifest_path)
    return bundle_dir


@pytest.fixture()
def bundles(tmp_path: Path) -> tuple[Path, Path]:
    baseline = _write_bundle(
        tmp_path / "baseline",
        dict_a_rows=[
            _dict_a_row("A-BASE-001", "alpha", ["C-ALPHA"]),
            _dict_a_row("A-BASE-002", "gamma", ["C-GAMMA"]),
        ],
        dict_b_rows=[
            _dict_b_row(
                "C-ALPHA",
                ["C-GAMMA"],
                hex_anchor="HX-0001",
            ),
            _dict_b_row(
                "C-GAMMA",
                [],
                area_id="A00",
                family_id="F02",
            ),
        ],
        manifest_version="v1",
    )
    candidate = _write_bundle(
        tmp_path / "candidate",
        dict_a_rows=[
            _dict_a_row("A-CAND-001", "alpha", ["C-ALPHA"]),
            _dict_a_row("A-CAND-002", "beta", ["C-BETA"], match_type="phrase"),
            _dict_a_row("A-CAND-003", "gamma", ["C-GAMMA"]),
        ],
        dict_b_rows=[
            _dict_b_row(
                "C-ALPHA",
                ["C-BETA", "C-GAMMA"],
                hex_anchor="HX-0101",
            ),
            _dict_b_row(
                "C-BETA",
                ["C-ALPHA"],
                area_id="A01",
                family_id="F03",
            ),
            _dict_b_row(
                "C-GAMMA",
                [],
                hex_anchor="HX-0103",
            ),
        ],
    )
    return baseline, candidate


class DeterministicRunner:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def __call__(
        self,
        text: str,
        *,
        repo_root: Path,
        dict_a_paths: list[Path],
        dict_b_paths: list[Path],
        anchors_path: Path | None = None,
        mode: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        assert not kwargs
        side = dict_a_paths[0].parent.name
        anchors = (
            json.loads(anchors_path.read_text(encoding="utf-8"))
            if anchors_path is not None
            else None
        )
        self.calls.append(
            {
                "text": text,
                "side": side,
                "repo_root": repo_root,
                "dict_a_paths": dict_a_paths,
                "dict_b_paths": dict_b_paths,
                "anchors_path": anchors_path,
                "anchors": anchors,
                "anchors_existed_during_call": (
                    anchors_path is not None and anchors_path.is_file()
                ),
                "mode": mode,
            }
        )
        if text == "alpha beta" and side == "baseline":
            return {
                "canonical_text": text,
                "lexical_hits_accepted": 1,
                "lexical_hits_rejected": 1,
                "concept_weights": {"C-ALPHA": 1.0},
                "family_activation": {"F-ONE": 1.0},
                "span_resolutions": [
                    {
                        "source_char_start": 0,
                        "source_char_end": 5,
                        "source_text_span": "alpha",
                        "candidate_concepts": ["C-ALPHA"],
                        "winning_concept_id": "C-ALPHA",
                    }
                ],
            }
        if text == "alpha beta":
            return {
                "canonical_text": text,
                "lexical_hits_accepted": 2,
                "lexical_hits_rejected": 0,
                "concept_weights": {"C-BETA": 1.0, "C-ALPHA": 1.0},
                "family_activation": {"F-TWO": 1.0, "F-ONE": 1.0},
                "span_resolutions": [
                    {
                        "source_char_start": 6,
                        "source_char_end": 10,
                        "source_text_span": "beta",
                        "candidate_concepts": ["C-BETA"],
                        "winning_concept_id": "C-BETA",
                    },
                    {
                        "source_char_start": 0,
                        "source_char_end": 5,
                        "source_text_span": "alpha",
                        "candidate_concepts": ["C-ALPHA"],
                        "winning_concept_id": "C-ALPHA",
                    },
                ],
            }
        if side == "baseline":
            return {
                "canonical_text": text,
                "lexical_hits_accepted": 1,
                "lexical_hits_rejected": 0,
                "concept_weights": {"C-GAMMA": 3.0},
                "family_activation": {"F-TWO": 3.0},
                "span_resolutions": [
                    {
                        "source_char_start": 0,
                        "source_char_end": len(text),
                        "source_text_span": text,
                        "candidate_concepts": ["C-GAMMA"],
                        "winning_concept_id": "C-GAMMA",
                    }
                ],
            }
        return {
            "canonical_text": text,
            "lexical_hits_accepted": 1,
            "lexical_hits_rejected": 1,
            "concept_weights": {"C-GAMMA": 1.0},
            "family_activation": {"F-TWO": 1.0},
            "span_resolutions": [
                {
                    "source_char_start": 0,
                    "source_char_end": len(text),
                    "source_text_span": text,
                    "candidate_concepts": ["C-GAMMA"],
                    "winning_concept_id": "C-GAMMA",
                }
            ],
        }


def _evaluate(
    baseline: Path,
    candidate: Path,
    runner: Runner,
    *,
    samples: list[str] | None = None,
    repo_path: Path | None = None,
) -> dict[str, Any]:
    return evaluate.evaluate_bundle_comparison(
        baseline_bundle=baseline,
        candidate_bundle=candidate,
        texts=["alpha beta", "gamma"] if samples is None else samples,
        repo_path=repo_path or baseline.parent / "explicit-repo",
        mode="core",
        runner=runner,
    )


def test_comparison_uses_each_manifest_pinned_bundle_without_global_dicts(
    bundles: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    baseline, candidate = bundles
    runner = DeterministicRunner()
    explicit_repo = baseline.parent / "repo-root"
    monkeypatch.setenv("HESPERIA_DICT_A_PATH", "/must/not/be/read/dict-a.jsonl")
    monkeypatch.setenv("HESPERIA_DICT_B_PATH", "/must/not/be/read/dict-b.jsonl")

    report = _evaluate(
        baseline,
        candidate,
        runner,
        repo_path=explicit_repo,
    )

    assert [(call["text"], call["side"]) for call in runner.calls] == [
        ("alpha beta", "baseline"),
        ("alpha beta", "candidate"),
        ("gamma", "baseline"),
        ("gamma", "candidate"),
    ]
    for call in runner.calls:
        bundle = baseline if call["side"] == "baseline" else candidate
        assert call["repo_root"] == explicit_repo
        assert call["dict_a_paths"] == [bundle / "dict_a.jsonl"]
        assert call["dict_b_paths"] == [bundle / "dict_b.jsonl"]
        dict_b_ids = {
            json.loads(line)["concept_id"]
            for line in (bundle / "dict_b.jsonl").read_text(encoding="utf-8").splitlines()
        }
        assert call["anchors_existed_during_call"] is True
        assert call["anchors_path"] is not None
        assert call["anchors_path"] != (
            explicit_repo
            / "assets"
            / "data"
            / "engine_dynamics_v060"
            / "anchors"
            / "concept_hex_anchors.json"
        )
        assert call["anchors_path"] != (
            explicit_repo
            / "assets"
            / "data"
            / "engine_dynamics_v060"
            / "anchors"
            / "concept_hex_anchors_tfp.json"
        )
        assert set(call["anchors"]) == dict_b_ids
        assert call["mode"] == "core"
    assert runner.calls[0]["anchors"] == {
        "C-ALPHA": "HX-0001",
        "C-GAMMA": "HX-0003",
    }
    assert runner.calls[1]["anchors"] == {
        "C-ALPHA": "HX-0101",
        "C-BETA": "HX-0028",
        "C-GAMMA": "HX-0103",
    }
    assert all(
        not call["anchors_path"].exists()
        for call in runner.calls
        if call["anchors_path"] is not None
    )
    assert report["baseline"]["bundle_id"] == json.loads(
        (baseline / "manifest.json").read_text(encoding="utf-8")
    )["bundle_id"]
    assert report["candidate"]["bundle_id"] == json.loads(
        (candidate / "manifest.json").read_text(encoding="utf-8")
    )["bundle_id"]


def test_comparison_allows_v1_baseline_but_requires_v2_candidate(
    tmp_path: Path,
) -> None:
    rows_a = [_dict_a_row("A-1", "alpha", ["C-1"])]
    rows_b = [_dict_b_row("C-1", [], hex_anchor="HX-0001")]
    baseline = _write_bundle(
        tmp_path / "baseline",
        dict_a_rows=rows_a,
        dict_b_rows=rows_b,
        manifest_version="v1",
    )
    candidate = _write_bundle(
        tmp_path / "candidate",
        dict_a_rows=rows_a,
        dict_b_rows=rows_b,
        manifest_version="v1",
    )

    with pytest.raises(ValueError, match="candidate manifest-v2"):
        _evaluate(
            baseline,
            candidate,
            DeterministicRunner(),
            samples=["alpha"],
        )


def test_comparison_fails_closed_on_manifest_bytes_hashes_and_paths(
    tmp_path: Path,
) -> None:
    def valid_pair(case: str) -> tuple[Path, Path]:
        baseline = _write_bundle(
            tmp_path / case / "baseline",
            dict_a_rows=[_dict_a_row("A-BASE-1", "alpha", ["C-1"])],
            dict_b_rows=[_dict_b_row("C-1", [], hex_anchor="HX-0001")],
        )
        candidate = _write_bundle(
            tmp_path / case / "candidate",
            dict_a_rows=[_dict_a_row("A-CAND-1", "alpha", ["C-1"])],
            dict_b_rows=[_dict_b_row("C-1", [], hex_anchor="HX-0001")],
        )
        return baseline, candidate

    baseline, candidate = valid_pair("artifact-hash")
    (candidate / "dict_a.jsonl").write_text(
        '{"normalized_form":"changed","candidate_concept_ids":["C-1"]}\n',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="dict_a.*(hash|digest|bytes)"):
        _evaluate(baseline, candidate, DeterministicRunner(), samples=["alpha"])

    baseline, candidate = valid_pair("manifest-hash")
    manifest = json.loads((candidate / "manifest.json").read_text(encoding="utf-8"))
    manifest["state"] = "release_candidate"
    (candidate / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="manifest.*(hash|digest|bytes|bundle_id)"):
        _evaluate(baseline, candidate, DeterministicRunner(), samples=["alpha"])

    baseline, candidate = valid_pair("unsafe-path")
    manifest_path = candidate / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["artifacts"]["dict_a_matcher"]["path"] = "../dict_a.jsonl"
    payload = {key: value for key, value in manifest.items() if key != "bundle_id"}
    manifest["bundle_id"] = _sha256_bytes(_canonical_bytes(payload))
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _write_sidecar(manifest_path)
    with pytest.raises(ValueError, match="dict_a.*(path|unsafe|bundle)"):
        _evaluate(baseline, candidate, DeterministicRunner(), samples=["alpha"])


@pytest.mark.parametrize(
    "case",
    [
        "wrong-schema-version",
        "quarantined-state",
        "mock-provenance",
        "quarantine-marker",
        "release-ineligible-marker",
        "missing-model",
        "missing-corpus-source-hashes",
        "wrong-dict-a-status",
        "wrong-dict-b-status",
    ],
)
def test_comparison_rejects_non_frozen_or_ineligible_manifests(
    tmp_path: Path,
    case: str,
) -> None:
    baseline = _write_bundle(
        tmp_path / case / "baseline",
        dict_a_rows=[_dict_a_row("A-BASE-1", "alpha", ["C-1"])],
        dict_b_rows=[_dict_b_row("C-1", [], hex_anchor="HX-0001")],
    )
    candidate = _write_bundle(
        tmp_path / case / "candidate",
        dict_a_rows=[_dict_a_row("A-CAND-1", "alpha", ["C-1"])],
        dict_b_rows=[_dict_b_row("C-1", [], hex_anchor="HX-0001")],
    )

    def mutate(manifest: dict[str, Any]) -> None:
        if case == "wrong-schema-version":
            manifest["schema_version"] = "hesperia.dict_calibration.unknown.v999"
        elif case == "quarantined-state":
            manifest["state"] = "quarantined"
        elif case == "mock-provenance":
            manifest["provenance"]["model"] = "mock"
        elif case == "quarantine-marker":
            manifest["quarantined"] = True
        elif case == "release-ineligible-marker":
            manifest["release_eligibility"] = False
        elif case == "missing-model":
            del manifest["provenance"]["model"]
        elif case == "missing-corpus-source-hashes":
            del manifest["provenance"]["corpus"]["source_hashes"]
        elif case == "wrong-dict-a-status":
            manifest["artifacts"]["dict_a_matcher"]["status"] = "proposal_evidence"
        elif case == "wrong-dict-b-status":
            manifest["artifacts"]["dict_b_canonical"]["status"] = "matcher_ready"
        else:
            raise AssertionError(f"unhandled test case: {case}")

    _rewrite_manifest(candidate, mutate)

    with pytest.raises(
        ValueError,
        match=(
            "schema_version|quarantined|mock|release|provenance|source_hashes|"
            "dict_a_matcher|dict_b_canonical|status"
        ),
    ):
        _evaluate(baseline, candidate, DeterministicRunner(), samples=["alpha"])


def test_candidate_dict_a_shape_and_dict_b_reference_closure_are_required(
    tmp_path: Path,
) -> None:
    baseline = _write_bundle(
        tmp_path / "baseline",
        dict_a_rows=[_dict_a_row("A-BASE-1", "alpha", ["C-1"])],
        dict_b_rows=[_dict_b_row("C-1", [], hex_anchor="HX-0001")],
    )
    invalid_candidates = [
        (
            [{"text": "alpha", "frequency": 7}],
            [_dict_b_row("C-1", [], hex_anchor="HX-0001")],
            "dict_a.*(matcher|normalized_form|schema)",
        ),
        (
            [_dict_a_row("A-CAND-1", "alpha", ["C-MISSING"])],
            [_dict_b_row("C-1", [], hex_anchor="HX-0001")],
            "C-MISSING.*(Dict B|reference|concept)",
        ),
        (
            [_dict_a_row("A-CAND-1", "alpha", ["C-1"])],
            [_dict_b_row("C-1", ["C-MISSING"], hex_anchor="HX-0001")],
            "C-MISSING.*(Dict B|reference|closure)",
        ),
    ]

    for index, (dict_a_rows, dict_b_rows, message) in enumerate(invalid_candidates):
        candidate = _write_bundle(
            tmp_path / f"candidate-{index}",
            dict_a_rows=dict_a_rows,
            dict_b_rows=dict_b_rows,
        )
        with pytest.raises(ValueError, match=message):
            _evaluate(baseline, candidate, DeterministicRunner(), samples=["alpha"])


@pytest.mark.parametrize(
    "case",
    [
        "missing-entry-id",
        "missing-normalized-form",
        "missing-match-type",
        "unsupported-match-type",
        "empty-candidates",
        "duplicate-entry-id",
        "duplicate-normalized-match",
        "duplicate-candidate-id",
    ],
)
def test_candidate_dict_a_matcher_rows_require_identity_shape_and_uniqueness(
    tmp_path: Path,
    case: str,
) -> None:
    baseline = _write_bundle(
        tmp_path / case / "baseline",
        dict_a_rows=[_dict_a_row("A-BASE-1", "alpha", ["C-1"])],
        dict_b_rows=[
            _dict_b_row("C-1", [], hex_anchor="HX-0001"),
            _dict_b_row("C-2", [], hex_anchor="HX-0002"),
        ],
    )
    first = _dict_a_row("A-CAND-1", "alpha", ["C-1"])
    rows = [first]
    if case == "missing-entry-id":
        del first["entry_id"]
    elif case == "missing-normalized-form":
        del first["normalized_form"]
    elif case == "missing-match-type":
        del first["match_type"]
    elif case == "unsupported-match-type":
        first["match_type"] = "fuzzy"
    elif case == "empty-candidates":
        first["candidate_concept_ids"] = []
    elif case == "duplicate-entry-id":
        rows.append(_dict_a_row("A-CAND-1", "beta", ["C-2"]))
    elif case == "duplicate-normalized-match":
        rows.append(_dict_a_row("A-CAND-2", "alpha", ["C-2"]))
    elif case == "duplicate-candidate-id":
        first["candidate_concept_ids"] = ["C-1", "C-1"]
    else:
        raise AssertionError(f"unhandled test case: {case}")

    candidate = _write_bundle(
        tmp_path / case / "candidate",
        dict_a_rows=rows,
        dict_b_rows=[
            _dict_b_row("C-1", [], hex_anchor="HX-0101"),
            _dict_b_row("C-2", [], hex_anchor="HX-0102"),
        ],
    )

    with pytest.raises(
        ValueError,
        match="dict_a|entry_id|normalized_form|match_type|candidate|duplicate|unique",
    ):
        _evaluate(baseline, candidate, DeterministicRunner(), samples=["alpha"])


def test_comparison_rejects_empty_ordered_text_sequence(
    bundles: tuple[Path, Path],
) -> None:
    def forbidden_runner(_text: str, **_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("empty input validation must run before the pipeline")

    with pytest.raises(ValueError, match="texts|samples|empty|non-empty"):
        _evaluate(*bundles, forbidden_runner, samples=[])


@pytest.mark.parametrize(
    "samples",
    [
        [""],
        ["   "],
        [None],
        [17],
        ["alpha", ""],
    ],
    ids=[
        "empty-string",
        "whitespace-only",
        "none",
        "integer",
        "empty-second-sample",
    ],
)
def test_comparison_rejects_non_string_or_empty_samples_before_pipeline(
    bundles: tuple[Path, Path],
    samples: list[Any],
) -> None:
    def forbidden_runner(_text: str, **_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("sample validation must run before the pipeline")

    with pytest.raises(ValueError, match="text|sample|string|empty|non-empty"):
        evaluate.evaluate_bundle_comparison(
            baseline_bundle=bundles[0],
            candidate_bundle=bundles[1],
            texts=samples,
            repo_path=REPO,
            mode="core",
            runner=forbidden_runner,
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("lexical_hits_accepted", -1),
        ("lexical_hits_rejected", -1),
    ],
)
def test_comparison_rejects_negative_pipeline_hit_counts(
    bundles: tuple[Path, Path],
    field: str,
    value: int,
) -> None:
    def invalid_count_runner(text: str, **_kwargs: Any) -> dict[str, Any]:
        output = {
            "canonical_text": text,
            "lexical_hits_accepted": 1,
            "lexical_hits_rejected": 0,
            "concept_weights": {"C-ALPHA": 1.0},
            "family_activation": {"F-ONE": 1.0},
            "span_resolutions": [
                {
                    "source_char_start": 0,
                    "source_char_end": len(text),
                    "source_text_span": text,
                    "candidate_concepts": ["C-ALPHA"],
                    "winning_concept_id": "C-ALPHA",
                }
            ],
        }
        output[field] = value
        return output

    with pytest.raises(ValueError, match="accepted|rejected|count|negative"):
        _evaluate(
            *bundles,
            invalid_count_runner,
            samples=["alpha"],
        )


@pytest.mark.parametrize(
    ("mapping_name", "invalid_value"),
    [
        ("concept_weights", float("nan")),
        ("concept_weights", float("inf")),
        ("concept_weights", float("-inf")),
        ("concept_weights", -0.01),
        ("family_activation", float("nan")),
        ("family_activation", float("inf")),
        ("family_activation", float("-inf")),
        ("family_activation", -0.01),
    ],
    ids=[
        "concept-nan",
        "concept-positive-infinity",
        "concept-negative-infinity",
        "concept-negative",
        "family-nan",
        "family-positive-infinity",
        "family-negative-infinity",
        "family-negative",
    ],
)
def test_comparison_rejects_non_finite_or_negative_activation_values(
    bundles: tuple[Path, Path],
    mapping_name: str,
    invalid_value: float,
) -> None:
    def invalid_activation_runner(text: str, **_kwargs: Any) -> dict[str, Any]:
        output = {
            "canonical_text": text,
            "lexical_hits_accepted": 1,
            "lexical_hits_rejected": 0,
            "concept_weights": {"C-ALPHA": 1.0},
            "family_activation": {"F-ONE": 1.0},
            "span_resolutions": [
                {
                    "source_char_start": 0,
                    "source_char_end": len(text),
                    "source_text_span": text,
                    "candidate_concepts": ["C-ALPHA"],
                    "winning_concept_id": "C-ALPHA",
                }
            ],
        }
        output[mapping_name] = {"invalid-signal": invalid_value}
        return output

    with pytest.raises(
        ValueError,
        match="concept_weights|family_activation|finite|negative|signal",
    ):
        _evaluate(
            *bundles,
            invalid_activation_runner,
            samples=["alpha"],
        )


def test_ordered_texts_receive_content_bound_stable_sample_ids(
    bundles: tuple[Path, Path],
) -> None:
    baseline, candidate = bundles
    samples = ["same text", "same text", "other text"]

    first = _evaluate(
        baseline,
        candidate,
        DeterministicRunner(),
        samples=samples,
    )
    second = _evaluate(
        baseline,
        candidate,
        DeterministicRunner(),
        samples=samples,
    )

    expected_ids = [
        _sha256_bytes(f"{index}\0{text}".encode("utf-8"))
        for index, text in enumerate(samples)
    ]
    assert [sample["sample_id"] for sample in first["samples"]] == expected_ids
    assert [sample["ordinal"] for sample in first["samples"]] == [0, 1, 2]
    assert [sample["text_sha256"] for sample in first["samples"]] == [
        _sha256_bytes(text.encode("utf-8")) for text in samples
    ]
    assert [sample["sample_id"] for sample in second["samples"]] == expected_ids
    assert len(set(expected_ids)) == len(samples)


def test_comparison_reports_normalized_aggregate_deltas(
    bundles: tuple[Path, Path],
) -> None:
    report = _evaluate(*bundles, DeterministicRunner())

    assert report["aggregate"]["baseline"] == {
        "accepted": 2,
        "rejected": 1,
        "coverage": 0.75,
        "entropy": 0.811278,
        "family_distribution": {"F-ONE": 0.25, "F-TWO": 0.75},
    }
    assert report["aggregate"]["candidate"] == {
        "accepted": 3,
        "rejected": 1,
        "coverage": 0.95,
        "entropy": 1.584963,
        "family_distribution": {
            "F-ONE": 0.333333,
            "F-TWO": 0.666667,
        },
    }
    assert report["aggregate"]["delta"] == {
        "accepted": 1,
        "rejected": 0,
        "coverage": 0.2,
        "entropy": 0.773685,
        "family_distribution": {
            "F-ONE": 0.083333,
            "F-TWO": -0.083333,
        },
    }


def test_span_diffs_and_report_sha256_are_canonical_and_deterministic(
    bundles: tuple[Path, Path],
) -> None:
    first = _evaluate(*bundles, DeterministicRunner())
    second = _evaluate(*bundles, DeterministicRunner())

    alpha_beta = first["samples"][0]
    assert [
        (
            span["source_char_start"],
            span["source_char_end"],
            span["status"],
        )
        for span in alpha_beta["span_diffs"]
    ] == [(0, 5, "unchanged"), (6, 10, "candidate_only")]
    assert all(len(span["span_id"]) == 64 for span in alpha_beta["span_diffs"])
    assert alpha_beta["span_diffs"] == second["samples"][0]["span_diffs"]
    assert first == second

    unsigned = {key: value for key, value in first.items() if key != "report_sha256"}
    assert first["report_sha256"] == _sha256_bytes(_canonical_bytes(unsigned))


def test_comparison_report_is_standards_compliant_finite_json(
    bundles: tuple[Path, Path],
) -> None:
    report = _evaluate(*bundles, DeterministicRunner())

    serialized = json.dumps(
        report,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )

    assert json.loads(serialized) == report
    assert "NaN" not in serialized
    assert "Infinity" not in serialized


@pytest.mark.parametrize(
    "case",
    [
        "missing-start",
        "missing-end",
        "string-start",
        "boolean-end",
        "negative-start",
        "zero-width",
        "past-canonical-end",
        "duplicate-offsets",
        "duplicate-span-key",
    ],
)
def test_comparison_rejects_invalid_or_duplicate_span_offsets(
    bundles: tuple[Path, Path],
    case: str,
) -> None:
    span: dict[str, Any] = {
        "source_char_start": 0,
        "source_char_end": 5,
        "source_text_span": "alpha",
        "candidate_concepts": ["C-ALPHA"],
        "winning_concept_id": "C-ALPHA",
    }
    spans = [span]
    if case == "missing-start":
        del span["source_char_start"]
    elif case == "missing-end":
        del span["source_char_end"]
    elif case == "string-start":
        span["source_char_start"] = "0"
    elif case == "boolean-end":
        span["source_char_end"] = True
    elif case == "negative-start":
        span["source_char_start"] = -1
    elif case == "zero-width":
        span["source_char_end"] = 0
    elif case == "past-canonical-end":
        span["source_char_end"] = 11
    elif case == "duplicate-offsets":
        spans.append(
            {
                **span,
                "source_text_span": "ALPHA",
                "winning_concept_id": "C-GAMMA",
            }
        )
    elif case == "duplicate-span-key":
        spans.append(
            {
                **span,
                "candidate_concepts": ["C-GAMMA"],
                "winning_concept_id": "C-GAMMA",
            }
        )
    else:
        raise AssertionError(f"unhandled test case: {case}")

    def invalid_span_runner(
        text: str,
        **_kwargs: Any,
    ) -> dict[str, Any]:
        return {
            "canonical_text": text,
            "lexical_hits_accepted": len(spans),
            "lexical_hits_rejected": 0,
            "concept_weights": {"C-ALPHA": 1.0},
            "family_activation": {"F-ONE": 1.0},
            "span_resolutions": spans,
        }

    with pytest.raises(
        ValueError,
        match="span|source_char_start|source_char_end|offset|duplicate",
    ):
        _evaluate(
            *bundles,
            invalid_span_runner,
            samples=["alpha beta"],
        )


def test_identical_bundles_are_a_strict_weight_zero_identity(
    bundles: tuple[Path, Path],
) -> None:
    _baseline, candidate = bundles

    report = _evaluate(candidate, candidate, DeterministicRunner())

    assert report["weight_zero_identity"] is True
    assert report["aggregate"]["delta"] == {
        "accepted": 0,
        "rejected": 0,
        "coverage": 0.0,
        "entropy": 0.0,
        "family_distribution": {"F-ONE": 0.0, "F-TWO": 0.0},
    }
    for sample in report["samples"]:
        assert sample["baseline"] == sample["candidate"]
        assert all(span["status"] == "unchanged" for span in sample["span_diffs"])


def test_default_real_runner_consumes_ambiguous_candidate_bundle(
    tmp_path: Path,
) -> None:
    baseline_dict_b = _dict_b_row("C-ALPHA", [], hex_anchor="HX-0001")
    baseline_dict_b.update(
        {
            "preferred_label": "Alpha",
            "specificity_rank": 10,
            "area_ids": ["A00"],
            "family_ids": ["F00"],
        }
    )
    candidate_alpha = _dict_b_row(
        "C-ALPHA",
        ["C-BETA"],
        hex_anchor="HX-0001",
    )
    candidate_alpha.update(
        {
            "preferred_label": "Alpha",
            "specificity_rank": 10,
            "area_ids": ["A00"],
            "family_ids": ["F00"],
        }
    )
    candidate_beta = _dict_b_row(
        "C-BETA",
        ["C-ALPHA"],
        hex_anchor="HX-0002",
    )
    candidate_beta.update(
        {
            "preferred_label": "Beta",
            "specificity_rank": 9,
            "area_ids": ["A00"],
            "family_ids": ["F01"],
        }
    )
    baseline = _write_bundle(
        tmp_path / "real-baseline",
        dict_a_rows=[_dict_a_row("A-BASE-REAL-1", "alpha", ["C-ALPHA"])],
        dict_b_rows=[baseline_dict_b],
    )
    candidate = _write_bundle(
        tmp_path / "real-candidate",
        dict_a_rows=[
            _dict_a_row(
                "A-CAND-REAL-1",
                "alpha",
                ["C-ALPHA", "C-BETA"],
            )
        ],
        dict_b_rows=[candidate_alpha, candidate_beta],
    )

    report = evaluate.evaluate_bundle_comparison(
        baseline_bundle=baseline,
        candidate_bundle=candidate,
        texts=["alpha"],
        repo_path=REPO,
        mode="core",
    )

    expected_baseline_id = json.loads(
        (baseline / "manifest.json").read_text(encoding="utf-8")
    )["bundle_id"]
    expected_candidate_id = json.loads(
        (candidate / "manifest.json").read_text(encoding="utf-8")
    )["bundle_id"]
    assert report["baseline"]["bundle_id"] == expected_baseline_id
    assert report["candidate"]["bundle_id"] == expected_candidate_id
    candidate_spans = report["samples"][0]["candidate"]["span_resolutions"]
    assert len(candidate_spans) == 1
    assert candidate_spans[0]["candidate_concepts"] == ["C-ALPHA", "C-BETA"]
    assert candidate_spans[0]["winning_concept_id"] in {"C-ALPHA", "C-BETA"}


def test_ambiguous_candidate_match_is_preserved_as_future_dict_d_signal(
    tmp_path: Path,
) -> None:
    baseline = _write_bundle(
        tmp_path / "baseline",
        dict_a_rows=[_dict_a_row("A-BASE-1", "alpha", ["C-ALPHA"])],
        dict_b_rows=[_dict_b_row("C-ALPHA", [], hex_anchor="HX-0001")],
    )
    candidate = _write_bundle(
        tmp_path / "candidate",
        dict_a_rows=[
            _dict_a_row(
                "A-CAND-1",
                "alpha",
                ["C-ALPHA", "C-BETA"],
            )
        ],
        dict_b_rows=[
            _dict_b_row("C-ALPHA", ["C-BETA"], hex_anchor="HX-0101"),
            _dict_b_row("C-BETA", ["C-ALPHA"], hex_anchor="HX-0102"),
        ],
    )

    def ambiguous_runner(
        text: str,
        *,
        dict_a_paths: list[Path],
        **_kwargs: Any,
    ) -> dict[str, Any]:
        is_candidate = dict_a_paths[0].parent.name == "candidate"
        candidate_ids = ["C-ALPHA", "C-BETA"] if is_candidate else ["C-ALPHA"]
        return {
            "canonical_text": text,
            "lexical_hits_accepted": 1,
            "lexical_hits_rejected": 0,
            "concept_weights": {"C-ALPHA": 1.0},
            "family_activation": {"F-ONE": 1.0},
            "span_resolutions": [
                {
                    "source_char_start": 0,
                    "source_char_end": len(text),
                    "source_text_span": text,
                    "candidate_concepts": candidate_ids,
                    "winning_concept_id": "C-ALPHA",
                }
            ],
        }

    report = _evaluate(
        baseline,
        candidate,
        ambiguous_runner,
        samples=["alpha"],
    )

    signal = report["samples"][0]["ambiguous_candidate_spans"]
    assert signal == [
        {
            "span_id": report["samples"][0]["span_diffs"][0]["span_id"],
            "source_char_start": 0,
            "source_char_end": 5,
            "candidate_concepts": ["C-ALPHA", "C-BETA"],
            "winning_concept_id": "C-ALPHA",
        }
    ]
