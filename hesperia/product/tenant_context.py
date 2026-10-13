# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# See LEGAL_NOTICE.md for full terms.

from __future__ import annotations

import re
from dataclasses import dataclass

_SAFE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,127}$")


@dataclass(frozen=True)
class TenantContext:
    tenant_id: str
    project_id: str
    environment: str = "pilot"
    retention_policy: str = "standard"


def validate_tenant_context(ctx: TenantContext) -> None:
    for name, val in (("tenant_id", ctx.tenant_id), ("project_id", ctx.project_id)):
        if not val or not _SAFE.match(val):
            raise ValueError(f"invalid {name}: must match safe id pattern")


def tenant_output_prefix(root: str | None, ctx: TenantContext) -> str:
    from pathlib import Path

    r = Path(root or "outputs")
    return str((r / ctx.tenant_id / ctx.project_id).resolve())
