# HESPERIA — TFP-ENF-02: CD ON vs OFF produces bounded non-zero delta on fixed fixture.
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
from __future__ import annotations

import json
from pathlib import Path

import pytest

from hesperia.engine.concept_dictionary.executor import apply_cd_phase1


def _l1_delta(a: dict[str, float], b: dict[str, float]) -> float:
    keys = set(a) | set(b)
    return sum(abs(float(a.get(k, 0.0)) - float(b.get(k, 0.0))) for k in keys)


def test_cd_delta_nonzero_and_bounded(tmp_path: Path) -> None:
    """CD OFF = pre-CD weights; CD ON = phase-2 executor with co_occurs — must change state but not explode."""
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
    pre_cd = {"B_A": 1.0, "B_Z": 1.0}
    evidence = {"B_A": 2, "B_Z": 2}
    cd_off = dict(pre_cd)
    cd_on = apply_cd_phase1(pre_cd, evidence, p, cd_phase=2)
    delta = _l1_delta(cd_on, cd_off)
    assert delta > 0.05, "CD_ON must differ from CD_OFF (CD useless if zero delta)"
    assert delta < 80.0, "CD delta unbounded — instability guard"
