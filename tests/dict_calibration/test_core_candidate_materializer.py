# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from tools.dict_calibration.core_candidate import materialize_candidate


def _canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_bytes(b"".join(_canonical_bytes(row) for row in rows))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture()
def live06_reduced(tmp_path: Path) -> Path:
    producer = tmp_path / "producer"
    producer.mkdir()
    drafts = [
        {"concept_id": "proposal-alpha", "from_lexical": ["alpha"], "labels": ["Alpha"]},
        {"concept_id": "proposal-beta", "from_lexical": ["beta"], "labels": ["Beta"]},
    ]
    _write_jsonl(producer / "dict_b_draft.jsonl", drafts)
    _write_jsonl(
        producer / "dict_b_anchored.jsonl",
        [
            {
                "concept_id": "C-001",
                "related_concept_ids": [],
                "area_ids": ["A00"],
                "family_ids": ["F00"],
                "calibration_draft_id": "proposal-alpha",
                "calibration_bind_score": 1.0,
                "calibration_bind_reason": "exact_id",
                "preferred_label": "discard me",
            },
            {
                "concept_id": "C-001",
                "related_concept_ids": [],
                "area_ids": ["A00"],
                "family_ids": ["F00"],
                "calibration_draft_id": "proposal-beta",
                "calibration_bind_score": 0.91,
                "calibration_bind_reason": "fuzzy_label",
                "definition": "discard me too",
            },
        ],
    )
    _write_jsonl(producer / "dict_b_rejected.jsonl", [])
    _write_jsonl(
        producer / "dict_a_to_b_links.jsonl",
        [
            {
                "lexical": "beta",
                "concept_id": "C-001",
                "match_type": "exact",
                "priority": 0.8,
            },
            {
                "lexical": "alpha",
                "concept_id": "C-001",
                "match_type": "exact",
                "priority": 1.0,
            },
        ],
    )
    _write_jsonl(
        producer / "dict_a_engine.jsonl",
        [
            {
                "entry_id": "CAL-00002",
                "surface_form": "beta",
                "normalized_form": "beta",
                "match_type": "exact",
                "candidate_concept_ids": ["C-001"],
                "priority": 8,
                "version": "v0.6.0-cal",
            },
            {
                "entry_id": "CAL-00001",
                "surface_form": "alpha",
                "normalized_form": "alpha",
                "match_type": "exact",
                "candidate_concept_ids": ["C-001"],
                "priority": 10,
                "version": "v0.6.0-cal",
            },
        ],
    )
    return producer


def test_materializes_strict_abc_and_truthful_zero(
    live06_reduced: Path,
    tmp_path: Path,
) -> None:
    output = tmp_path / "materialized"

    result = materialize_candidate(live06_reduced, output)

    assert result["row_counts"] == {
        "dict_a_matcher": 2,
        "dict_b_authored_edge_provenance": 0,
        "dict_b_canonical": 1,
        "dict_b_proposal_evidence": 2,
        "dict_c_intermediate": 2,
        "dict_c_runtime_conversion": 2,
        "dict_c_source": 2,
    }
    assert (output / "dict_a.jsonl").read_text(encoding="utf-8").splitlines() == [
        '{"candidate_concept_ids":["C-001"],"entry_id":"CAL-00001","match_type":"exact","normalized_form":"alpha"}',
        '{"candidate_concept_ids":["C-001"],"entry_id":"CAL-00002","match_type":"exact","normalized_form":"beta"}',
    ]
    assert (output / "dict_b.jsonl").read_text(encoding="utf-8") == (
        '{"area_ids":["A00"],"concept_id":"C-001","family_ids":["F00"],'
        '"related_concept_ids":[]}\n'
    )
    edge_path = output / "evidence/dict_b_authored_edges.jsonl"
    assert edge_path.read_bytes() == b""
    assert _sha256(edge_path) == hashlib.sha256(b"").hexdigest()

    source_rows = [
        json.loads(line)
        for line in (output / "evidence/dict_c_source.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    intermediate_rows = [
        json.loads(line)
        for line in (output / "evidence/dict_c_intermediate.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    runtime_rows = [
        json.loads(line)
        for line in (output / "dict_c.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert {row["link_id"] for row in source_rows} == {
        link_id
        for row in intermediate_rows
        for link_id in row["source_link_ids"]
    }
    assert runtime_rows == [
        {
            "normalized_form": row["normalized_form"],
            "candidate_concept_ids": row["candidate_concept_ids"],
            "priority": row["priority"],
        }
        for row in intermediate_rows
    ]


def test_rejected_proposal_is_a_distinct_exact_variant(
    live06_reduced: Path,
    tmp_path: Path,
) -> None:
    drafts = [
        json.loads(line)
        for line in (live06_reduced / "dict_b_draft.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    _write_jsonl(live06_reduced / "dict_b_draft.jsonl", drafts[:1])
    _write_jsonl(live06_reduced / "dict_b_anchored.jsonl", [])
    _write_jsonl(
        live06_reduced / "dict_b_rejected.jsonl",
        [
            {
                "draft": drafts[0],
                "reason": "cannot_anchor",
                "best_score": 0.1,
                "detail": "no_match",
            }
        ],
    )
    _write_jsonl(
        live06_reduced / "dict_a_engine.jsonl",
        [
            {
                "entry_id": "CAL-1",
                "surface_form": "alpha",
                "normalized_form": "alpha",
                "match_type": "exact",
                "candidate_concept_ids": ["C-001"],
                "priority": 10,
                "version": "v",
            }
        ],
    )
    _write_jsonl(
        live06_reduced / "dict_b_anchored.jsonl",
        [
            {
                "concept_id": "C-001",
                "related_concept_ids": [],
                "calibration_draft_id": "other",
                "calibration_bind_score": 1.0,
                "calibration_bind_reason": "exact_id",
            }
        ],
    )
    _write_jsonl(
        live06_reduced / "dict_b_draft.jsonl",
        [drafts[0], {"concept_id": "other"}],
    )

    materialize_candidate(live06_reduced, tmp_path / "output")

    rows = [
        json.loads(line)
        for line in (tmp_path / "output/evidence/dict_b_proposals.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    rejected = next(row for row in rows if row["outcome"] == "rejected")
    assert set(rejected) == {
        "proposal_id",
        "outcome",
        "proposed_concept_id",
        "reason",
        "best_score",
        "detail",
        "source_ordinal",
    }
    assert "anchor" not in rejected


def test_duplicate_draft_ids_consume_exact_occurrences_by_lowest_ordinal(
    live06_reduced: Path,
    tmp_path: Path,
) -> None:
    duplicate_a = {
        "concept_id": "duplicate",
        "from_lexical": ["alpha"],
        "labels": ["same"],
    }
    duplicate_b = {
        "concept_id": "duplicate",
        "from_lexical": ["beta"],
        "labels": ["different"],
    }
    _write_jsonl(
        live06_reduced / "dict_b_draft.jsonl",
        [duplicate_a, duplicate_a, duplicate_b],
    )
    base = {
        "concept_id": "C-001",
        "related_concept_ids": [],
        "calibration_draft_id": "duplicate",
        "calibration_bind_score": 1.0,
        "calibration_bind_reason": "exact_id",
    }
    _write_jsonl(
        live06_reduced / "dict_b_anchored.jsonl",
        [
            {**base, "calibration_from_lexical": ["alpha"]},
            {**base, "calibration_from_lexical": ["beta"]},
            {**base, "calibration_from_lexical": ["alpha"]},
        ],
    )

    materialize_candidate(live06_reduced, tmp_path / "output")

    rows = [
        json.loads(line)
        for line in (tmp_path / "output/evidence/dict_b_proposals.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert sorted(row["source_ordinal"] for row in rows) == [0, 1, 2]
    alpha_ordinals = sorted(
        row["source_ordinal"]
        for row in rows
        if row["source_ordinal"] in {0, 1}
    )
    assert alpha_ordinals == [0, 1]


def test_duplicate_draft_id_with_differing_unmatched_content_fails_closed(
    live06_reduced: Path,
    tmp_path: Path,
) -> None:
    _write_jsonl(
        live06_reduced / "dict_b_draft.jsonl",
        [
            {"concept_id": "duplicate", "from_lexical": ["alpha"]},
            {"concept_id": "duplicate", "from_lexical": ["beta"]},
        ],
    )
    anchored = [
        {
            "concept_id": "C-001",
            "related_concept_ids": [],
            "calibration_draft_id": "duplicate",
            "calibration_bind_score": 1.0,
            "calibration_bind_reason": "exact_id",
        },
        {
            "concept_id": "C-001",
            "related_concept_ids": [],
            "calibration_draft_id": "duplicate",
            "calibration_bind_score": 1.0,
            "calibration_bind_reason": "exact_id",
        },
    ]
    _write_jsonl(live06_reduced / "dict_b_anchored.jsonl", anchored)

    with pytest.raises(ValueError, match="ambiguous differing content"):
        materialize_candidate(live06_reduced, tmp_path / "output")


def test_dict_c_preserves_finite_float_priority(
    live06_reduced: Path,
    tmp_path: Path,
) -> None:
    links = [
        {
            "lexical": "alpha",
            "concept_id": "C-001",
            "match_type": "exact",
            "priority": 0.875,
        }
    ]
    _write_jsonl(live06_reduced / "dict_a_to_b_links.jsonl", links)

    materialize_candidate(live06_reduced, tmp_path / "output")

    runtime = json.loads(
        (tmp_path / "output/dict_c.jsonl").read_text(encoding="utf-8")
    )
    assert runtime["priority"] == 0.875


@pytest.mark.parametrize(
    ("target", "mutation", "message"),
    [
        (
            "dict_a_engine.jsonl",
            lambda rows: rows + [dict(rows[0], entry_id="CAL-OTHER")],
            "duplicate normalized",
        ),
        (
            "dict_b_anchored.jsonl",
            lambda rows: rows + [dict(rows[0], family_ids=["F99"])],
            "conflicting duplicate",
        ),
        (
            "dict_b_rejected.jsonl",
            lambda rows: [{"draft": {"concept_id": "unknown"}, "reason": "x", "best_score": 0.0, "detail": "x"}],
            "unknown proposal",
        ),
    ],
)
def test_adversarial_producer_mutations_fail_closed(
    live06_reduced: Path,
    tmp_path: Path,
    target: str,
    mutation: Any,
    message: str,
) -> None:
    path = live06_reduced / target
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    _write_jsonl(path, mutation(rows))

    with pytest.raises(ValueError, match=message):
        materialize_candidate(live06_reduced, tmp_path / "output")
