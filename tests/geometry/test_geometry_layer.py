# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Structural geometry layer tests: loader, index, boundary validation.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def test_load_area_geometry() -> None:
    """Area geometry loads; 12 areas, 24 family_members each."""
    from sphere.geometry import load_area_geometry
    path = _REPO / "spec" / "area_geometry.yaml"
    ag = load_area_geometry(path)
    assert ag.get("version") == 1
    areas = ag.get("areas") or []
    assert len(areas) == 12
    for a in areas:
        members = a.get("family_members") or []
        assert len(members) == 24
        assert set(a.get("adjacent_areas") or []) <= set(range(12))


def test_load_family_geometry() -> None:
    """Family geometry loads; 288 families, area_id 0..11, boundary_class allowed."""
    from sphere.geometry import load_family_geometry, ALLOWED_BOUNDARY_CLASSES
    path = _REPO / "spec" / "family_geometry.yaml"
    fg = load_family_geometry(path)
    assert fg.get("version") == 1
    families = fg.get("families") or []
    assert len(families) == 288
    for f in families:
        assert 0 <= int(f.get("area_id", -1)) < 12
        assert f.get("boundary_class") in ALLOWED_BOUNDARY_CLASSES
        assert len(f.get("neighbor_families") or []) == 2


def test_build_geometry_index() -> None:
    """Index has families_by_index, areas_by_index, families_by_area, boundary_families, bridge_families."""
    from sphere.geometry import load_family_geometry, load_area_geometry, build_geometry_index
    fg = load_family_geometry(_REPO / "spec" / "family_geometry.yaml")
    ag = load_area_geometry(_REPO / "spec" / "area_geometry.yaml")
    idx = build_geometry_index(fg, ag)
    assert len(idx["families_by_index"]) == 288
    assert len(idx["areas_by_index"]) == 12
    assert len(idx["families_by_area"]) == 12
    assert "boundary_families" in idx
    assert "bridge_families" in idx


def test_validate_topological_boundaries_pass() -> None:
    """Validator passes with canonical spec and topology data."""
    from sphere.geometry import (
        load_family_geometry,
        load_area_geometry,
        validate_topological_boundaries,
    )
    from sphere.topology import load_area_adjacency, load_family_area_mapping
    fg = load_family_geometry(_REPO / "spec" / "family_geometry.yaml")
    ag = load_area_geometry(_REPO / "spec" / "area_geometry.yaml")
    adj = load_area_adjacency()
    f2a = load_family_area_mapping()
    r = validate_topological_boundaries(fg, ag, adj, f2a)
    assert r["passed"] is True
    assert "AREA_COUNT_12" in r["passed_checks"]
    assert "FAMILY_COUNT_288" in r["passed_checks"]
    assert "FAMILY_AREA_PARTITION_VALID" in r["passed_checks"]
    assert "AREA_ADJACENCY_MATCHES_GEOMETRY" in r["passed_checks"]
    assert "BOUNDARY_LEGALITY" in r["passed_checks"]
    assert len(r["failed_checks"]) == 0
