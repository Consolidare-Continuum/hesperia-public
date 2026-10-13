# HESPERIA — TFP MVP context packet tests.
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). See LEGAL_NOTICE.md.

from __future__ import annotations

from pathlib import Path

from runtime.shipping.tfp_mvp_context import build_tfp_mvp_context_packet, merge_tfp_mvp_context


def test_build_tfp_mvp_context_allowlisted_keys() -> None:
    packet = build_tfp_mvp_context_packet(repo_root=Path(__file__).resolve().parents[1])
    allowed = {
        "retrieval",
        "retrieval_context",
        "relation_context",
        "corpus_snapshot_id",
        "calculable",
        "coherence_hints",
        "observability",
        "gtp_current_hex",
        "gtp_powv_position",
        "thinking_map_outcome",
    }
    assert set(packet.keys()) <= allowed
    assert packet["corpus_snapshot_id"] == "tfp_mvp_inspector_exports_v1"
    assert packet["coherence_hints"]["structure_map"]["dict_mode"] == "full_tfp_stack"


def test_merge_preserves_caller_snapshot() -> None:
    merged = merge_tfp_mvp_context({"corpus_snapshot_id": "caller_pack", "retrieval": {"x": 1}})
    assert merged["corpus_snapshot_id"] == "caller_pack"
    assert merged["retrieval"] == {"x": 1}
