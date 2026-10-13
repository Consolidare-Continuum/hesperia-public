# HESPERIA — Crude guard: critical integrity tests/tools must keep key markers.
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

from __future__ import annotations

from pathlib import Path


def _repo() -> Path:
    return Path(__file__).resolve().parents[1]


def _must_contain(rel: str, *needles: str) -> None:
    p = _repo() / rel
    text = p.read_text(encoding="utf-8")
    for n in needles:
        assert n in text, f"integrity marker {n!r} missing from {rel} — risk of silent test weakening"


def test_public_output_contract_locked() -> None:
    _must_contain(
        "tests/support/public_output_contract.py",
        "assert_canonical_structural_json_contract",
        "assert_multiscale_magnitude_bounds",
        "structural_pipeline_version",
        "validate_against_public_schema",
        "hspr_index",
        "product_signals",
    )


def test_runtime_spine_trace_locked() -> None:
    _must_contain(
        "tests/test_runtime_spine_integrity.py",
        "run_sealed_multiscale_stack",
        "apply_public_projection",
        "run_pipeline",
        "exclusive path",
        "n_stack",
        "inspect.signature",
        "wiring_and_signature",
        "__dict__",
    )


def test_tool_contracts_locked_file_present() -> None:
    _must_contain(
        "tests/test_tool_contracts_locked.py",
        "_SHIPPING_ALLOWLIST_SHA256",
        "shipping_import_allowlist.yaml",
        "_is_core_projection",
    )


def test_forbidden_zone_tool_locked() -> None:
    _must_contain(
        "tools/check_forbidden_zone_imports.py",
        "research.",
        "legacy.",
        "STRICT_TREES",
    )


def test_engine_projection_boundary_tool_locked() -> None:
    _must_contain(
        "tools/check_engine_projection_boundary.py",
        "core.projection",
        "core/engine/projection/",
        "_is_core_projection",
    )
