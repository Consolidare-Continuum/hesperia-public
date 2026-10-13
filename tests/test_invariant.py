# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
HESPERIA v0.3 — minimal test matrix (mandatory).
19_SPEC Release v0.3 Structural Enforcement.
Area typo → reject; family/sideId overflow → hard stop; governance/tension clamp;
extra output key → hard stop. If any pass silently → v0.3 not done.
"""

from __future__ import annotations

import pytest

try:
    from core.topology.invariant_catalog import (
        AREAS,
        CANONICAL_AREA_SET,
        AREA_FAMILY_MAP,
        FAMILIES_PER_AREA,
        forward,
        inverse,
        TOTAL_SIDES,
        validate_coord,
        validate_side_id,
    )
    from core.propagation.invariant_enforcer import (
        check_area_canonical,
        check_bijection,
        check_geometry,
        check_family_in_area,
        enforce,
        validate_output_contract,
        clamp_domain,
        REQUIRED_OUTPUT_KEYS,
    )
    from core.propagation.failure_classes import FailureClass
except ImportError:
    from invariant_catalog import (
        AREAS,
        CANONICAL_AREA_SET,
        AREA_FAMILY_MAP,
        FAMILIES_PER_AREA,
        forward,
        inverse,
        TOTAL_SIDES,
        validate_coord,
        validate_side_id,
    )
    from invariant_enforcer import (
        check_area_canonical,
        check_bijection,
        check_geometry,
        check_family_in_area,
        enforce,
        validate_output_contract,
        clamp_domain,
        REQUIRED_OUTPUT_KEYS,
    )
    from failure_classes import FailureClass


# ---------- Area typo → reject ----------
def test_area_typo_reject():
    assert check_area_canonical("GOOD") is True
    assert check_area_canonical("GOODD") is False
    assert check_area_canonical("care") is False  # case-sensitive
    assert check_area_canonical("UNKNOWN") is False


# ---------- Family index overflow → hard stop ----------
def test_family_index_overflow_hard_stop():
    with pytest.raises(RuntimeError, match="Sigma HARD_STOP|family_local"):
        validate_coord(0, FAMILIES_PER_AREA, 0, 0)
    with pytest.raises(RuntimeError, match="Sigma HARD_STOP"):
        check_geometry(12, 25, 250, 6)


# ---------- sideId overflow → hard stop ----------
def test_side_id_overflow_hard_stop():
    with pytest.raises(RuntimeError, match="Sigma HARD_STOP|sideId"):
        validate_side_id(TOTAL_SIDES)
    with pytest.raises(RuntimeError, match="Sigma HARD_STOP|sideId"):
        validate_side_id(-1)


# ---------- governance > 1 → clamped ----------
def test_governance_above_one_clamped():
    result = {
        "governance": 1.5,
        "loopability": 0.5,
        "tension_energy": 0.2,
        "obstacle_score": 0.1,
        "dominant_family": None,
        "dominant_area": None,
    }
    out = clamp_domain(result)
    assert out["governance"] == 1.0


# ---------- negative tension_energy → clamped ----------
def test_negative_tension_energy_clamped():
    result = {
        "governance": 0.8,
        "loopability": 0.5,
        "tension_energy": -0.3,
        "obstacle_score": 0.0,
        "dominant_family": None,
        "dominant_area": None,
    }
    out = clamp_domain(result)
    assert out["tension_energy"] == 0.0


# ---------- extra output key → hard stop ----------
def test_extra_output_key_hard_stop():
    result = {
        "governance": 0.8,
        "loopability": 0.5,
        "tension_energy": 0.2,
        "obstacle_score": 0.1,
        "dominant_family": None,
        "dominant_area": None,
        "extra_key": 42,
    }
    with pytest.raises(RuntimeError, match="Sigma HARD_STOP|exactly"):
        enforce(result, skip_geometry=True, skip_bijection=True)


# ---------- Bijection identity ----------
def test_bijection_identity():
    check_bijection()


# ---------- Geometry constants ----------
def test_geometry_constants():
    check_geometry(AREAS, FAMILIES_PER_AREA, 250, 6)


# ---------- Valid 6-key passes and is clamped ----------
def test_valid_six_key_passes():
    result = {
        "governance": 0.9,
        "loopability": 0.7,
        "tension_energy": 0.1,
        "obstacle_score": 0.2,
        "dominant_family": None,
        "dominant_area": None,
    }
    out = enforce(result, skip_geometry=True, skip_bijection=True)
    assert set(out.keys()) == REQUIRED_OUTPUT_KEYS
    assert out["governance"] == 0.9 and out["loopability"] == 0.7
