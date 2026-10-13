# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Pipeline isolation validation tests.
Verify snapshot and no-upstream-mutation checks.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from sphere.pipeline.isolation_validation import (
    snapshot_layer_output,
    validate_no_upstream_mutation,
    validate_layer_isolation,
)


def test_snapshot_is_deep_copy() -> None:
    """Snapshot must not share reference with original."""
    payload = {"a": [1, 2], "nested": {"x": 3}}
    snap = snapshot_layer_output(payload)
    payload["a"].append(3)
    assert len(snap["a"]) == 2
    assert payload["a"] != snap["a"]


def test_validate_no_upstream_mutation_unchanged() -> None:
    """Identical snapshot and reference pass."""
    prev = {"x": 1, "y": [2, 3]}
    current = {"x": 1, "y": [2, 3]}
    validate_no_upstream_mutation(prev, current, "layer_3")


def test_validate_no_upstream_mutation_detects_change() -> None:
    """Mutated reference raises."""
    prev = {"x": 1}
    current = {"x": 2}
    try:
        validate_no_upstream_mutation(prev, current, "layer_2")
        assert False, "expected ValueError"
    except ValueError as e:
        assert "Isolation" in str(e) or "mutation" in str(e).lower()


def test_validate_layer_isolation_structure() -> None:
    """validate_layer_isolation accepts dict of layer_1..layer_10 dicts."""
    layer_outputs = {f"layer_{i}": {"dummy": i} for i in range(1, 11)}
    validate_layer_isolation(layer_outputs)


def test_validate_layer_isolation_rejects_non_dict() -> None:
    """Non-dict layer_outputs or non-dict value raises."""
    try:
        validate_layer_isolation("not a dict")
        assert False
    except ValueError as e:
        assert "dict" in str(e).lower()
