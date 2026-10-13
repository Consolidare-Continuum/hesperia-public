#!/usr/bin/env python3

# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Structural state visualization: entropy / tension example plot. Outputs PNG.
Usage: python3 -m tools.visualization.structural_state_plot [--out structural_state_plot.png]
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

    # Example series (placeholder)
    steps = list(range(5))
    entropy = [0.3, 0.35, 0.32, 0.38, 0.34]
    tension = [0.2, 0.25, 0.28, 0.22, 0.26]
    fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True)
    ax1.plot(steps, entropy, "o-", label="entropy")
    ax1.set_ylabel("entropy")
    ax1.legend()
    ax1.set_title("Structural state (example)")
    ax2.plot(steps, tension, "s-", label="tension")
    ax2.set_ylabel("tension")
    ax2.set_xlabel("step")
    ax2.legend()
    out = _REPO / "assets" / "artifacts" / "structural_state_plot.png"
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
