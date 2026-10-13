# HESPERIA — Bench-0 gold pytest node. Copyright © 2026 igareosh.com.
"""Gold-pinned structural/math compliance for bare Latin a-z (bench0_latin lane) — the CI/agent
fast path per Colombo's Bench-0 design (COLOMBO-HESPERIA-DEV-TEST-BENCH0-DESIGN-2026-07-26.md).
Never asserts what a letter "means"; a flat/uniform result across a-z is the pinned gold, not a
failure (ADV-09). If this test needs updating because the gold witness genuinely changed, that is
an explicit Felix/Ethan re-gold step (see tools/hesperia_dev_test/gold/bench0_v0_1.json), never a
silent edit to make it pass.
"""

from __future__ import annotations

import pytest

from tools.hesperia_dev_test import bench0

pytestmark = pytest.mark.dev_test


def test_bench0_latin_gold() -> None:
    results = bench0.run_bench0()
    failing = {r.entry.token: r.violations for r in results if not r.ok}
    assert not failing, f"Bench-0 gold violations: {failing}"
