# HESPERIA — Commercial module entitlement (HESP-LIC-024/031/057).
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM"
# (IDNO 1026023120076). See LEGAL_NOTICE.md.
#
# Product SKU gate distinct from redistribution license_check.py.
# HSPR = default licenced · TFP = free_forever · paid = fail-closed without matrix PASS.
# Not ISO/NIS2 certification.

"""Runtime entitlement decisions for Hesperia module installs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping

# Exact commercial instrument for sealed product Hesperia 1.0.0.
LICENCE_INSTRUMENT = "CC-HES-LIC-1.0"
LICENCE_PRODUCT_VERSION = "1.0.0"

COMMERCIAL_DEFAULT = "default_licenced"
COMMERCIAL_FREE = "free_forever"
COMMERCIAL_PAID = "paid"

# Align with postgres_db cc_brain.hesperia_licence.sku seed rows (HESP-LIC-041).
BUILTIN_SKUS: dict[str, dict[str, str]] = {
    "hspr": {
        "sku_id": "sku_hspr_default",
        "module_id": "hspr",
        "commercial": COMMERCIAL_DEFAULT,
        "class_label": "product_default",
    },
    "hesperia.modules.hspr": {
        "sku_id": "sku_hspr_default",
        "module_id": "hspr",
        "commercial": COMMERCIAL_DEFAULT,
        "class_label": "product_default",
    },
    "tfp": {
        "sku_id": "sku_tfp_free",
        "module_id": "hesperia.modules.tfp",
        "commercial": COMMERCIAL_FREE,
        "class_label": "B",
    },
    "tfp.v1": {
        "sku_id": "sku_tfp_free",
        "module_id": "hesperia.modules.tfp",
        "commercial": COMMERCIAL_FREE,
        "class_label": "B",
    },
    "hesperia.modules.tfp": {
        "sku_id": "sku_tfp_free",
        "module_id": "hesperia.modules.tfp",
        "commercial": COMMERCIAL_FREE,
        "class_label": "B",
    },
    "hesperia.modules.tfp.v1": {
        "sku_id": "sku_tfp_free",
        "module_id": "hesperia.modules.tfp",
        "commercial": COMMERCIAL_FREE,
        "class_label": "B",
    },
    "hesperia.modules.default": {
        "sku_id": "sku_modules_default",
        "module_id": "hesperia.modules.default",
        "commercial": COMMERCIAL_DEFAULT,
        "class_label": "A",
    },
    # Paid Class B+ — require matrix PASS (HESP-LIC-057).
    "mrt": {
        "sku_id": "sku_mrt_paid",
        "module_id": "mrt",
        "commercial": COMMERCIAL_PAID,
        "class_label": "B+",
    },
    "cobalt": {
        "sku_id": "sku_cobalt_paid",
        "module_id": "cobalt",
        "commercial": COMMERCIAL_PAID,
        "class_label": "B+",
    },
    "hesperia.modules.mrt": {
        "sku_id": "sku_mrt_paid",
        "module_id": "mrt",
        "commercial": COMMERCIAL_PAID,
        "class_label": "B+",
    },
    "hesperia.modules.cobalt": {
        "sku_id": "sku_cobalt_paid",
        "module_id": "cobalt",
        "commercial": COMMERCIAL_PAID,
        "class_label": "B+",
    },
}

# Class A dictionary / plumbing aliases — default licenced with modules.default.
_DEFAULT_LICENCED_ALIASES = frozenset(
    {
        "nlp",
        "nlp.basic",
        "dict_a",
        "dict_b",
        "core.dict_a",
        "core.dict_b",
        "topology",
        "topology.core",
        "metrics",
        "metrics.base",
    }
)


@dataclass(frozen=True)
class EntitlementDecision:
    """One install/enable decision (mirrors hesperia_licence.entitlement_decision)."""

    module_id: str
    sku_id: str
    commercial: str
    allow: bool
    reason: str
    hspr_default_on: bool = False
    host: str = "unnamed"


class EntitlementDenied(PermissionError):
    """Fail-closed: paid (or unknown-paid) module without matrix PASS."""

    def __init__(self, decision: EntitlementDecision) -> None:
        self.decision = decision
        super().__init__(f"entitlement_denied:{decision.module_id}:{decision.reason}")


MatrixProbe = Callable[[str, str], bool]
"""(module_id, sku_id) -> True if HSPR×120-books matrix PASS."""


def resolve_sku(module_id: str, catalog: Mapping[str, dict[str, str]] | None = None) -> dict[str, str]:
    """Resolve module / alias to SKU row. Unknown → treated as paid (fail-closed)."""
    cat = catalog if catalog is not None else BUILTIN_SKUS
    key = (module_id or "").strip()
    if key in cat:
        return dict(cat[key])
    if key in _DEFAULT_LICENCED_ALIASES:
        return dict(cat["hesperia.modules.default"])
    # Unknown module_id: fail-closed paid placeholder (HESP-LIC-057).
    return {
        "sku_id": f"sku_unknown_{key or 'empty'}",
        "module_id": key or "unknown",
        "commercial": COMMERCIAL_PAID,
        "class_label": "unknown",
    }


def hspr_default_enabled_for_licenced_install() -> bool:
    """HESP-LIC-024: HSPR default on for licenced installs."""
    return True


def tfp_requires_paid_sku_check() -> bool:
    """HESP-LIC-031: TFP forever free — no paid SKU check."""
    return False


def check_entitlement(
    module_id: str,
    *,
    matrix_pass: bool | None = None,
    matrix_probe: MatrixProbe | None = None,
    host: str = "unnamed",
    catalog: Mapping[str, dict[str, str]] | None = None,
) -> EntitlementDecision:
    """
    Decide whether module may be installed/enabled.

    - default_licenced (incl. HSPR): allow; HSPR sets hspr_default_on=True
    - free_forever (TFP): allow without paid / matrix check
    - paid: allow only if matrix_pass is True or matrix_probe returns True
    """
    sku = resolve_sku(module_id, catalog=catalog)
    commercial = sku["commercial"]
    sku_id = sku["sku_id"]
    resolved_module = sku["module_id"]
    hspr_on = hspr_default_enabled_for_licenced_install() and (
        resolved_module == "hspr" or commercial == COMMERCIAL_DEFAULT
    )

    if commercial == COMMERCIAL_FREE:
        # Explicit: no paid SKU gate for TFP.
        if tfp_requires_paid_sku_check():  # pragma: no cover — locked False
            return EntitlementDecision(
                module_id=resolved_module,
                sku_id=sku_id,
                commercial=commercial,
                allow=False,
                reason="tfp_paid_check_misconfigured",
                hspr_default_on=False,
                host=host,
            )
        return EntitlementDecision(
            module_id=resolved_module,
            sku_id=sku_id,
            commercial=commercial,
            allow=True,
            reason="tfp_free_forever",
            hspr_default_on=False,
            host=host,
        )

    if commercial == COMMERCIAL_DEFAULT:
        return EntitlementDecision(
            module_id=resolved_module,
            sku_id=sku_id,
            commercial=commercial,
            allow=True,
            reason="default_licenced",
            hspr_default_on=hspr_on,
            host=host,
        )

    # Paid — fail-closed unless matrix PASS.
    passed = matrix_pass
    if passed is None and matrix_probe is not None:
        passed = bool(matrix_probe(resolved_module, sku_id))
    if passed is True:
        return EntitlementDecision(
            module_id=resolved_module,
            sku_id=sku_id,
            commercial=commercial,
            allow=True,
            reason="matrix_pass",
            hspr_default_on=False,
            host=host,
        )
    return EntitlementDecision(
        module_id=resolved_module,
        sku_id=sku_id,
        commercial=commercial,
        allow=False,
        reason="matrix_deny_fail_closed",
        hspr_default_on=False,
        host=host,
    )


def assert_module_entitlement(
    module_id: str,
    *,
    matrix_pass: bool | None = None,
    matrix_probe: MatrixProbe | None = None,
    host: str = "unnamed",
) -> EntitlementDecision:
    """Raise EntitlementDenied when not allowed (install fail-closed)."""
    decision = check_entitlement(
        module_id,
        matrix_pass=matrix_pass,
        matrix_probe=matrix_probe,
        host=host,
    )
    if not decision.allow:
        raise EntitlementDenied(decision)
    return decision
