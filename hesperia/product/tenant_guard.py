# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# See LEGAL_NOTICE.md for full terms.

"""Tenant isolation: no cross-tenant paths, no benchmark output mixing."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from hesperia.product.tenant_context import TenantContext

TENANT_ISOLATION_ERROR = "Tenant isolation violation detected."

# In-process cache namespace per tenant (no cross-tenant reuse)
_RUN_CACHE: dict[str, dict[str, Any]] = {}


class TenantIsolationViolation(RuntimeError):
    pass


def assert_tenant_output_path(path: Path, tenant: TenantContext) -> None:
    """Path must resolve under outputs/{tenant_id}/{project_id}/."""
    path = path.resolve()
    parts = path.parts
    if tenant.tenant_id not in parts or tenant.project_id not in parts:
        raise TenantIsolationViolation(
            f"{TENANT_ISOLATION_ERROR} Path must include tenant_id and project_id segments."
        )
    ti = parts.index(tenant.tenant_id)
    if ti + 1 >= len(parts) or parts[ti + 1] != tenant.project_id:
        raise TenantIsolationViolation(f"{TENANT_ISOLATION_ERROR} project_id must follow tenant_id.")


def guard_no_benchmark_in_path(path: Path) -> None:
    p = str(path).lower()
    if "benchmark" in p and "corpus_" in p and "fixtures" in p:
        raise TenantIsolationViolation(f"{TENANT_ISOLATION_ERROR} Benchmark fixtures must not write to tenant tree mixed paths.")


def tenant_cache_get(tenant_id: str, key: str) -> Any:
    return _RUN_CACHE.setdefault(tenant_id, {}).get(key)


def tenant_cache_set(tenant_id: str, key: str, value: Any) -> None:
    _RUN_CACHE.setdefault(tenant_id, {})[key] = value


def clear_tenant_cache(tenant_id: str) -> None:
    _RUN_CACHE.pop(tenant_id, None)
