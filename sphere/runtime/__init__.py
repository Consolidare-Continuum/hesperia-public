# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""Runtime guards: topology integrity and startup checks."""
from sphere.runtime.guards import (
    TopologyIntegrityError,
    validate_topology_at_startup,
)

__all__ = [
    "TopologyIntegrityError",
    "validate_topology_at_startup",
]
