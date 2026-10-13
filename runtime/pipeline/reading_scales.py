# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""
HESPERIA Reading Scale Engine.
Run L1–L9 execution flow across multiple reading scales (R1 sentences, R2 paragraphs, R3 sections, R4 document)
and combine outputs into a multiscale dossier with global topology summary.
Deterministic segmentation: no NLP libraries.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List

from .run_l1_through_l9 import run_pipeline_for_text

def _assets_root() -> Path:
    _here = Path(__file__).resolve().parent
    return _here.parents[1] / "assets" / "lexicon" / "curated"


# ---- Deterministic segmentation (no NLP) ----

# Sentence-ending punctuation
_SENTENCE_END = re.compile(r"[.!?]+")

# Blank line (paragraph boundary)
_BLANK_LINE = re.compile(r"\n\s*\n")

# Markdown-style heading: # Title or === / --- underline
_HEADING_LINE = re.compile(r"^(#{1,6}\s+.+|\s*[-=]{2,}\s*)$", re.MULTILINE)

# Section size threshold: max paragraphs per section when no headings
SECTION_PARAGRAPH_THRESHOLD = 4


def segment_r1_sentences(text: str) -> List[str]:
    """R1: segment into sentences by punctuation . ! ?"""
    if not text or not text.strip():
        return []
    # Split on sentence-ending punctuation, keep boundaries
    parts = _SENTENCE_END.split(text)
    sentences = [s.strip() for s in parts if s.strip()]
    return sentences


def segment_r2_paragraphs(text: str) -> List[str]:
    """R2: segment into paragraphs by blank lines."""
    if not text or not text.strip():
        return []
    blocks = _BLANK_LINE.split(text)
    paragraphs = [b.strip() for b in blocks if b.strip()]
    return paragraphs if paragraphs else [text.strip()]


def segment_r3_sections(text: str) -> List[str]:
    """R3: segment into sections by headings or size threshold."""
    if not text or not text.strip():
        return []
    paragraphs = segment_r2_paragraphs(text)
    if not paragraphs:
        return [text.strip()]
    # Find heading indices: paragraph that looks like a heading (# or all-caps short line)
    heading_indices: List[int] = []
    for i, p in enumerate(paragraphs):
        first_line = p.split("\n")[0].strip()
        if first_line.startswith("#") or (len(first_line) < 80 and first_line.isupper() and len(first_line) > 1):
            heading_indices.append(i)
    # Build sections: from start to first heading, then between headings, or by SECTION_PARAGRAPH_THRESHOLD
    sections: List[str] = []
    if heading_indices:
        start = 0
        for hi in heading_indices:
            if hi > start:
                chunk = "\n\n".join(paragraphs[start:hi])
                if chunk.strip():
                    sections.append(chunk)
            start = hi
        if start < len(paragraphs):
            chunk = "\n\n".join(paragraphs[start:])
            if chunk.strip():
                sections.append(chunk)
    else:
        for i in range(0, len(paragraphs), SECTION_PARAGRAPH_THRESHOLD):
            chunk = "\n\n".join(paragraphs[i : i + SECTION_PARAGRAPH_THRESHOLD])
            if chunk.strip():
                sections.append(chunk)
    return sections if sections else ["\n\n".join(paragraphs)]


def segment_r4_document(text: str) -> List[str]:
    """R4: full document as single segment."""
    if not text or not text.strip():
        return []
    return [text.strip()]


def _run_scale(
    text: str,
    segments: List[str],
    assets_root: Path | None,
    defaults: dict | None,
    profile_id: str | None,
    profile: dict | None,
) -> List[Dict[str, Any]]:
    """Run execution_flow for each segment; return list of full execution_flow outputs."""
    results: List[Dict[str, Any]] = []
    for seg in segments:
        out = run_pipeline_for_text(
            seg,
            assets_root=assets_root,
            defaults=defaults,
            profile_id=profile_id,
            profile=profile,
        )
        results.append(out)
    return results


def _aggregate_global_structure(
    r1: List[Dict],
    r2: List[Dict],
    r3: List[Dict],
    r4: List[Dict],
) -> Dict[str, Any]:
    """Compute topology summary from all scale outputs."""
    all_outputs: List[Dict] = []
    for scale in (r1, r2, r3, r4):
        all_outputs.extend(scale)

    # dominant_area_distribution: count of DOMINANT_AREA_ID across segments
    area_counts: Dict[int, int] = {}
    for out in all_outputs:
        l1 = out.get("L1") or {}
        area = int(l1.get("DOMINANT_AREA_ID", 0))
        area_counts[area] = area_counts.get(area, 0) + 1
    total = sum(area_counts.values()) or 1
    dominant_area_profile = {
        str(k): round(v / total, 4) for k, v in sorted(area_counts.items())
    }

    # stable_family_core: families that appear as dominant in more than 25% of segments
    family_counts: Dict[int, int] = {}
    for out in all_outputs:
        l1 = out.get("L1") or {}
        fam = int(l1.get("DOMINANT_FAMILY_ID", 0))
        family_counts[fam] = family_counts.get(fam, 0) + 1
    n_seg = len(all_outputs) or 1
    stable_family_core = [
        fam for fam, count in family_counts.items()
        if count / n_seg > 0.25
    ]
    stable_family_core.sort()

    # tension_axes: distinct dominant areas (axes of variation)
    tension_axes = sorted(set(area_counts.keys()))

    # confidence_profile: profile of L7 SYSTEM_CONFIDENCE_SCORE and OUTPUT_TRUST_TAG
    confidence_scores: List[float] = []
    tag_counts: Dict[str, int] = {}
    for out in all_outputs:
        l7 = out.get("L7") or {}
        confidence_scores.append(float(l7.get("SYSTEM_CONFIDENCE_SCORE", 0.0)))
        tag = l7.get("OUTPUT_TRUST_TAG", "UNKNOWN")
        tag_counts[tag] = tag_counts.get(tag, 0) + 1
    confidence_profile = {
        "mean_confidence": round(sum(confidence_scores) / len(confidence_scores), 6) if confidence_scores else 0.0,
        "min_confidence": round(min(confidence_scores), 6) if confidence_scores else 0.0,
        "max_confidence": round(max(confidence_scores), 6) if confidence_scores else 0.0,
        "trust_tag_distribution": tag_counts,
    }

    # document_anomaly: mean of segment Δ consistency layer anomaly_score
    stability_scores: List[float] = []
    for out in all_outputs:
        diag = out.get("diagnostics") or {}
        stability = diag.get("stability") or {}
        stability_scores.append(float(stability.get("anomaly_score", 0.0)))
    document_anomaly = round(
        sum(stability_scores) / len(stability_scores), 6
    ) if stability_scores else 0.0

    return {
        "dominant_area_profile": dominant_area_profile,
        # Compatibility mirror.
        "dominant_area_distribution": dominant_area_profile,
        "stable_family_core": stable_family_core,
        "tension_axes": tension_axes,
        "confidence_profile": confidence_profile,
        "document_anomaly": document_anomaly,
    }


def run_multiscale(
    text: str,
    assets_root: Path | None = None,
    defaults: dict | None = None,
    profile_id: str | None = None,
    profile: dict | None = None,
) -> Dict[str, Any]:
    """
    Run L1–L9 execution flow at reading scales R1 (sentences), R2 (paragraphs), R3 (sections), R4 (document).
    Returns a multiscale dossier with per-scale outputs and topology_summary.
    """
    if defaults is None:
        from core.layers import load_defaults
        defaults = load_defaults()
    assets = assets_root if assets_root is not None else _assets_root()

    segments_r1 = segment_r1_sentences(text)
    segments_r2 = segment_r2_paragraphs(text)
    segments_r3 = segment_r3_sections(text)
    segments_r4 = segment_r4_document(text)

    r1 = _run_scale(text, segments_r1, assets, defaults, profile_id, profile)
    r2 = _run_scale(text, segments_r2, assets, defaults, profile_id, profile)
    r3 = _run_scale(text, segments_r3, assets, defaults, profile_id, profile)
    r4 = _run_scale(text, segments_r4, assets, defaults, profile_id, profile)

    topology_summary = _aggregate_global_structure(r1, r2, r3, r4)

    return {
        "R1": r1,
        "R2": r2,
        "R3": r3,
        "R4": r4,
        "topology_summary": topology_summary,
        # Compatibility mirror.
        "global_structure": topology_summary,
    }
