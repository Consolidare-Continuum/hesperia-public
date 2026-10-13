# HESPERIA — FPF-BUII fingerprint + pin helpers.
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

from __future__ import annotations

import hashlib
import json
import re
from importlib import metadata
from pathlib import Path
from typing import Any

from sphere.fpf_inspect.constants import FPF_PIN_EXPECTED


def stable_json_hash(payload: Any) -> str:
    """Deterministic SHA-256 of canonical JSON."""
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def engine_fingerprint(analyze_result: dict[str, Any] | None) -> str:
    """Hash of analyze_result keys that identify the sealed measurement (not LLM prose)."""
    if not analyze_result:
        return stable_json_hash({"empty": True})
    keys = (
        "document_id",
        "pipeline_metadata",
        "shadow_metrics",
        "logic_metrics",
        "interpretation_metrics",
        "dynamism_metrics",
        "layer_4",
        "l4_metrics",
        "layer_5",
        "l5_metrics",
        "layer_6",
        "l6_metrics",
        "layer_7",
        "l7_metrics",
        "guards",
        "gtp",
    )
    subset = {k: analyze_result[k] for k in keys if k in analyze_result}
    return stable_json_hash(subset)


def resolve_fpf_pin(repo_root: Path | None = None) -> str:
    """Installed package version, falling back to requirements pin text."""
    try:
        ver = metadata.version("fpf-thinking-map")
        return f"fpf-thinking-map=={ver}"
    except metadata.PackageNotFoundError:
        pass
    root = repo_root or Path(__file__).resolve().parents[2]
    for rel in ("requirements/calibration.txt", "requirements/router.txt"):
        path = root / rel
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        m = re.search(r"fpf-thinking-map==([0-9.]+)", text)
        if m:
            return f"fpf-thinking-map=={m.group(1)}"
    return FPF_PIN_EXPECTED


def pin_matches_expected(pin: str | None = None) -> bool:
    pin = pin or resolve_fpf_pin()
    return pin.strip() == FPF_PIN_EXPECTED
