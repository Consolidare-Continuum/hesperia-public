# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

"""Optional Dict-A ``confidence_type`` (strong|weak) scales marker weight at load time."""

from __future__ import annotations

import tempfile
from pathlib import Path

import yaml


def test_build_marker_to_concepts_confidence_type_weak_multiplier() -> None:
    from hesperia.ontology.dictA.loader import build_marker_to_concepts

    data = {
        "version": 0,
        "entries": [
            {"marker": "убью", "concept_id": "B_A4_F1_001", "weight": 1.0, "confidence_type": "strong"},
            {"marker": "на свою", "concept_id": "B_A1_F1_001", "weight": 1.0, "confidence_type": "weak"},
        ],
    }
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "m.yaml"
        p.write_text(yaml.safe_dump(data), encoding="utf-8")
        idx = build_marker_to_concepts(p)
    assert idx["убью"] == [("B_A4_F1_001", 1.0)]
    assert idx["на свою"] == [("B_A1_F1_001", 0.3)]
