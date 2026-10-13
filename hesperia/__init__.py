# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""HESPERIA package — Engine Dynamics (canonical core.domain/core.runtime + compat facades)."""

try:
    from hesperia.system.version import get_system_version

    __version__ = get_system_version()
except Exception:  # import-order / packaging without VERSION.yaml
    # Emergency fallback only; package metadata should normally resolve VERSION.yaml.
    __version__ = "0.6.5"
