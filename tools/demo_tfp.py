#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from hesperia.product.service import run_product_profile


def main() -> int:
    ap = argparse.ArgumentParser(description="Demo TFP decision.")
    ap.add_argument("text")
    args = ap.parse_args()
    out = run_product_profile(args.text, "tfp_analysis")
    print(json.dumps(out, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

