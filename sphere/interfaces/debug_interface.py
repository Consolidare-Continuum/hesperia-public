# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Layer Debug Interface — inspection of intermediate pipeline layers for development and research.
Uses the same pipeline runner; only difference is which layer outputs are returned.
Does not alter pipeline behavior or skip guards.
"""

from __future__ import annotations

from typing import Any

from sphere.interfaces.interface_validation import (
    validate_config,
    validate_text_input,
    validate_layer_request,
)


def debug_pipeline(
    text: str,
    config: dict[str, Any],
    layers: list[int] | None = None,
) -> dict[str, Any]:
    """
    Run full pipeline and return requested layer outputs only.

    If layers is None, return all layers (layer_1 .. layer_10).
    If layers is e.g. [3, 4, 5], return only layer_3, layer_4, layer_5.
    Layer outputs are returned exactly as produced; no modification.
    """
    validate_text_input(text, max_length=config.get("max_text_length"))
    validate_config(config)
    validate_layer_request(layers)

    from sphere.pipeline import run_pipeline
    result = run_pipeline(text, config, document_id="debug")

    layer_outputs = result.get("layer_outputs") or {}
    if layers is None:
        return dict(layer_outputs)

    out: dict[str, Any] = {}
    for lid in layers:
        key = f"layer_{lid}"
        if key in layer_outputs:
            out[key] = dict(layer_outputs[key])
    return out
