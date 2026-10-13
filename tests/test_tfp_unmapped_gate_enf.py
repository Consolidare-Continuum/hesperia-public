# HESPERIA — TFP-ENF-03: unmapped mass fraction gate on fixed fixture (FAIL if rate > threshold).
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
FIXTURE = REPO / "tests" / "fixtures" / "tfp_unmapped_gate_fixture.json"


def _unmapped_rate(data: dict) -> float:
    total = int(data["total_tokens"])
    assert total > 0
    counts = data.get("unmapped_counts") or {}
    mass = sum(int(v) for v in counts.values())
    return mass / float(total)


def test_unmapped_rate_within_fixture_threshold() -> None:
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
    rate = _unmapped_rate(raw)
    max_frac = float(raw["max_unmapped_mass_fraction"])
    env_cap = os.environ.get("HESPERIA_UNMAPPED_RATE_MAX")
    if env_cap:
        max_frac = min(max_frac, float(env_cap))
    assert rate <= max_frac, f"unmapped_rate={rate} > max={max_frac}"


def test_unmapped_rate_fails_when_fixture_would_violate() -> None:
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
    broken = dict(raw)
    broken["max_unmapped_mass_fraction"] = 0.001
    rate = _unmapped_rate(broken)
    assert rate > broken["max_unmapped_mass_fraction"]
