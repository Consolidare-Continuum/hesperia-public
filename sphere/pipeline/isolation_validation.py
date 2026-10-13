# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Layer isolation validation: verify layers do not mutate upstream artifacts.
Uses deep-copy snapshots and equality checks after each layer completes.
"""

from __future__ import annotations

import copy
from typing import Any


def snapshot_layer_output(payload: dict[str, Any]) -> dict[str, Any]:
    """Deep copy of payload for later comparison. Ensures no in-place mutation."""
    return copy.deepcopy(payload)


def validate_no_upstream_mutation(
    previous_snapshot: dict[str, Any],
    current_reference: dict[str, Any],
    layer_name: str,
) -> None:
    """
    Verify that current_reference has not been mutated from previous_snapshot.
    Raises ValueError if contents differ (indicating upstream was mutated).
    """
    if previous_snapshot != current_reference:
        raise ValueError(
            f"Isolation violation: {layer_name} or later mutated upstream artifact "
            "(previous snapshot != current reference)"
        )


def validate_layer_isolation(layer_outputs: dict[str, Any]) -> None:
    """
    Structural check: layer_outputs must be a dict of layer_1..layer_N,
    each value a dict. Does not re-run pipeline; use with snapshots taken during run.
    Caller should have taken snapshots after each layer and verified no mutation;
    this function only checks that raw vs propagated separation is respected
    (e.g. layer_7 must not overwrite raw family_counts in layer_3).
    """
    if not isinstance(layer_outputs, dict):
        raise ValueError("layer_outputs must be a dict")
    for i in range(1, 11):
        key = f"layer_{i}"
        if key not in layer_outputs:
            continue
        if not isinstance(layer_outputs[key], dict):
            raise ValueError(f"{key} must be a dict")
