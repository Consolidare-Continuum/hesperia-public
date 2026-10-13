# HESP-LIC-024 / 031 / 057 — commercial entitlement unit tests.

from __future__ import annotations

import pytest

from hesperia.product.commercial_entitlement import (
    COMMERCIAL_DEFAULT,
    COMMERCIAL_FREE,
    COMMERCIAL_PAID,
    EntitlementDenied,
    assert_module_entitlement,
    check_entitlement,
    hspr_default_enabled_for_licenced_install,
    tfp_requires_paid_sku_check,
)


def test_hspr_default_on_for_licenced_install() -> None:
    assert hspr_default_enabled_for_licenced_install() is True
    d = check_entitlement("hspr")
    assert d.allow is True
    assert d.commercial == COMMERCIAL_DEFAULT
    assert d.hspr_default_on is True
    assert d.reason == "default_licenced"


def test_tfp_free_forever_no_paid_sku_check() -> None:
    assert tfp_requires_paid_sku_check() is False
    d = check_entitlement("tfp", matrix_pass=False)
    assert d.allow is True
    assert d.commercial == COMMERCIAL_FREE
    assert d.reason == "tfp_free_forever"
    # Paid matrix deny must not block TFP.
    assert_module_entitlement("hesperia.modules.tfp", matrix_pass=False)


def test_paid_fail_closed_without_matrix() -> None:
    d = check_entitlement("mrt")
    assert d.allow is False
    assert d.commercial == COMMERCIAL_PAID
    assert d.reason == "matrix_deny_fail_closed"
    with pytest.raises(EntitlementDenied):
        assert_module_entitlement("cobalt")


def test_paid_allow_when_matrix_pass() -> None:
    d = check_entitlement("mrt", matrix_pass=True)
    assert d.allow is True
    assert d.reason == "matrix_pass"
    assert_module_entitlement("cobalt", matrix_pass=True)


def test_paid_via_matrix_probe() -> None:
    d = check_entitlement("mrt", matrix_probe=lambda _m, _s: True)
    assert d.allow is True
    d2 = check_entitlement("mrt", matrix_probe=lambda _m, _s: False)
    assert d2.allow is False


def test_unknown_module_fail_closed() -> None:
    d = check_entitlement("hesperia.modules.future_paid_thing")
    assert d.allow is False
    assert d.commercial == COMMERCIAL_PAID
