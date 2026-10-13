#!/usr/bin/env python3

# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Topology visualization: area adjacency graph. Outputs PNG.
Usage: python3 -m tools.visualization.topology_map [--out topology_map.png]
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def main() -> int:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        print("matplotlib required: pip install matplotlib", file=sys.stderr)
        return 1

    from sphere.topology import load_area_adjacency

    adj = load_area_adjacency()
    n = adj.shape[0]
    fig, ax = plt.subplots()
    ax.imshow(adj, cmap="Blues", vmin=0, vmax=1)
    for i in range(n):
        for j in range(n):
            if adj[i, j]:
                ax.text(j, i, "1", ha="center", va="center", fontsize=8)
    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_title("Area adjacency (12x12)")
    out = _REPO / "assets" / "artifacts" / "topology_map.png"
    if "--out" in sys.argv:
        idx = sys.argv.index("--out")
        if idx + 1 < len(sys.argv):
            out = Path(sys.argv[idx + 1])
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=100, bbox_inches="tight")
    plt.close()
    print(out.resolve(), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
