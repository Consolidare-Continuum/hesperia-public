# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""
Fuel-chamber capacity floor for core.attribution.attribution_shared — the sole
live core attribution pipeline (core has no relation to any extension/module;
the former "v06" pipeline was retired 2026-07-30, see
core/attribution/_deprecated/README.md) — measured against the frozen B0
token->family ground-truth catalog (same calibration lineage). Baseline
measured 2026-07-30: 99.1% overall (3169/3198), 0 dead families, 0 untested
families; all 29 misses are a single known root cause (tokenizer strips
underscores from compound catalog keys like "addiction_harms", not a
family-detection defect). Floor is set below baseline to catch real
regressions without flaking on that known gap.
"""

from __future__ import annotations

from tools.measure_family_area_capacity import measure_capacity

OVERALL_CAPACITY_FLOOR = 0.95
AREA_CAPACITY_FLOOR = 0.90


def test_overall_fuel_chamber_capacity_above_floor():
    report = measure_capacity()
    overall = report["overall"]
    assert overall["fuel_tokens"] > 0
    assert overall["capacity"] >= OVERALL_CAPACITY_FLOOR


def test_no_area_below_floor():
    report = measure_capacity()
    for area in report["areas"]:
        assert area["fuel_tokens"] > 0, f"area {area['area_id']} has no ground-truth fuel"
        assert area["capacity"] >= AREA_CAPACITY_FLOOR, (
            f"area {area['area_id']} ({area['area_name']}) capacity "
            f"{area['capacity']:.1%} below floor"
        )


def test_no_dead_families():
    report = measure_capacity()
    assert report["dead_families"] == [], f"dead families: {report['dead_families']}"


def test_no_untested_families():
    report = measure_capacity()
    assert report["untested_families"] == [], f"untested families: {report['untested_families']}"
