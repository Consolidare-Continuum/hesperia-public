# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""
Measurement service facade. Public runtime must not orchestrate internal math/execution_flow step by step.

**Canonical path (Engine Dynamics):** multiscale sealed stack only — Concept → Hex → Family → Area →
signals → ``project_to_public``. No sphere L1–L9 runner on the shipping path.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def _reject_legacy_profile_args(
    *,
    profile_path: Path | None,
    profile_id: str | None,
    profile: dict | None,
) -> None:
    if profile_path is not None or profile_id is not None or profile is not None:
        raise ValueError(
            "structure profiles are not supported on the canonical multiscale path; "
            "remove profile_path / profile_id / profile. "
            "Legacy sphere layer orchestration is dev-only (HESPERIA_SPHERE_PIPELINE_DEV=1)."
        )


def run_structural_analysis(
    text: str,
    assets_root: Path | None = None,
    calibration_profile_id: str | None = None,
    report_profile_id: str | None = None,
    policy_mode: str | None = None,
    profile_path: Path | None = None,
    profile_id: str | None = None,
    profile: dict | None = None,
    stages: str = "full",
    enable_domain_metrics: bool = False,
    domain_constants_path: str | Path | None = None,
    attach_version: bool = True,
) -> dict[str, Any]:
    """
    Run structural measurement on text. Returns public-safe SUMMARY/DIAGNOSTICS output only (projected).

    stages: only ``\"full\"`` is supported (canonical multiscale stack). Reduced L1–L3-only paths
    were removed — they bypassed the hex layer.

    Profile-based sphere orchestration is rejected; use the sealed multiscale engine only.

    attach_version: when False, skip VERSION.yaml envelope (for rows embedded in a parent E2E artifact).
    """
    from core.engine.projection import project_to_public
    from core.engine.multiscale_product_bridge import build_structural_internal_from_multiscale

    if stages != "full":
        raise ValueError(
            f'unsupported stages={stages!r}; only "full" (canonical multiscale with hex layer) is allowed.'
        )
    _reject_legacy_profile_args(profile_path=profile_path, profile_id=profile_id, profile=profile)

    repo_root = Path(__file__).resolve().parents[2]
    assets = assets_root or repo_root / "assets" / "lexicon" / "curated"
    raw = build_structural_internal_from_multiscale(
        text,
        assets,
        policy_mode=policy_mode,
        enable_domain_metrics=enable_domain_metrics,
        domain_constants_path=domain_constants_path,
        use_triz_contradiction=False,
        document_id="analysis_service",
    )
    out = project_to_public(raw, validate_schema=True)

    from hesperia.system.capabilities import structural_dlcr_allowed

    if structural_dlcr_allowed():
        from core.engine.lexical_concept.pipeline import run_dlcr_pipeline
        from core.engine.projection.dlcr_public import project_dlcr_public_summary

        dlcr_bundle = run_dlcr_pipeline(text, repo_root=repo_root)
        lr = project_dlcr_public_summary(dlcr_bundle)
        pl = out.get("payload")
        if isinstance(pl, dict):
            merged = dict(pl)
            merged["lexical_resolution"] = lr
            out["payload"] = merged
        else:
            out["payload"] = {"lexical_resolution": lr}
        from core.engine.projection.schema_enforcer import enforce_public_schema

        enforce_public_schema(out)

    if not attach_version:
        return out
    from hesperia.system.version import attach_public_output_metadata, default_calibration_profile, structural_pipeline_version

    prof = calibration_profile_id
    if prof is None:
        prof = default_calibration_profile()
    return attach_public_output_metadata(
        out,
        calibration_profile=prof,
        pipeline_version=structural_pipeline_version(),
        execution_flow_version=structural_pipeline_version(),
        orchestration_mode="SERVICE_SYNC",
    )


def run_structural_analysis_batch(
    texts: list[str],
    assets_root: Path | None = None,
    policy_mode: str | None = None,
    attach_version: bool = True,
) -> list[dict[str, Any]]:
    """Run canonical multiscale analysis on each text. Returns projected public-safe rows."""
    from core.engine.multiscale_product_bridge import build_structural_internal_from_multiscale
    from core.engine.projection import project_to_public

    assets = assets_root or Path(__file__).resolve().parents[2] / "assets" / "lexicon" / "curated"
    results: list[dict[str, Any]] = []
    for i, text in enumerate(texts):
        raw = build_structural_internal_from_multiscale(
            text,
            assets,
            policy_mode=policy_mode,
            enable_domain_metrics=False,
            domain_constants_path=None,
            use_triz_contradiction=False,
            document_id=f"batch_{i}",
        )
        proj = project_to_public(raw, validate_schema=True)
        if attach_version:
            from hesperia.system.version import attach_public_output_metadata, default_calibration_profile, structural_pipeline_version

            results.append(
                attach_public_output_metadata(
                    proj,
                    calibration_profile=default_calibration_profile(),
                    pipeline_version=structural_pipeline_version(),
                    execution_flow_version=structural_pipeline_version(),
                    orchestration_mode="SERVICE_BATCH",
                )
            )
        else:
            results.append(proj)
    return results
