#!/usr/bin/env python3

# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Propagation visualization: area vector heatmap. Outputs PNG.
Usage: python3 -m tools.visualization.propagation_heatmap [--out propagation_heatmap.png]
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

    # Example: 12-area vector (placeholder if no pipeline run)
    area_vector = [0.1, 0.15, 0.05, 0.2, 0.08, 0.12, 0.06, 0.1, 0.04, 0.05, 0.03, 0.02]
    v = np.array(area_vector).reshape(1, -1)
    fig, ax = plt.subplots()
    im = ax.imshow(v, cmap="YlOrRd", aspect="auto", vmin=0)
    ax.set_yticks([0])
    ax.set_yticklabels(["area vector"])
    ax.set_xticks(range(12))
    ax.set_xticklabels([f"A{i}" for i in range(12)])
    plt.colorbar(im, ax=ax, label="mass")
    ax.set_title("Propagation area vector (example)")
    out = _REPO / "assets" / "artifacts" / "propagation_heatmap.png"
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
