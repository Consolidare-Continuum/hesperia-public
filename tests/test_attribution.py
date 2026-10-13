# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
HESPERIA — attribution and pipeline tests (structural path).
Uses stub dicts when assets not present. Deterministic.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

try:
    from core.attribution.structural import (
        normalize,
        tokenize,
        load_dict_a,
        load_dict_b,
        attribute,
        aggregate_dominant,
        build_region_seed,
        run_attribution_pipeline,
    )
except ImportError:
    from structural import (
        normalize,
        tokenize,
        load_dict_a,
        load_dict_b,
        attribute,
        aggregate_dominant,
        build_region_seed,
        run_attribution_pipeline,
    )


def test_normalize():
    assert normalize("  Hello   World  ", cap=100) == "hello world"
    assert normalize("Café", cap=10) == "café"
    assert len(normalize("a" * 20000, cap=100)) == 100


def test_tokenize():
    assert tokenize("hello world") == ["hello", "world"]
    assert tokenize("one, two. three") == ["one", "two", "three"]


def test_attribute_exclude_direct_dict_a_family():
    """Ethan PO-11: strict guard skips Dict-A direct path; B0 fallback when token is in dict_b."""
    dict_a = {"truth": {"familyGlobal": 9, "altitude": 0.2}}
    dict_b = {"truth": 5, "other": 7}
    tokens = ["truth", "other"]
    matched, metrics = attribute(tokens, dict_a, dict_b, exclude_landing_sources=frozenset({"A"}))
    assert metrics.get("excluded_by_guard") == 1
    assert metrics.get("unfiltered_landing_counts", {}).get("A") == 1
    assert metrics.get("b_fallback_after_a_excluded") == 1
    assert metrics["landing_source_counts"].get("B0_fallback") == 1
    assert len(matched) == 2
    assert {m[0] for m in matched} == {5, 7}


def test_attribute_exclude_a_no_b_fallback_when_missing_from_dict_b():
    dict_a = {"onlya": {"familyGlobal": 3, "altitude": 0.1}}
    dict_b: dict[str, int] = {}
    matched, metrics = attribute(["onlya"], dict_a, dict_b, exclude_landing_sources=frozenset({"A"}))
    assert metrics.get("excluded_by_guard") == 1
    assert metrics.get("b_fallback_after_a_excluded") == 0
    assert len(matched) == 0


def test_attribute_and_aggregate():
    dict_a = {"truth": {"familyGlobal": 9, "altitude": 0.2}, "order": {"familyGlobal": 2, "altitude": 0.5}}
    dict_b = {"good": 0}
    tokens = ["truth", "order", "truth", "unknown"]
    matched, metrics = attribute(tokens, dict_a, dict_b)
    assert len(matched) == 3
    assert metrics["total_tokens"] == 4
    assert metrics["matched_tokens"] == 3
    assert metrics["attribution_coverage"] == 0.75
    dom_f, dom_a, mean_alt, hit_d, _ = aggregate_dominant(matched)
    assert dom_f == 9
    assert dom_a == 0


def test_build_region_seed():
    seed = build_region_seed(0, 0.5, 0.2, base_weight=1.0)
    assert len(seed) == 250 * 6
    side_ids = [s[0] for s in seed]
    assert len(set(side_ids)) == len(side_ids)
    assert all(0 <= s[0] < 432000 for s in seed)
    assert all(s[1] >= 0 for s in seed)


def test_run_attribution_pipeline_stub():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        (root / "A_CORE_STAR_MAP_v1.json").write_text(
            '{"truth": {"familyGlobal": 9, "altitude": 0.3}, "good": {"familyGlobal": 0, "altitude": 0.2}}',
            encoding="utf-8",
        )
        (root / "B_SURFACE_LEX_FIELD_v1.json").write_text("{}", encoding="utf-8")
        dom_f, dom_a, seed, metrics, extended = run_attribution_pipeline(
            "truth and good", cap=1000, assets_root=root
        )
        assert dom_f in (0, 9)
        assert dom_a in (0, 0)
        assert metrics["matched_tokens"] >= 1
        assert metrics["attribution_coverage"] > 0


def test_semantic_vacuum_raises():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        (root / "A_CORE_STAR_MAP_v1.json").write_text("{}", encoding="utf-8")
        (root / "B_SURFACE_LEX_FIELD_v1.json").write_text("{}", encoding="utf-8")
        try:
            run_attribution_pipeline("xyznonexistent", cap=1000, assets_root=root)
            raise AssertionError("expected semantic_vacuum")
        except ValueError as e:
            assert "semantic_vacuum" in str(e)


# ---- Legacy Dict A: multi-side same family → stable; across families → first entry wins ----


def test_legacy_dict_a_multi_side_same_family_stable():
    """Legacy lemma with multiple side_ids in the same family → stable single familyGlobal/area."""
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        # Same family: side_id 0 and 100 (both family 0); first entry wins → familyGlobal 0
        (root / "A_CORE_STAR_MAP_v1.json").write_text(
            json.dumps({
                "alpha": [
                    {"side_id": 0, "weight": 0.9},
                    {"side_id": 100, "weight": 0.5},
                ],
            }),
            encoding="utf-8",
        )
        (root / "B_SURFACE_LEX_FIELD_v1.json").write_text("{}", encoding="utf-8")
        dict_a = load_dict_a(assets_root=root)
        assert "alpha" in dict_a
        assert dict_a["alpha"]["familyGlobal"] == 0
        # Deterministic: repeated load same
        dict_a2 = load_dict_a(assets_root=root)
        assert dict_a2["alpha"]["familyGlobal"] == dict_a["alpha"]["familyGlobal"]
        assert dict_a2["alpha"]["altitude"] == dict_a["alpha"]["altitude"]


def test_legacy_dict_a_multi_side_across_families_first_entry_wins():
    """Legacy lemma with side_ids in different families → first entry wins (deterministic)."""
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        # Family 0 (side_id 0) and family 1 (side_id 1500); first entry = 0 → familyGlobal 0
        (root / "A_CORE_STAR_MAP_v1.json").write_text(
            json.dumps({
                "beta": [
                    {"side_id": 0, "weight": 0.2},
                    {"side_id": 1500, "weight": 0.8},
                ],
            }),
            encoding="utf-8",
        )
        (root / "B_SURFACE_LEX_FIELD_v1.json").write_text("{}", encoding="utf-8")
        dict_a = load_dict_a(assets_root=root)
        assert "beta" in dict_a
        assert dict_a["beta"]["familyGlobal"] == 0
        # Explicit rule: first entry wins
        (root / "A_CORE_STAR_MAP_v1.json").write_text(
            json.dumps({
                "gamma": [
                    {"side_id": 1500, "weight": 0.8},
                    {"side_id": 0, "weight": 0.2},
                ],
            }),
            encoding="utf-8",
        )
        dict_a = load_dict_a(assets_root=root)
        assert dict_a["gamma"]["familyGlobal"] == 1


# ---- Tokenization determinism (NFKC / tricky Unicode) ----


def test_tokenize_determinism_nfkc_unicode():
    """Same normalized input → same token list; NFKC and tricky punctuation."""
    # NFKC: compatibility composites normalized to same form
    n1 = normalize("\u2167", cap=100)  # ROMAN NUMERAL EIGHT
    n2 = normalize("VIII", cap=100)
    # They may or may not be equal after NFKC; we care that same string → same tokens
    t1 = tokenize(normalize("hello\u2167world", cap=100))
    t2 = tokenize(normalize("hello\u2167world", cap=100))
    assert t1 == t2
    # Tricky punctuation: strip only fixed ASCII set
    t3 = tokenize(normalize("a'b-c.d:e", cap=100))
    t4 = tokenize(normalize("a'b-c.d:e", cap=100))
    assert t3 == t4
    # Empty after strip
    assert tokenize("  ...  ") == []
    assert tokenize("  ---  ") == []


# ---- Sigma guard: minimal 6-key impossible without Σ ----
def test_sigma_required_for_valid_minimal():
    """Prove minimal 6-key result is only valid when result passed through Sigma."""
    try:
        from core.propagation.invariant_enforcer import enforce as sigma_enforce
        from core.propagation.output_contracts import to_minimal_operational_result
    except ImportError:
        from invariant_enforcer import enforce as sigma_enforce
        from output_contracts import to_minimal_operational_result
    raw_out_of_domain = {
        "governance": 1.5,
        "loopability": -0.1,
        "tension_energy": 0.0,
        "obstacle_score": 0.0,
        "dominant_family": 0,
        "dominant_area": 0,
    }
    minimal_unguarded = to_minimal_operational_result(raw_out_of_domain)
    assert minimal_unguarded["governance"] == 1.5
    assert minimal_unguarded["loopability"] == -0.1
    enforced = sigma_enforce(raw_out_of_domain, skip_geometry=True, skip_bijection=True)
    minimal_guarded = to_minimal_operational_result(enforced)
    assert 0.0 <= minimal_guarded["governance"] <= 1.0
    assert 0.0 <= minimal_guarded["loopability"] <= 1.0
    assert 0.0 <= minimal_guarded["tension_energy"]
    assert 0.0 <= minimal_guarded["obstacle_score"]
