# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# See LEGAL_NOTICE.md for full terms.

"""Re-export trace sanitizer from core for a single projection import path."""

from __future__ import annotations

from typing import Any

from core.projection.public_projection_layer import sanitize_public_trace

__all__ = ["sanitize_public_trace"]


def sanitize_trace(trace: dict[str, Any] | list[Any]) -> dict[str, Any] | list[Any]:
    """Alias for :func:`sanitize_public_trace`."""
    return sanitize_public_trace(trace)
