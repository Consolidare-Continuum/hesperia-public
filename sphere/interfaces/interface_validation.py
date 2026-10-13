# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Centralized validation for public interfaces.
Input validation only; no business logic. Raises ValueError with clear messages.
"""

from __future__ import annotations

from typing import Any

# Configurable default; interfaces may override via config
DEFAULT_MAX_TEXT_LENGTH = 500_000
VALID_LAYER_IDS = frozenset(range(1, 11))


def validate_text_input(
    text: Any,
    max_length: int | None = None,
) -> None:
    """
    Validate text input for structural analysis.
    Raises ValueError if text is not a non-empty string or exceeds max_length.
    """
    if not isinstance(text, str):
        raise ValueError("Text input must be a string")
    if not text or not text.strip():
        raise ValueError("Text input cannot be empty")
    limit = max_length if max_length is not None else DEFAULT_MAX_TEXT_LENGTH
    if len(text) > limit:
        raise ValueError(
            f"Text length ({len(text)}) exceeds allowed maximum ({limit} characters)"
        )


def validate_config(config: Any) -> None:
    """
    Validate config for pipeline execution.
    Raises ValueError if config is missing, not a dict, or missing required keys.
    """
    if config is None:
        raise ValueError("Config must be provided")
    if not isinstance(config, dict):
        raise ValueError("Config must be a dictionary")
    if not config:
        raise ValueError("Config cannot be empty")
    if "pipeline_version" not in config:
        raise ValueError("Config must include pipeline_version")
    if config.get("deterministic") is not True:
        raise ValueError("Config.deterministic must be True for canonical pipeline")


def validate_layer_request(layers: Any) -> None:
    """
    Validate layer list for debug_pipeline.
    Raises ValueError if layers is not None and not a list of valid layer ids (1-10).
    """
    if layers is None:
        return
    if not isinstance(layers, (list, tuple)):
        raise ValueError("layers must be a list or None")
    for i, lid in enumerate(layers):
        if not isinstance(lid, int):
            raise ValueError(f"layers[{i}] must be an integer, got {type(lid).__name__}")
        if lid not in VALID_LAYER_IDS:
            raise ValueError(
                f"layers[{i}] must be a layer id 1-10, got {lid}"
            )
