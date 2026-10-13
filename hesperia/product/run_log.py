# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# See LEGAL_NOTICE.md for full terms.

"""Run audit trail: start/complete/failure + immutable run manifest."""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hesperia.product.tenant_context import TenantContext
from hesperia.product.tenant_guard import assert_tenant_output_path


@dataclass
class RunLogEntry:
    tenant_id: str
    project_id: str
    product_sku: str
    corpus_id: str
    run_id: str
    timestamp_start: str
    timestamp_end: str = ""
    status: str = "STARTED"
    readiness_gate_result: str = ""
    artifact_paths: list[str] = field(default_factory=list)


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log_run_start(
    tenant: TenantContext,
    *,
    product_sku: str,
    corpus_id: str,
    run_id: str | None = None,
    output_root: Path | str = "outputs",
) -> RunLogEntry:
    rid = run_id or str(uuid.uuid4())
    return RunLogEntry(
        tenant_id=tenant.tenant_id,
        project_id=tenant.project_id,
        product_sku=product_sku,
        corpus_id=corpus_id,
        run_id=rid,
        timestamp_start=_ts(),
    )


def log_run_complete(
    entry: RunLogEntry,
    *,
    artifact_paths: list[str],
    readiness_gate_result: str = "PASS",
    output_root: Path | str = "outputs",
    tenant: TenantContext,
) -> dict[str, Any]:
    entry.timestamp_end = _ts()
    entry.status = "PASS"
    entry.readiness_gate_result = readiness_gate_result
    entry.artifact_paths = artifact_paths
    out_dir = Path(output_root) / tenant.tenant_id / tenant.project_id / entry.run_id
    assert_tenant_output_path(out_dir, tenant)
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "artifact_paths": sorted(artifact_paths),
        "input_corpus_ids": [entry.corpus_id],
        "product_sku": entry.product_sku,
        "run_id": entry.run_id,
        "schema_version": "triz_run_manifest_v1",
        "status": "PASS",
    }
    mp = out_dir / "run_manifest.json"
    mp.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    logf = out_dir / "run_audit.jsonl"
    with logf.open("a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(entry), sort_keys=True) + "\n")
    return manifest


def log_run_failure(
    entry: RunLogEntry,
    reason: str,
    *,
    output_root: Path | str = "outputs",
    tenant: TenantContext,
) -> None:
    entry.timestamp_end = _ts()
    entry.status = f"FAIL:{reason[:200]}"
    out_dir = Path(output_root) / tenant.tenant_id / tenant.project_id / entry.run_id
    assert_tenant_output_path(out_dir, tenant)
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "run_id": entry.run_id,
        "schema_version": "triz_run_manifest_v1",
        "status": "FAIL",
        "reason": reason[:500],
    }
    (out_dir / "run_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
