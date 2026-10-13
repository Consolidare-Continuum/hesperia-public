# HESPERIA — hesperia-dev-test full-corpus soak (opt-in, manual/nightly). Copyright © 2026 igareosh.com.
"""Full corpus (letters + casefold + digits + numerics + booleans + diacritics + indices) —
observational, not gold-checked. Diacritic-lane fragmentation and any double-/analyze-pass latency
are known sealed behavior (Ethan ETHAN-HDT-01 findings; Grace grind rows), never asserted here as
pass/fail. Marked dev_test_soak — excluded by default (see pytest.ini addopts), matching the `tfp`
convention. Run explicitly with: pytest -m dev_test_soak
"""

from __future__ import annotations

import pytest

from tools.hesperia_dev_test import api_battery, fpf_battery
from tools.hesperia_dev_test.corpus import full_corpus

pytestmark = pytest.mark.dev_test_soak


def test_api_battery_full_corpus_no_crash() -> None:
    client = api_battery.in_process_client()
    results = api_battery.run_battery(client, corpus=full_corpus())

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


def test_fpf_battery_full_corpus_stays_green() -> None:
    results = fpf_battery.run_fpf_battery(corpus=full_corpus())

    errors = [(r.entry.token, r.error) for r in results if r.error]
    assert not errors, f"fpf harness exceptions: {errors}"

    not_ops_ok = [r.entry.token for r in results if not r.ops_ok]
    assert not not_ops_ok, f"ops loop missing ground_truth for: {not_ops_ok}"

    not_dig_ok = [r.entry.token for r in results if not r.dig_ok]
    assert not not_dig_ok, f"dig loop GapReport schema mismatch for: {not_dig_ok}"
