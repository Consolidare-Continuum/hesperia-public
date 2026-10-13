# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Reading Scale Engine tests.
Deterministic segmentation R1–R4 and multiscale dossier with topology_summary.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from runtime.pipeline.reading_scales import (
    segment_r1_sentences,
    segment_r2_paragraphs,
    segment_r3_sections,
    segment_r4_document,
    run_multiscale,
)


def test_segment_r1_sentences() -> None:
    """R1: sentences by punctuation."""
    assert segment_r1_sentences("One. Two! Three?") == ["One", "Two", "Three"]
    assert segment_r1_sentences("") == []
    assert segment_r1_sentences("Single") == ["Single"]


def test_segment_r2_paragraphs() -> None:
    """R2: paragraphs by blank lines."""
    assert segment_r2_paragraphs("A\n\nB") == ["A", "B"]
    assert segment_r2_paragraphs("Only one") == ["Only one"]
    assert segment_r2_paragraphs("") == []


def test_segment_r4_document() -> None:
    """R4: full document as one segment."""
    assert segment_r4_document("Full doc.") == ["Full doc."]
    assert segment_r4_document("") == []


def test_run_multiscale_dossier_shape() -> None:
    """run_multiscale returns R1, R2, R3, R4 and topology_summary."""
    text = "Justice. Fairness. Order."
    dossier = run_multiscale(text, assets_root=_REPO / "assets" / "lexicon" / "curated")
    assert "R1" in dossier and "R2" in dossier and "R3" in dossier and "R4" in dossier
    assert "topology_summary" in dossier
    g = dossier["topology_summary"]
    assert "dominant_area_distribution" in g
    assert "stable_family_core" in g
    assert "tension_axes" in g
    assert "confidence_profile" in g
    assert "document_anomaly" in g


def test_run_multiscale_r1_entries_full_pipeline() -> None:
    """Each R1 entry contains full pipeline output (L1–L9, diagnostics)."""
    text = "First. Second."
    dossier = run_multiscale(text, assets_root=_REPO / "assets" / "lexicon" / "curated")
    r1 = dossier["R1"]
    assert len(r1) == 2
    for entry in r1:
        for layer in ("L1", "L7", "L9"):
            assert layer in entry
        assert "diagnostics" in entry
        assert "consistency_profile" in entry.get("diagnostics", {})


def test_document_anomaly_mean_of_stability_scores() -> None:
    """document_anomaly is mean of segment Δ stability layer anomaly_score."""
    text = "A. B. C."
    dossier = run_multiscale(text, assets_root=_REPO / "assets" / "lexicon" / "curated")
    g = dossier["topology_summary"]
    scores = [
        dossier["R1"][i].get("diagnostics", {}).get("consistency_profile", {}).get("anomaly_score", 0.0)
        for i in range(len(dossier["R1"]))
    ]
    if scores:
        expected = sum(scores) / len(scores)
        assert abs(g["document_anomaly"] - expected) < 1e-5
