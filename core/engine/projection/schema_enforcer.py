# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# See LEGAL_NOTICE.md for full terms.

"""
Schema / vocabulary enforcement before any public serialization.

Implementation lives in ``core.projection.schema_guard``. This module is the engine-side façade
so product code imports projection as one package.
"""

from __future__ import annotations

from typing import Any


def enforce_public_schema(output: dict[str, Any] | list[Any]) -> None:
    """Raise ``ValueError`` if any key in the JSON tree exposes forbidden internal terms."""
    from core.projection.schema_guard import validate_public_schema_strict

    validate_public_schema_strict(output)
