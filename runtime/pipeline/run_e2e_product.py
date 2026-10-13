#!/usr/bin/env python3
# HESPERIA — Product E2E (Task 4): RAW_TEXT -> analysis_service -> projection (inside service) -> schema guard.
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). See LEGAL_NOTICE.md.
#
# Internal / full repo E2E remains: python3 -m runtime.pipeline.run_e2e_all
# This component is the minimal auditable product proof (no TRIZ, clinical, research, field calibration grid).

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

_DEFAULT_TEXT = os.environ.get("HESPERIA_PRODUCT_E2E_TEXT", "тест структурного анализа").strip() or "x"
_OUT = Path(os.environ.get("HESPERIA_PRODUCT_E2E_OUT", str(_REPO / "assets/artifacts/e2e/run_output_e2e_product_surface.json")))


def main() -> int:
    from runtime.services.analysis_service import run_structural_analysis
    from runtime.shipping.schema_guard import validate_against_public_schema

    assets = _REPO / "assets" / "lexicon" / "curated"
    summary_payload = run_structural_analysis(_DEFAULT_TEXT, assets_root=assets, stages="full")
    validate_against_public_schema(summary_payload)
    _OUT.parent.mkdir(parents=True, exist_ok=True)
    _OUT.write_text(json.dumps(summary_payload, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    print(f"product_e2e_ok wrote {_OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
