# HESPERIA — Tests for LEVEL 2 family structure (TFP domain).
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

"""Tests for families_master.txt and families_structure_tfp.yaml loaders."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def test_load_families_master_240() -> None:
    """T2.1: Master has 240 families, each with area_id, family_id, family_name, family_definition."""
    from sphere.topology import load_families_master
    path = _REPO / "spec" / "families_master.txt"
    entries = load_families_master(path)
    assert len(entries) == 240
    for e in entries:
        assert "area_id" in e and e["area_id"].startswith("A")
        assert "family_id" in e and e["family_id"].startswith("family_")
        assert "family_name" in e
        assert "family_definition" in e


def test_load_families_structure_tfp_240() -> None:
    """T2.2–T2.4: Structure has 240 families with scope, observability, adjacency."""
    from sphere.topology import load_families_structure_tfp, OBSERVABILITY_LEVELS
    path = _REPO / "spec" / "families_structure_tfp.yaml"
    data = load_families_structure_tfp(path)
    families = data["families"]
    assert len(families) == 240
    for f in families:
        assert "scope" in f
        assert "included_phenomena" in f and isinstance(f["included_phenomena"], list)
        assert "excluded_phenomena" in f and isinstance(f["excluded_phenomena"], list)
        assert f.get("observability") in OBSERVABILITY_LEVELS
        assert "family_neighbors" in f and isinstance(f["family_neighbors"], list)
        assert "family_conflicts" in f and isinstance(f["family_conflicts"], list)
        assert "family_complements" in f and isinstance(f["family_complements"], list)


def test_get_family_by_id() -> None:
    """get_family_by_id returns entry with neighbors."""
    from sphere.topology import get_family_by_id
    path = _REPO / "spec" / "families_structure_tfp.yaml"
    entry = get_family_by_id("family_001", path=path)
    assert entry is not None
    assert entry["family_id"] == "family_001"
    assert "family_neighbors" in entry
