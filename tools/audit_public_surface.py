#!/usr/bin/env python3
# HESPERIA — Task 6 Phase 4.10: product boundary sanity (endpoints + projection + leak sample).
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
#
# Usage: python3 tools/audit_public_surface.py

from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]

ALLOWED = frozenset(
    {
        "GET /health",
        "POST /analyze",
        "POST /compare",
        "POST /batch",
        "POST /batch-analyze",
    }
)


def main() -> int:
    sys.path.insert(0, str(_REPO))
    from runtime.shipping.api_main import create_app
    from runtime.shipping.schema_guard import validate_against_public_schema
    from runtime.services.analysis_service import run_structural_analysis

    app = create_app()
    routes: list[str] = []
    for route in app.routes:
        p = getattr(route, "path", None)
        methods = getattr(route, "methods", None) or set()
        if p and methods:
            for m in sorted(methods - {"HEAD"}):
                routes.append(f"{m} {p}")
    bad = [r for r in sorted(set(routes)) if r not in ALLOWED]

    svc = (_REPO / "runtime" / "services" / "analysis_service.py").read_text(encoding="utf-8")
    proj_ok = "project_to_public" in svc and "core.engine.projection" in svc

    assets = _REPO / "assets" / "lexicon" / "curated"
    fixture = _REPO / "tests" / "fixtures" / "release_v0_5_0" / "canonical_input.txt"
    text = fixture.read_text(encoding="utf-8").strip() if fixture.is_file() else "x"
    out = run_structural_analysis(text, assets_root=assets, stages="full")
    leak_ok = True
    try:
        validate_against_public_schema(out)
    except ValueError as e:
        leak_ok = False
        leak_err = str(e)
    else:
        leak_err = None

    report = {
        "shipping_routes": sorted(set(routes)),
        "endpoint_violations": bad,
        "projection_in_analysis_service": proj_ok,
        "sample_output_schema_guard": "pass" if leak_ok else "fail",
        "sample_output_error": leak_err,
        "pass": not bad and proj_ok and leak_ok,
    }
    print(json.dumps(report, indent=2))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
