# HESPERIA — canonical version authority (VERSION.yaml).
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

from __future__ import annotations

import copy
import importlib.resources as resources
import os
import subprocess
from datetime import timezone, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _git_commit_short(root: Path) -> str | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=3,
        )
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()[:12]
    except (OSError, subprocess.SubprocessError):
        pass
    return None


def _read_version_yaml(path: Path) -> dict[str, Any]:
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise ValueError(f"VERSION.yaml must be a mapping at top level: {path}")
    return copy.deepcopy(doc)


@lru_cache(maxsize=1)
def load_version_document() -> dict[str, Any]:
    """Load VERSION.yaml and inject runtime build fields (not written back to disk)."""
    root = _repo_root()
    path = root / "VERSION.yaml"
    if path.exists():
        doc = _read_version_yaml(path)
    else:
        try:
            package_path = resources.files("hesperia").joinpath("VERSION.yaml")
            with resources.as_file(package_path) as resolved:
                if not resolved.is_file():
                    raise FileNotFoundError
                doc = _read_version_yaml(resolved)
        except FileNotFoundError as exc:
            raise FileNotFoundError(
                f"Canonical VERSION.yaml missing at {path} and packaged copy is unavailable"
            ) from exc
    build = doc.setdefault("build", {})
    env_commit = os.environ.get("HESPERIA_GIT_COMMIT", "").strip()
    env_ts = os.environ.get("HESPERIA_BUILD_TIMESTAMP", "").strip()
    env_bid = os.environ.get("HESPERIA_BUILD_ID", "").strip()
    commit = env_commit or _git_commit_short(root) or "unknown"
    ts = env_ts or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    build["git_commit"] = commit
    build["timestamp"] = ts
    if env_bid:
        build["build_id_override"] = env_bid
    return doc


def get_system_version() -> str:
    v = load_version_document().get("system_version")
    if not v:
        raise RuntimeError("VERSION.yaml missing system_version")
    return str(v)


def get_component_versions() -> dict[str, str]:
    comp = load_version_document().get("components") or {}
    return {str(k): str(v) for k, v in comp.items()}


def get_schema_versions() -> dict[str, str]:
    sch = load_version_document().get("schema") or {}
    return {str(k): str(v) for k, v in sch.items()}


def production_matrix_bundle_id() -> str:
    """Bundle id for ``assets/matrices/production`` (must match on-disk manifest ``version``)."""
    m = load_version_document().get("matrices") or {}
    return str(m.get("production_bundle", "v1"))


def pch_bundle_id() -> str:
    """Bundle id for ``assets/matrices/pch`` (must match ``P_CH_manifest.json`` ``version``)."""
    m = load_version_document().get("matrices") or {}
    return str(m.get("pch_bundle", "v1"))


def get_build_id() -> str:
    """Deterministic-ish id: system_version + commit + timestamp (or override)."""
    doc = load_version_document()
    build = doc.get("build") or {}
    override = build.get("build_id_override") or os.environ.get("HESPERIA_BUILD_ID", "").strip()
    if override:
        return str(override)
    sv = get_system_version()
    commit = build.get("git_commit") or "unknown"
    ts = build.get("timestamp") or "unknown"
    return f"hesperia_{sv}_{commit}_{ts}"


def calibration_profile_bundle_id() -> str:
    c = load_version_document().get("calibration") or {}
    return str(c.get("profile_bundle", "v1"))


def calibration_active_profile_id() -> str:
    c = load_version_document().get("calibration") or {}
    if c.get("active_profile"):
        return str(c["active_profile"])
    d = load_version_document().get("defaults") or {}
    return str(d.get("calibration_profile") or "default_v1")


def default_calibration_profile() -> str:
    """Public metadata string: active governed calibration profile."""
    return calibration_active_profile_id()


def attach_version_metadata(output: dict[str, Any]) -> dict[str, Any]:
    """Minimal envelope: system_version + schema_version (public_output)."""
    sch = get_schema_versions()
    meta = {
        "system_version": get_system_version(),
        "schema_version": sch.get("public_output", "v1"),
    }
    return {**output, **meta}


def attach_public_output_metadata(
    output: dict[str, Any],
    *,
    calibration_profile: str | None = None,
    run_id: str | None = None,
    pipeline_version: str | None = None,
    execution_flow_version: str | None = None,
    orchestration_mode: str | None = None,
    modules_used: list[str] | None = None,
) -> dict[str, Any]:
    """
    Full public envelope. Call after apply_public_projection.
    Required for API, CLI, and E2E JSON surfaces.
    """
    sch = get_schema_versions()
    profile = calibration_profile if calibration_profile is not None else default_calibration_profile()
    envelope: dict[str, Any] = {
        "system_version": get_system_version(),
        "build_id": get_build_id(),
        "schema_version": sch.get("public_output", "v1"),
        "calibration_profile": profile,
    }
    if run_id is not None:
        envelope["run_id"] = run_id
    flow_version = execution_flow_version if execution_flow_version is not None else pipeline_version
    if flow_version is not None:
        # Canonical naming first.
        envelope["execution_flow_version"] = flow_version
    if pipeline_version is not None:
        # Legacy compatibility surface.
        envelope["pipeline_version"] = pipeline_version
    elif flow_version is not None:
        envelope["pipeline_version"] = flow_version
    if orchestration_mode is not None:
        envelope["orchestration_mode"] = orchestration_mode
    if modules_used is not None:
        envelope["modules_used"] = list(modules_used)
    # Envelope keys must win over payload collisions (authoritative trace).
    return {**output, **envelope}


def e2e_pipeline_version() -> str:
    pipes = load_version_document().get("pipelines") or {}
    return str(pipes.get("e2e", "e2e_v2"))


def structural_pipeline_version() -> str:
    pipes = load_version_document().get("pipelines") or {}
    return str(pipes.get("structural", "structural_v1"))


def api_pipeline_version() -> str:
    pipes = load_version_document().get("pipelines") or {}
    return str(pipes.get("api", "api_v1"))


def triz_pipeline_version() -> str:
    pipes = load_version_document().get("pipelines") or {}
    return str(pipes.get("triz", "triz_v1"))


def clear_version_cache() -> None:
    """Test helper."""
    load_version_document.cache_clear()
