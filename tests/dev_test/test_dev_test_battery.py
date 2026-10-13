# HESPERIA — hesperia-dev-test pytest battery (opt-in, in-process only). Copyright © 2026 igareosh.com.
"""Semantics-free structural + FPF-BUII math consistency battery, restricted to the bench0_latin
lane (Colombo Bench-0 design, 2026-07-26) — this is the fast CI/agent path. Full corpus (digit/
bool/index/diacritic lanes) lives in test_dev_test_soak.py under `dev_test_soak` (opt-in, excluded
by default). Marked dev_test; runs by default (not excluded via addopts, unlike `tfp`) since it
stays fast (in-process, bench0_latin only, no live server). Select explicitly with:
pytest -m dev_test
"""

from __future__ import annotations

import pytest

from tools.hesperia_dev_test import api_battery, fpf_battery
from tools.hesperia_dev_test.corpus import bench0_latin

pytestmark = pytest.mark.dev_test


def test_api_battery_structural_invariants() -> None:
    client = api_battery.in_process_client()
    results = api_battery.run_battery(client, corpus=bench0_latin())

    errors = [(r.entry.token, r.error) for r in results if r.error]
    assert not errors, f"unexpected exceptions: {errors}"

    bad_status = [
        (r.entry.token, r.analyze_status, r.interpret_status)
        for r in results
        if r.analyze_status != 200 or r.interpret_status != 200
    ]
    assert not bad_status, f"non-200 responses: {bad_status}"

    non_deterministic = [r.entry.token for r in results if r.deterministic is False]
    assert not non_deterministic, f"non-deterministic tokens: {non_deterministic}"


def test_fpf_battery_stays_green() -> None:
    results = fpf_battery.run_fpf_battery(corpus=bench0_latin())

    errors = [(r.entry.token, r.error) for r in results if r.error]
    assert not errors, f"fpf harness exceptions: {errors}"

    not_ops_ok = [r.entry.token for r in results if not r.ops_ok]
    assert not not_ops_ok, f"ops loop missing ground_truth for: {not_ops_ok}"

    not_dig_ok = [r.entry.token for r in results if not r.dig_ok]
    assert not not_dig_ok, f"dig loop GapReport schema mismatch for: {not_dig_ok}"
