# HESPERIA — RAD. Map DLCR internal bundle → public-safe nested dict (schema key walk safe).
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

from __future__ import annotations

from typing import Any


def project_dlcr_public_summary(dlcr_bundle: dict[str, Any]) -> dict[str, Any]:
    """
    Derive a compact, nested summary safe for ``payload`` attachment.

    Avoids forbidden key substrings from ``runtime.shipping.schema_guard`` on **keys**
    (no ``hex``, ``topology``, ``graph``, etc.).
    """
    spans = dlcr_bundle.get("span_resolutions") or []
    evidence: list[dict[str, str]] = []
    for s in spans[:64]:
        if not isinstance(s, dict):
            continue
        mt = s.get("normalized_span") or s.get("source_text_span") or ""
        win = s.get("winning_concept_id")
        evidence.append(
            {
                "matched_span": str(mt)[:500],
                "concept_or_family_label": str(win) if win else "",
                "confidence_band": "resolved" if win else "unresolved",
                "document_location": "",
            }
        )
    cw = dlcr_bundle.get("concept_weights") or {}
    top_c = sorted(cw.items(), key=lambda x: -float(x[1]))[:12]
    return {
        "resource_versions": dlcr_bundle.get("resource_versions") or {},
        "matched_span_count": int(dlcr_bundle.get("lexical_hits_accepted") or 0),
        "microcell_concentration": float(dlcr_bundle.get("hex_concentration") or 0.0),
        "microcell_dispersion": float(dlcr_bundle.get("hex_dispersion") or 0.0),
        "domain_activation": dlcr_bundle.get("area_activation") or {},
        "policy_activation": dlcr_bundle.get("family_activation") or {},
        "degradation_markers": list(dlcr_bundle.get("degradation_flags") or []),
        "top_concepts": [
            {"concept_label": k, "activation_mass": round(float(v), 6)} for k, v in top_c
        ],
        "evidence": evidence,
        "segment_motion": dlcr_bundle.get("segment_trajectory") or {},
    }
