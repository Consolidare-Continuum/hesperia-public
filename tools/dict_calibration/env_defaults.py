# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""Defaults for dict calibration until full C / CD / HC dict pipeline is wired."""

from __future__ import annotations

import os
from pathlib import Path

_WORKER_CAP = 64


def _truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes", "on")


def assert_corpus_not_legacy_research(corpus: Path | str) -> None:
    """TFP-DATA-T10: forbid legacy noone corpus path unless env set."""
    bad = "research" + "/_noone_local"
    s = str(corpus).replace("\\", "/")
    if bad in s and not _truthy("HESPERIA_LEGACY_RESEARCH_CORPUS"):
        raise ValueError(
            f"corpus path under {bad} is deprecated for dict calibration; use "
            "Class A: hesperia/modules/default/corpus/syzif  OR  "
            "Class B: hesperia/modules/tfp/data/tfp_v1/corpus/…  "
            "(or set HESPERIA_LEGACY_RESEARCH_CORPUS=1 temporarily)."
        )


def normalize_domain(domain: str) -> str:
    normalized = (domain or "core").strip().lower()
    if normalized not in {"core", "tfp"}:
        raise ValueError(f"domain must be 'core' or 'tfp', got {domain!r}")
    return normalized


def assert_domain_corpus_pairing(
    domain: str,
    corpus: Path | str | None,
    *,
    dict_b_paths: list[Path] | None = None,
) -> None:
    """
    Hard seal: CORE/default/syzif and TFP stay in separate lanes.

    - domain=core → corpus under modules/default (syzif); catalog must not be dict_b_tfp*
    - domain=tfp  → corpus under modules/tfp; never syzif/default as TFP input
    """
    d = normalize_domain(domain)

    if corpus is not None:
        s = str(corpus).replace("\\", "/")
        under_default = "modules/default/" in s or "/modules/default/" in s
        under_tfp = "modules/tfp/" in s or "/modules/tfp/" in s
        if not under_default and not under_tfp:
            raise ValueError(
                "calibration corpus must be under hesperia/modules/default "
                "or hesperia/modules/tfp"
            )
        if d == "core" and under_tfp:
            raise ValueError(
                "domain=core forbids TFP module corpus. "
                "Use hesperia/modules/default/corpus/syzif (Class A) "
                "or pass --domain tfp for Class B TFP only."
            )
        if d == "tfp" and under_default:
            raise ValueError(
                "domain=tfp forbids default/syzif corpus. "
                "Use hesperia/modules/tfp/… corpus or --domain core for Class A."
            )

    if dict_b_paths:
        paths = [str(Path(p)).replace("\\", "/").casefold() for p in dict_b_paths]
        tfp_marked = [
            path
            for path in paths
            if "/modules/tfp/" in path
            or "dict_b_tfp" in Path(path).name
            or "/engine_dynamics_v060/dict_b/" in path
        ]
        core_marked = [
            path
            for path in paths
            if "/modules/default/" in path
            or "/assets/calibration/dicts/" in path
            or "core" in Path(path).name
            or "syzif" in Path(path).name
        ]
        unclassified = [
            path
            for path in paths
            if path not in tfp_marked and path not in core_marked
        ]
        if unclassified:
            raise ValueError(
                "dict_b catalog path must identify the core/default or TFP lane "
                f"(got {unclassified})"
            )
        if d == "core" and tfp_marked:
            raise ValueError(
                "domain=core forbids TFP dict_b catalogs "
                f"(got {[Path(p).name for p in dict_b_paths]}). "
                "Use assets/calibration/dicts/v0_core_syzif_001/dict_b.jsonl."
            )
        if d == "tfp" and core_marked:
            raise ValueError(
                "domain=tfp forbids core/default dict_b catalogs "
                f"(got {[Path(p).name for p in dict_b_paths]})."
            )


def apply_dict_calib_offline_bundle() -> None:
    """
    Single switch: no OpenAI network + default 4 worker processes for local stages.

    Sets (only if unset): ``HESPERIA_CALIB_MOCK_OPENAI=1``, ``HESPERIA_DICT_CALIB_WORKERS=4``.
    """
    if _truthy("HESPERIA_DICT_CALIB_OFFLINE"):
        os.environ.setdefault("HESPERIA_CALIB_MOCK_OPENAI", "1")
        os.environ.setdefault("HESPERIA_DICT_CALIB_WORKERS", "4")


def dict_calib_worker_default() -> int:
    """
    Process pool size for anchor / links / eval / errors.

    Env: ``HESPERIA_DICT_CALIB_WORKERS`` (default **4**). Clamped to [1, 64].
    """
    raw = os.environ.get("HESPERIA_DICT_CALIB_WORKERS", "4").strip()
    try:
        w = int(raw)
    except ValueError:
        return 4
    return max(1, min(w, _WORKER_CAP))
