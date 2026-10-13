# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

# Layer-7 propagation: topology-driven diffusion and family projection.
# Behavior only; math in core/math. Topology from sphere/topology.

from sphere.propagation.engine import compute_propagation

__all__ = ["compute_propagation"]
