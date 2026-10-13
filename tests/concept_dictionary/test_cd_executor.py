# HESPERIA — CD executor tests. Copyright © 2026 igareosh.com.
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from hesperia.engine.concept_dictionary.executor import apply_cd_phase1, apply_saturation
from hesperia.engine.concept_dictionary.loader import load_cd_registry
from hesperia.engine.concept_dictionary.validator import CDValidationError, validate_cd_row


def test_apply_saturation_identity() -> None:
    assert apply_saturation(3.0, 1.0) == pytest.approx(3.0)


def test_load_default_registry(tmp_path: Path) -> None:
    p = tmp_path / "cd.jsonl"
    p.write_text(
        json.dumps(
            {
                "concept_id": "*",
                "type": "state",
                "activation": {
                    "base_weight": 1.0,
                    "cap": 10.0,
                    "saturation_k": 1.0,
                    "threshold": 0.0,
                },
                "constraints": {"requires": [], "excludes": [], "co_occurs": []},
                "effects": {"amplifies": {}, "inhibits": {}},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    reg = load_cd_registry(p)
    assert "*" in reg


def test_requires_drop(tmp_path: Path) -> None:
    p = tmp_path / "cd.jsonl"
    rows = [
        {
            "concept_id": "*",
            "type": "state",
            "activation": {"base_weight": 1.0, "cap": 10.0, "saturation_k": 1.0, "threshold": 0.0},
            "constraints": {"requires": [], "excludes": [], "co_occurs": []},
            "effects": {"amplifies": {}, "inhibits": {}},
        },
        {
            "concept_id": "B_A",
            "type": "state",
            "activation": {"base_weight": 1.0, "cap": 10.0, "saturation_k": 1.0, "threshold": 0.0},
            "constraints": {"requires": ["B_B"], "excludes": [], "co_occurs": []},
            "effects": {"amplifies": {}, "inhibits": {}},
        },
        {
            "concept_id": "B_B",
            "type": "state",
            "activation": {"base_weight": 1.0, "cap": 10.0, "saturation_k": 1.0, "threshold": 0.0},
            "constraints": {"requires": [], "excludes": [], "co_occurs": []},
            "effects": {"amplifies": {}, "inhibits": {}},
        },
    ]
    p.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    out = apply_cd_phase1({"B_A": 1.0, "B_B": 0.0}, {"B_A": 2, "B_B": 0}, p)
    assert "B_A" not in out
    out2 = apply_cd_phase1({"B_A": 1.0, "B_B": 1.0}, {"B_A": 2, "B_B": 1}, p)
    assert "B_A" in out2


def test_co_occurs_phase2_miss_vs_full(tmp_path: Path) -> None:
    """CO_OCCURS_MATH_PHASE2.md — penalty when co_occur peers missing; boost when present."""
    p = tmp_path / "cd.jsonl"
    rows = [
        {
            "concept_id": "*",
            "type": "state",
            "activation": {"base_weight": 1.0, "cap": 10.0, "saturation_k": 1.0, "threshold": 0.0},
            "constraints": {"requires": [], "excludes": [], "co_occurs": []},
            "effects": {"amplifies": {}, "inhibits": {}},
        },
        {
            "concept_id": "B_A",
            "type": "state",
            "activation": {"base_weight": 1.0, "cap": 10.0, "saturation_k": 1.0, "threshold": 0.0},
            "constraints": {"requires": [], "excludes": [], "co_occurs": ["B_Z"]},
            "effects": {"amplifies": {}, "inhibits": {}},
        },
        {
            "concept_id": "B_Z",
            "type": "state",
            "activation": {"base_weight": 1.0, "cap": 10.0, "saturation_k": 1.0, "threshold": 0.0},
            "constraints": {"requires": [], "excludes": [], "co_occurs": []},
            "effects": {"amplifies": {}, "inhibits": {}},
        },
    ]
    p.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    w = {"B_A": 1.0, "B_Z": 1.0}
    e = {"B_A": 2, "B_Z": 2}
    miss = apply_cd_phase1({"B_A": 1.0}, {"B_A": 2}, p, cd_phase=2)
    full = apply_cd_phase1(w, e, p, cd_phase=2)
    # Phase 1 alone gives B_A weight 2.0; miss=1 => *0.8
    assert miss["B_A"] == pytest.approx(1.6)
    assert full["B_A"] > miss["B_A"]
    assert full["B_Z"] == pytest.approx(2.0)
    no_soft = apply_cd_phase1({"B_A": 1.0}, {"B_A": 2}, p, cd_phase=1)
    assert no_soft["B_A"] == pytest.approx(2.0)


def test_determinism_double_run(tmp_path: Path) -> None:
    p = tmp_path / "cd.jsonl"
    p.write_text(
        json.dumps(
            {
                "concept_id": "*",
                "type": "state",
                "activation": {"base_weight": 1.0, "cap": 10.0, "saturation_k": 1.0, "threshold": 0.0},
                "constraints": {"requires": [], "excludes": [], "co_occurs": []},
                "effects": {"amplifies": {}, "inhibits": {}},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    w = {"X": 0.5, "Y": 1.2}
    e = {"X": 3, "Y": 1}
    a = apply_cd_phase1(w, e, p)
    b = apply_cd_phase1(w, e, p)
    assert a == b


def test_validate_too_many_requires() -> None:
    with pytest.raises(CDValidationError):
        validate_cd_row(
            {
                "concept_id": "z",
                "type": "state",
                "activation": {"base_weight": 1.0, "cap": 1.0, "saturation_k": 1.0, "threshold": 0.0},
                "constraints": {"requires": ["a", "b", "c"], "excludes": [], "co_occurs": []},
            }
        )


def test_real_asset_path_exists() -> None:
    root = Path(__file__).resolve().parents[2]
    asset = root / "assets" / "data" / "engine_dynamics_v060" / "concept_dict" / "concept_dict_cd.jsonl"
    assert asset.is_file()
    reg = load_cd_registry(asset)
    assert "*" in reg
