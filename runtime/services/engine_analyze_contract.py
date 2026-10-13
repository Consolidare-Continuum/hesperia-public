# HESPERIA — Engine /analyze contract envelope (HES-61-01 Python path).
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). See LEGAL_NOTICE.md.

"""Re-export shim — moved to sphere.router.engine_analyze_bridge 2026-07-31 (core/RAD severance:
sphere/router couldn't import this from here without violating "sphere must not import runtime").
Kept so existing runtime/tools/tests callers importing this path don't break.

Also the attach point for 24_SPEC §10.1's `meta.hesperia_metric` (HESPERIA_METRIC_EMIT=1,
in-scope per release/v0.7.0/RELEASE_SCOPE.md): sphere/router/engine_analyze_bridge.py cannot call
runtime.services.hesperia_metric_emit itself (same RAD rule), so the attach happens here, at the
runtime boundary layer these envelopes are meant for.

Optional L6 perturbation producer (HESPERIA_L6_PERTURBATION=1) attaches ``meta.layer_6``
after the sealed multiscale run — default off; does not alter the public schema snapshot.

Optional testing-params envelope (HESPERIA_TESTING_PARAMS=1) attaches ``meta.testing_params``
for LLM/agent testing loops — default off; additive; no freeze gates.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from runtime.services.hesperia_metric_emit import attach_hesperia_metric_meta
from runtime.services.l6_perturbation_producer import (
    attach_l6_using_raw,
    l6_perturbation_enabled,
)
from runtime.services.testing_params_emit import attach_testing_params_meta
from sphere.router.engine_analyze_bridge import (
    build_engine_analyze_from_raw as _build_engine_analyze_from_raw,
)
from sphere.router.engine_analyze_bridge import (
    run_engine_analyze as _run_engine_analyze,
)
from sphere.router.engine_analyze_bridge import (
    trace_content_hash,
)


def build_engine_analyze_from_raw(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return attach_testing_params_meta(
        attach_hesperia_metric_meta(_build_engine_analyze_from_raw(*args, **kwargs))
    )


def run_engine_analyze(*args: Any, **kwargs: Any) -> dict[str, Any]:
    # Default-off path: preserve prior shim (and test monkeypatches of _run_engine_analyze).
    if not l6_perturbation_enabled():
        return attach_testing_params_meta(
            attach_hesperia_metric_meta(_run_engine_analyze(*args, **kwargs))
        )

    from core.engine.multiscale_product_bridge import build_structural_internal_from_multiscale

    text = args[0] if args else kwargs.get("text")
    assets_root = args[1] if len(args) > 1 else kwargs.get("assets_root")
    overlay_hint = kwargs.get("overlay_hint")
    temp_relation_overlay = kwargs.get("temp_relation_overlay")
    policy_mode = kwargs.get("policy_mode")

    repo_root = Path(__file__).resolve().parents[2]
    assets = assets_root or repo_root / "assets" / "lexicon" / "curated"
    raw = build_structural_internal_from_multiscale(
        text,
        assets,
        policy_mode=policy_mode,
        enable_domain_metrics=False,
        document_id="engine_analyze",
    )
    envelope = _build_engine_analyze_from_raw(
        raw,
        overlay_hint=overlay_hint,
        temp_relation_overlay=temp_relation_overlay,
    )
    envelope = attach_hesperia_metric_meta(envelope)
    return attach_testing_params_meta(attach_l6_using_raw(envelope, raw))


__all__ = [
    "build_engine_analyze_from_raw",
    "run_engine_analyze",
    "trace_content_hash",
]
