# HESPERIA — Hesperia Engine Dynamics
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

"""Canonical release label for Engine Dynamics (align with VERSION.yaml + CHANGELOG)."""

try:
    from hesperia.system.version import get_system_version

    ENGINE_DYNAMICS_VERSION = get_system_version()
except Exception:
    ENGINE_DYNAMICS_VERSION = "0.6.5"
PRODUCT_LINE = "Hesperia Engine Dynamics"
