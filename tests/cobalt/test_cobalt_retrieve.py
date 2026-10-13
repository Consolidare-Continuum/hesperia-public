# COBALT retrieval tests (mock CHROMA-2).

from __future__ import annotations

from unittest.mock import patch

from runtime.cobalt.flags import cobalt_enabled
from runtime.cobalt.retrieve import cobalt_to_retrieval_context, compose_and_retrieve


def test_compose_and_retrieve_mock_chroma() -> None:
    fake_hits = [
        {
            "rank": 1,
            "doc_id": "doc-1",
            "doc_name": "tfp_paper.pdf",
            "title": "TFP",
            "creator": "test",
            "chunk_index": 0,
            "excerpt": "reflective process",
            "distance": 0.12,
            "concept_id": None,
            "area_name": None,
            "family_name": None,
            "citation": "tfp_paper.pdf#0",
        }
    ]
    with patch("runtime.cobalt.retrieve.query_chroma2", return_value=(fake_hits, "ok")):
        pkt = compose_and_retrieve("TFP clinical query", strategy="S0")
    assert pkt["version"] == "0.1-mvp"
    assert pkt["chroma2_status"] == "ok"
    assert len(pkt["hits"]) == 1
    ctx = cobalt_to_retrieval_context(pkt)
    assert len(ctx["chunks"]) == 1
    assert ctx["chunks"][0]["source"] == "CHROMA-2"


def test_cobalt_disabled_by_default() -> None:
    with patch.dict("os.environ", {}, clear=False):
        import os

        os.environ.pop("HESPERIA_COBALT_ENABLED", None)
        assert cobalt_enabled() is False


def test_analyze_adapter_cobalt_off() -> None:
    from runtime.irc_teacher.analyze_adapter import HybridRetrieveInput, retrieve

    with patch.dict("os.environ", {"HESPERIA_COBALT_ENABLED": "0"}):
        out = retrieve(HybridRetrieveInput(query="smoke"))
    assert out.cobalt_retrieval is None
