# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# See LEGAL_NOTICE.md for full terms.

"""
Single public projection gate for product/runtime surfaces.

All shipped JSON (API, CLI, public artifacts) MUST pass internal payloads through
``project_to_public`` — do not call ``core.projection.apply_public_projection`` directly
from product code; the engine package is the auditable choke point.

Product-facing contradiction / propagation / density / innovation scalars must arrive already
hex-derived (see ``core.engine.product_signals``); this layer must not recompute them from
family or area vectors alone.
"""

from __future__ import annotations

from typing import Any


def project_to_public(
    internal_state: dict[str, Any],
    *,
    validate_schema: bool = True,
) -> dict[str, Any]:
    """
    Transform internal pipeline state into a public-safe dict.

    Delegates sanitization to ``core.projection.apply_public_projection`` (topology / vocabulary).
    When ``validate_schema`` is True, runs the runtime public key guard (forbidden internal terms).
    """
    from core.projection import apply_public_projection

    out = apply_public_projection(internal_state)
    if validate_schema:
        from core.engine.projection.schema_enforcer import enforce_public_schema

        enforce_public_schema(out)
    return out
