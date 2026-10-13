# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Tests for family to area mapping (288 families → 0..11).
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def test_family_area_mapping_valid() -> None:
    """Mapping has 288 entries; each area in 0..11."""
    from sphere.topology import load_family_area_mapping
    mapping = load_family_area_mapping()
    assert len(mapping) == 288
    assert all(0 <= int(a) < 12 for a in mapping)


def test_family_area_mapping_canonical_order() -> None:
    """family_001..family_288 map to areas 0..11 in blocks of 24."""
    from sphere.topology import load_family_area_mapping
    mapping = load_family_area_mapping()
    for i in range(288):
        expected_area = i // 24
        assert mapping[i] == expected_area
