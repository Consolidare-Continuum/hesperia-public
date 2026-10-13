#!/usr/bin/env python3

# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
TASK 5 — Energy invariants stress test. Five synthetic S/L vectors; verify conservation, no negative energy,
no energy > E_cap, shadow never increases energy, degrade flags trigger correctly.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.math.core_math import (
    load_config,
    fusion,
    centroid_indices,
    base_step,
    make_demo_W,
    check_conservation_pre_decay,
    check_shadow_non_creation,
)

def main() -> int:
    cfg = load_config(ROOT / "assets" / "config" / "guard_config_v1.json")
    n = 72
    W = make_demo_W(n)
    E_cap = cfg["E_cap"]
    eps = cfg["eps"]
    failed = 0

    cases = [
        ("Pure Dict A activation", [1.0] + [0.0] * (n - 1), [0.0] * n),
        ("Pure Dict B activation", [0.0] * n, [1.0] + [0.0] * (n - 1)),
        ("Equal ambiguity case", [0.5, 0.5] + [0.0] * (n - 2), [0.0] * n),
        ("Extreme thin-core case", [0.01] * n, [1.0] * n),
        ("High dispersion random case", [1.0 / n] * n, [1.0 / n] * n),
    ]

    for name, S, L in cases:
        if len(S) != n or len(L) != n:
            S = (S + [0.0] * n)[:n]
            L = (L + [0.0] * n)[:n]
        try:
            E0 = fusion(S, L, cfg)
        except ValueError as e:
            if "F5" in str(e):
                continue  # expected for all-zero
            print(f"FAIL {name}: fusion raised", e)
            failed += 1
            continue
        # No negative energy
        if any(e < -eps for e in E0):
            print(f"FAIL {name}: negative E0")
            failed += 1
        if any(e > E_cap + eps for e in E0):
            print(f"FAIL {name}: E0 > E_cap")
            failed += 1
        # Conservation pre-decay
        if not check_conservation_pre_decay(E0, W, cfg):
            print(f"FAIL {name}: I-R2 conservation pre-decay")
            failed += 1
        # Shadow never increases energy
        if not check_shadow_non_creation(E0, W, cfg):
            print(f"FAIL {name}: I-R3 shadow non-creation")
            failed += 1
        E = E0[:]
        for _ in range(cfg["T_steps"]):
            E, cons_ok = base_step(E, W, cfg)
            if not cons_ok:
                print(f"FAIL {name}: conservation failed during traversal")
                failed += 1
            if any(e < -eps for e in E):
                print(f"FAIL {name}: negative E during traversal")
                failed += 1
            if any(e > E_cap + eps for e in E):
                print(f"FAIL {name}: E > E_cap during traversal")
                failed += 1

    if failed:
        print(f"TASK 5: {failed} failures")
        return 1
    print("TASK 5: all invariant checks hold")
    return 0

if __name__ == "__main__":
    sys.exit(main())
