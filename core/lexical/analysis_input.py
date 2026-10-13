# HESPERIA — RAD. Unified measurement text preparation (Ethan PO-01, PO-14).
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). See LEGAL_NOTICE.md.

"""Single preprocessing contract before structural multiscale + DLCR paths."""

from __future__ import annotations

import hashlib
from typing import Any


def prepare_structural_analysis_text(
    text: str,
    *,
    policy_mode: str | None = None,
) -> tuple[str, dict[str, Any]]:
    """
    Return (canonical_text, preprocess_meta) for deterministic downstream use.

    PO-01: NFKC, casefold, whitespace normalization via ``normalize_text``.

    Core has no relation to any extension/module (clinical, TFP, TRIZ, or otherwise) —
    the clinical-transcript role-folding branch that used to live here (PO-14) was removed;
    that's a clinical-domain concern, not core's.
    """
    from core.lexical.normalization import normalize_text

    raw = (text or "").strip()
    if not raw:
        return "", {"empty": True, "analysis_text_fingerprint": ""}

    n = normalize_text(raw)
    canonical = n["canonical_text"]

    fp = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:24]
    meta: dict[str, Any] = {
        "policy_mode": policy_mode or "default",
        "analysis_text_fingerprint": fp,
        "token_count": len(n["tokens"]),
        "phrase_span_count": len(n["phrase_spans"]),
        "preprocess_version": "hesperia_text_prep_v1",
    }
    return canonical, meta
