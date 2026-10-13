# HESPERIA — Enforce canonical runtime spine (imports + minimal integration).
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

from __future__ import annotations

import inspect
from pathlib import Path

import pytest


def _repo() -> Path:
    return Path(__file__).resolve().parents[1]


def _assets() -> Path:
    return _repo() / "assets" / "lexicon" / "curated"


@pytest.mark.skipif(not _assets().is_dir(), reason="lexicon/curated missing")
def test_spine_modules_importable() -> None:
    from core.projection import apply_public_projection
    from core.engine.multiscale_product_bridge import build_structural_internal_from_multiscale
    from core.engine.projection.public_projection import project_to_public
    from core.engine.sealed_multiscale_stack import run_sealed_multiscale_stack
    from runtime.services.analysis_service import run_structural_analysis

    assert callable(run_structural_analysis)
    assert callable(build_structural_internal_from_multiscale)
    assert callable(run_sealed_multiscale_stack)
    assert callable(project_to_public)
    assert callable(apply_public_projection)


@pytest.mark.skipif(not _assets().is_dir(), reason="lexicon/curated missing")
def test_zero_marker_hits_hex_and_L1_not_silently_annihilated() -> None:
    """
    Regression (Ethan calibration pack / Task 2): uniform concept prior + microphysics must not
    clip to all-zero hex; L1 must align with sealed family mass via bridge fallback.
    """
    from core.engine.multiscale_product_bridge import build_structural_internal_from_multiscale
    from core.engine.sealed_multiscale_stack import run_sealed_multiscale_stack
    from hesperia.extensions.dynamics.e2e_bridge import markers_to_concept_activation

    text = "абвгд абвгд ежзий " * 80
    assets = _assets()
    act = markers_to_concept_activation(text, assets)
    assert sum(act["a_concept_counts"]) == 0

    sealed = run_sealed_multiscale_stack(text, assets, apply_local_step=True)
    tm = float(sealed["hex_activation_map"]["total_mass"])
    assert tm > 1e-12, "hex mass must not annihilate under diffuse prior"
    assert sealed["concept_layer"]["uniform_concept_prior_fallback_used"] is True

    raw = build_structural_internal_from_multiscale(text, assets, document_id="zero_marker_regression")
    assert int(raw["L1"]["ATTRIBUTED_TOKENS"]) > 0
    assert raw["L1"].get("CALIBRATION_FALLBACK_USED") == "sealed_family_activation_to_L1"
    cal = raw["diagnostics"]["calibration_status"]
    assert cal.get("true_absence_of_marker_signal") is True
    assert cal.get("l1_calibration_fallback") == "sealed_family_activation_to_L1"


@pytest.mark.skipif(not _assets().is_dir(), reason="lexicon/curated missing")
def test_sealed_multiscale_stack_produces_hex_activation() -> None:
    from core.engine.sealed_multiscale_stack import run_sealed_multiscale_stack

    out = run_sealed_multiscale_stack(
        "justice fairness social order",
        _assets(),
        apply_local_step=True,
        use_triz_contradiction=False,
    )
    ham = out.get("hex_activation_map")
    assert isinstance(ham, dict)
    assert "shape" in ham


@pytest.mark.skipif(not _assets().is_dir(), reason="lexicon/curated missing")
def test_product_bridge_to_projection_roundtrip() -> None:
    from core.engine.multiscale_product_bridge import build_structural_internal_from_multiscale
    from core.engine.projection.public_projection import project_to_public

    raw = build_structural_internal_from_multiscale(
        "harm conflict trust repair",
        _assets(),
        use_triz_contradiction=False,
        document_id="spine_test",
    )
    pub = project_to_public(raw, validate_schema=True)
    assert isinstance(pub, dict)
    assert "L7" in pub


@pytest.mark.skipif(not _assets().is_dir(), reason="lexicon/curated missing")
def test_analysis_service_matches_spine() -> None:
    from runtime.services.analysis_service import run_structural_analysis

    out = run_structural_analysis(
        "structure test phrase",
        assets_root=_assets(),
        stages="full",
        attach_version=True,
    )
    assert isinstance(out, dict)
    assert out.get("run") == "structural_analysis"


@pytest.mark.skipif(not _assets().is_dir(), reason="lexicon/curated missing")
def test_multiscale_bridge_stack_runner_wiring_and_signature() -> None:
    """Refactor resistance: module-level binding + canonical object + frozen parameter lists."""
    import core.engine.multiscale_product_bridge as mpb
    import core.engine.sealed_multiscale_stack as sms

    assert "run_sealed_multiscale_stack" in mpb.__dict__, (
        "bridge must bind run_sealed_multiscale_stack at module level"
    )
    assert mpb.run_sealed_multiscale_stack is sms.run_sealed_multiscale_stack, (
        "bridge must reference the canonical sealed_multiscale_stack runner"
    )
    sig = inspect.signature(mpb.run_sealed_multiscale_stack)
    assert tuple(sig.parameters.keys()) == (
        "text",
        "assets_root",
        "apply_local_step",
        "hotspot_list_cap",
        "use_triz_contradiction",
        "contradiction_package",
    )
    sig_b = inspect.signature(mpb.build_structural_internal_from_multiscale)
    assert tuple(sig_b.parameters.keys()) == (
        "text",
        "assets",
        "policy_mode",
        "enable_domain_metrics",
        "domain_constants_path",
        "use_triz_contradiction",
        "document_id",
    )


@pytest.mark.skipif(not _assets().is_dir(), reason="lexicon/curated missing")
def test_analysis_service_exclusive_path_once(monkeypatch: pytest.MonkeyPatch) -> None:
    """Detect hidden parallel preprocessing / alternate projection / sphere runner side-calls."""
    import core.projection as cp
    import core.engine.multiscale_product_bridge as mpb
    import core.engine.sealed_multiscale_stack as sms
    import sphere.pipeline.pipeline_runner as spr

    assert "run_sealed_multiscale_stack" in mpb.__dict__
    assert mpb.run_sealed_multiscale_stack is sms.run_sealed_multiscale_stack

    n_stack = {"n": 0}
    n_proj = {"n": 0}
    n_sphere = {"n": 0}

    # Bridge binds run_sealed_multiscale_stack at import time; patch the bridge global, not sms.
    orig_stack = mpb.run_sealed_multiscale_stack
    orig_proj = cp.apply_public_projection
    orig_sphere = spr.run_pipeline

    def wrap_stack(*a, **kw):
        n_stack["n"] += 1
        return orig_stack(*a, **kw)

    def wrap_proj(*a, **kw):
        n_proj["n"] += 1
        return orig_proj(*a, **kw)

    def wrap_sphere(*a, **kw):
        n_sphere["n"] += 1
        return orig_sphere(*a, **kw)

    monkeypatch.setattr(mpb, "run_sealed_multiscale_stack", wrap_stack)
    monkeypatch.setattr(cp, "apply_public_projection", wrap_proj)
    monkeypatch.setattr(spr, "run_pipeline", wrap_sphere)

    from runtime.services.analysis_service import run_structural_analysis

    run_structural_analysis(
        "exclusive path spine check",
        assets_root=_assets(),
        stages="full",
        attach_version=True,
    )

    assert n_stack["n"] == 1, "multiscale bridge must invoke run_sealed_multiscale_stack exactly once"
    assert n_proj["n"] == 1, "apply_public_projection must be invoked exactly once (via project_to_public)"
    assert n_sphere["n"] == 0, "sphere.pipeline.run_pipeline must not run on canonical product path"
