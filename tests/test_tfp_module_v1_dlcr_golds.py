# HESPERIA — TFP-V1-04: hash-locked DLCR pipeline gold subset (no research/).
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from core.engine.lexical_concept.pipeline import run_dlcr_pipeline

REPO = Path(__file__).resolve().parents[1]

# SHA256 of canonical JSON blob (see _digest_blob); bump when dict pack or pipeline semantics change intentionally.
_GOLDS: dict[str, str] = {
    "tfp v1 gold probe alpha": "449bce0c38e98082125218d0a786924c593517368c1a50b7b58940c4425c4263",
    "примитивное расщепление в терапии": "38dd31221b4ead856bb10ea4059a14d79e288d46d9e7dcf0a75ef3a87457a577",
    "anxiety structure boundary test": "21a2a860b835a2e1f4f32642e1de572ad071723d4248d69f2a1e084503a9909a",
    "control trust identity aggression": "8213ca08c80114c4c0fd43335be1785d714c612f02bbfac9f2751c7c2c5e4b06",
    "minimal": "00ed3557efd3db7fa3dcd1f26ac994f121e11798cb5998d9dc1ffebcc159f1eb",
}


def _digest_blob(out: dict) -> str:
    aa = {k: round(float(v), 6) for k, v in sorted((out.get("area_activation") or {}).items())}
    fa = {k: round(float(v), 6) for k, v in sorted((out.get("family_activation") or {}).items())}
    dom = max(aa, key=aa.get) if aa else None
    blob = {
        "canonical_text": out.get("canonical_text"),
        "lexical_hits_accepted": out.get("lexical_hits_accepted"),
        "lexical_hits_rejected": out.get("lexical_hits_rejected"),
        "dominant_area": dom,
        "area_activation": aa,
        "family_activation": fa,
    }
    raw = json.dumps(blob, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def test_dlcr_pipeline_v1_gold_digests() -> None:
    for text, expected in _GOLDS.items():
        out = run_dlcr_pipeline(text, repo_root=REPO, mode="clinical_speech")
        got = _digest_blob(out)
        assert got == expected, f"gold drift for {text!r}: {got} != {expected}"
