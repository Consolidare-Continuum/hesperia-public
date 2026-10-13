"""Single deterministic pipeline runner entrypoint."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from core.engine.core import HesperiaEngine
from core.engine.validators import validate_final_ctx
from hesperia.system.version import load_version_document


def _apply_version() -> str:
    doc = load_version_document()
    apply_doc = doc.get("apply") or {}
    return str(apply_doc.get("version", "0.7.0"))


def _checksum_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def run_pipeline(
    text: str,
    *,
    config_path: Path,
    until_phase: str | None = None,
    only_module: str | None = None,
) -> dict[str, Any]:
    engine = HesperiaEngine()
    engine.load_from_config(config_path)
    only_modules = {only_module} if only_module else None
    ctx = engine.run(text, until_phase=until_phase, only_modules=only_modules)

    if until_phase is None:
        validate_final_ctx(ctx)

    module_versions = {m.name: str(getattr(m, "version", "")) for m in engine.modules}
    config_payload = json.loads(json.dumps({}))  # sentinel for deterministic typing
    try:
        import yaml  # type: ignore[import-untyped]

        config_payload = dict(yaml.safe_load(config_path.read_text(encoding="utf-8")) or {})
    except Exception:
        config_payload = {}
    expected_versions = dict(config_payload.get("expected_module_versions") or {})
    mismatch = {
        k: {"expected": str(v), "actual": module_versions.get(k)}
        for k, v in expected_versions.items()
        if module_versions.get(k) != str(v)
    }
    if mismatch and bool(config_payload.get("fail_on_version_mismatch", False)):
        raise ValueError(f"module_version_mismatch_manifest:{mismatch}")
    ctx["meta"]["version_manifest"] = {
        "apply_version": _apply_version(),
        "modules": module_versions,
        "version_mismatch": mismatch,
    }
    ctx["meta"]["run_manifest"] = {
        "config_path": str(config_path),
        "config_checksum": hashlib.sha256(config_path.read_bytes()).hexdigest(),
        "modules_loaded": [m.name for m in engine.modules],
        "input_checksum": _checksum_text(text),
        "hashes": {k: v for k, v in ctx.get("meta", {}).items() if str(k).startswith("hash_")},
    }
    return {
        "meta": dict(ctx.get("meta") or {}),
        "signals": dict(ctx.get("signals") or {}),
        "areas": dict(ctx.get("areas") or {}),
        "families": dict(ctx.get("families") or {}),
        "metrics": dict(ctx.get("metrics") or {}),
        "trace": list((ctx.get("meta") or {}).get("trace") or []),
    }


def write_run_manifest(dossier: dict[str, Any], output_path: Path) -> None:
    output_path.write_text(
        json.dumps(dict(dossier.get("meta", {}).get("run_manifest") or {}), ensure_ascii=False, sort_keys=True, indent=2),
        encoding="utf-8",
    )
