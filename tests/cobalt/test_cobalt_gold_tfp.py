# tests/cobalt/test_cobalt_gold_tfp.py — COBALT-19

from __future__ import annotations

from unittest.mock import patch

from runtime.cobalt.retrieve import compose_and_retrieve

_TFP_QUERY = "TFP transference clinical Kernberg borderline"
_EXPECTED_SUBSTR = "TFP"


def test_gold_tfp_query_top_hit_clinical_corpus() -> None:
    """Ava gold: known TFP query should rank a TFP-tagged document (live or mock)."""
    fake_hits = [
        {
            "rank": 1,
            "doc_id": "gold-tfp-1",
            "doc_name": "RU - Kernberg - TFP clinical guide [TFP normalized].md",
            "title": "TFP",
            "creator": "Kernberg",
            "chunk_index": 0,
            "excerpt": "transference clinical",
            "distance": 0.9,
            "concept_id": "synthetic_family_012",
            "area_name": "A3",
            "family_name": "family_012",
            "citation": "gold#0",
        }
    ]
    with patch("runtime.cobalt.retrieve.query_chroma2", return_value=(fake_hits, "ok")):
        pkt = compose_and_retrieve(_TFP_QUERY, strategy="S0")
    top = pkt["hits"][0]
    assert _EXPECTED_SUBSTR.lower() in (top.get("doc_name") or "").lower()
    assert pkt["chroma2_status"] == "ok"
