# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""Postgres-backed S/W truth-point support (corpus_grounding.py).

Unit-level: no dict_b_path -> no DB round-trip, S=W=0 always (T reduces to L in the
caller). Live checks against the real tfp_corpus schema are integration-only, run
manually (see the file's own docstring) rather than in the default suite, since they
need a live ops-method-pg on 127.0.0.1:5433.
"""
from __future__ import annotations

from hesperia.modules.tfp.data.tfp_v1.postgres.corpus_grounding import (
    corpus_support,
    load_concept_labels,
)


def test_no_dict_b_path_returns_no_label_without_db_round_trip() -> None:
    result = corpus_support({"B_A10_F10_002", "B_A10_F10_006"}, dict_b_path=None)
    assert result == {
        "B_A10_F10_002": {"S": 0.0, "W": 0.0, "status": "no_label"},
        "B_A10_F10_006": {"S": 0.0, "W": 0.0, "status": "no_label"},
    }


def test_load_concept_labels_missing_file_returns_empty() -> None:
    from pathlib import Path

    assert load_concept_labels(Path("/nonexistent/dict_b.jsonl")) == {}


def test_load_concept_labels_first_non_empty_wins(tmp_path) -> None:
    from pathlib import Path

    p: Path = tmp_path / "dict_b.jsonl"
    p.write_text(
        '{"concept_id": "X", "preferred_label": "first"}\n'
        '{"concept_id": "X", "preferred_label": "second"}\n'
        '{"concept_id": "Y", "preferred_label": ""}\n',
        encoding="utf-8",
    )
    labels = load_concept_labels(p)
    assert labels == {"X": "first"}
