# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
L1 Normative Structure Profile Extension (34_SPEC N1) — minimal compliance tests.
Case A: perfect match → PCS ≥ 0.95
Case B: strong mismatch → PCS ≤ 0.30
Case C: deny-family hits present → FMP > 0 and PCS reduced
Case D: altitude out of band → ALTD > 0 and PCS reduced
Case E: budget cap violation → BVS > 0
"""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from core.layers.layer_1 import compute_L1
from core.layers.structure_profile import (
    StructureProfile,
    load_structure_profile,
    validate_profile,
    profile_checksum,
)

F, A = 288, 12
EPS = 1e-9


def _uniform_fedv_aedv() -> tuple[list[float], list[float]]:
    fedv = [1.0 / F] * F
    aedv = [1.0 / A] * A
    return fedv, aedv


def _make_profile(
    fedv: list[float],
    aedv: list[float],
    deny: list[int] | None = None,
    alt_band: list[float] | None = None,
    max_area_dom: float | None = None,
    min_coverage: float | None = None,
) -> StructureProfile:
    p: StructureProfile = {"FEDV": fedv, "AEDV": aedv}
    if deny is not None:
        p["DENY_FAMILIES"] = deny
    if alt_band is not None:
        p["ALT_BAND"] = alt_band
    if max_area_dom is not None:
        p["MAX_AREA_DOMINANCE"] = max_area_dom
    if min_coverage is not None:
        p["MIN_COVERAGE_RATIO"] = min_coverage
    return p


def test_baseline_mode_no_profile():
    """No profile → PROFILE_MODE_ACTIVE False; only 34_SPEC metrics."""
    matched = [(0, 0.5), (1, 0.5), (2, 0.5)]  # 3 tokens, 3 families
    out = compute_L1(10, matched, F=F, A=A, eps=EPS)
    assert out["PROFILE_MODE_ACTIVE"] is False
    assert "PROFILE_CONFORMANCE_SCORE" not in out
    assert out["ATTRIBUTED_TOKENS"] == 3
    assert out["COVERAGE_RATIO"] == 0.3


def test_case_a_perfect_match_pcs_high():
    """Perfect match to uniform profile → PCS ≥ 0.95; PROFILE_MODE_ACTIVE True."""
    fedv, aedv = _uniform_fedv_aedv()
    profile = _make_profile(fedv, aedv)
    n_hits = 288 * 5
    matched = [(i % F, 0.5) for i in range(n_hits)]
    out = compute_L1(n_hits, matched, F=F, A=A, eps=EPS, profile_id="uniform", profile=profile)
    assert out["PROFILE_MODE_ACTIVE"] is True
    assert out["PROFILE_CONFORMANCE_SCORE"] >= 0.95, f"PCS={out['PROFILE_CONFORMANCE_SCORE']}"


def test_case_b_strong_mismatch_pcs_low():
    """Strong mismatch (all mass on one family) → PCS ≤ 0.30."""
    fedv, aedv = _uniform_fedv_aedv()
    profile = _make_profile(fedv, aedv)
    # All hits on family 0
    matched = [(0, 0.5)] * 100
    out = compute_L1(100, matched, F=F, A=A, eps=EPS, profile_id="uniform", profile=profile)
    assert out["PROFILE_CONFORMANCE_SCORE"] <= 0.35  # allow small tolerance


def test_case_c_deny_family_fmp_positive():
    """Deny families hit → FMP > 0 and PCS reduced."""
    fedv, aedv = _uniform_fedv_aedv()
    profile = _make_profile(fedv, aedv, deny=[0, 1, 2])
    # Put some hits on denied family 0
    matched = [(0, 0.5)] * 10 + [(50, 0.5)] * 90
    out = compute_L1(100, matched, F=F, A=A, eps=EPS, profile_id="deny", profile=profile)
    assert "FORBIDDEN_MASS_PENALTY" in out
    assert out["FORBIDDEN_MASS_PENALTY"] > 0
    assert out["PROFILE_CONFORMANCE_SCORE"] < 1.0


def test_case_d_altitude_out_of_band_altd_positive():
    """Altitude outside band → ALTD > 0 and PCS reduced."""
    fedv, aedv = _uniform_fedv_aedv()
    profile = _make_profile(fedv, aedv, alt_band=[0.3, 0.6])
    # Mean altitude 0.9 (above band)
    matched = [(f % 20, 0.9) for f in range(100)]
    out = compute_L1(100, matched, F=F, A=A, eps=EPS, profile_id="alt", profile=profile)
    assert "ALTITUDE_DEVIATION" in out
    assert out["ALTITUDE_DEVIATION"] > 0
    assert out["PROFILE_CONFORMANCE_SCORE"] < 1.0


def test_case_e_budget_violation_bvs_positive():
    """Budget cap violation → BVS > 0."""
    fedv, aedv = _uniform_fedv_aedv()
    # Require MIN_COVERAGE_RATIO 0.5 but give only 0.2
    profile = _make_profile(fedv, aedv, min_coverage=0.5)
    matched = [(0, 0.5)] * 20  # 20 attributed
    out = compute_L1(100, matched, F=F, A=A, eps=EPS, profile_id="budget", profile=profile)
    assert out["COVERAGE_RATIO"] == 0.2
    assert "BUDGET_VIOLATION_SCORE" in out
    assert out["BUDGET_VIOLATION_SCORE"] > 0


def test_profile_load_and_checksum():
    """Load profile from JSON; checksum deterministic."""
    repo = Path(__file__).resolve().parent.parent
    path = repo / "docs" / "specs" / "profiles" / "STRUCTURE_PROFILE__uniform__v1.json"
    if not path.exists():
        pytest.skip("docs/specs/profiles/STRUCTURE_PROFILE__uniform__v1.json not found")
    profile, checksum = load_structure_profile(path, F=F, A=A)
    assert len(profile["FEDV"]) == F and len(profile["AEDV"]) == A
    assert checksum == profile_checksum(profile)


def test_validate_profile_rejects_bad_length():
    """Validate rejects wrong FEDV length."""
    fedv, aedv = _uniform_fedv_aedv()
    bad = [fedv[:100], aedv]  # FEDV length 100
    profile: StructureProfile = {"FEDV": bad[0], "AEDV": bad[1]}
    with pytest.raises(ValueError, match="FEDV"):
        validate_profile(profile, F=F, A=A)


def test_empty_attributed_profile_mode():
    """When attributed == 0 and profile supplied: FPD=1, APD=1, PCS=0 (deterministic)."""
    fedv, aedv = _uniform_fedv_aedv()
    profile = _make_profile(fedv, aedv)
    out = compute_L1(100, [], F=F, A=A, eps=EPS, profile_id="empty", profile=profile)
    assert out["PROFILE_MODE_ACTIVE"] is True
    assert out["FAMILY_PROFILE_DEVIATION"] == 1.0
    assert out["AREA_PROFILE_DEVIATION"] == 1.0
    assert out["PROFILE_CONFORMANCE_SCORE"] == 0.0


def test_validate_profile_rejects_fedv_sum_not_one():
    """Validate rejects FEDV sum != 1."""
    fedv = [0.5] + [0.0] * (F - 1)
    aedv = [1.0 / A] * A
    profile = _make_profile(fedv, aedv)
    with pytest.raises(ValueError, match="sum to 1"):
        validate_profile(profile, F=F, A=A)
