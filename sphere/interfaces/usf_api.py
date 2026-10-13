# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
USF Output API — structured access to USF artifacts for downstream systems.
Deterministic serialization; no mutation of USF. Schema validation before return.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any


def get_usf(result: dict[str, Any]) -> dict[str, Any]:
    """
    Extract USF from an analyze_text / pipeline result.
    Returns a copy of the USF dict; does not mutate result. If USF is missing or error, returns empty dict.
    """
    usf = result.get("usf")
    if usf is None or not isinstance(usf, dict):
        return {}
    return copy.deepcopy(usf)


def serialize_usf(result: dict[str, Any]) -> str:
    """
    Serialize USF from result to deterministic JSON string.
    Uses sphere.usf.serialize_usf_to_json. Same USF always produces same string.
    """
    from sphere.usf import serialize_usf_to_json
    usf = get_usf(result)
    if not usf or "_usf_error" in usf:
        return "{}"
    return serialize_usf_to_json(usf)


def save_usf(result: dict[str, Any], path: str | Path) -> None:
    """
    Write USF from result to file as UTF-8 JSON. Deterministic; no extra metadata.
    """
    from sphere.usf import save_usf_json
    usf = get_usf(result)
    if not usf or "_usf_error" in usf:
        Path(path).write_text("{}", encoding="utf-8")
        return
    save_usf_json(usf, path)


def compare_usf(usf_a: dict[str, Any], usf_b: dict[str, Any]) -> dict[str, Any]:
    """
    Compare two USF artifacts. Returns deterministic delta report.
    Does not mutate either USF. Uses sphere.usf.compare_usf.
    Output: same_schema_version, metric_deltas, dominant_changes, logic_changes (and vector_deltas).
    """
    from sphere.usf import compare_usf as _compare
    if not usf_a or "_usf_error" in usf_a or not usf_b or "_usf_error" in usf_b:
        return {
            "same_schema_version": False,
            "metric_deltas": {},
            "dominant_changes": {},
            "logic_changes": {},
            "vector_deltas": {},
        }
    return _compare(usf_a, usf_b)
