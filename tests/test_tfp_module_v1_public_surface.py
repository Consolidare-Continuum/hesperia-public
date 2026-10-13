# HESPERIA — TFP-V1-02: public import surface for hesperia.modules.tfp.
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
from __future__ import annotations

import hesperia.modules.tfp as tfp_pkg
from hesperia.modules.tfp import TFPModule, create, create_v1
from hesperia.modules.tfp.module import create as create_shim
from hesperia.modules.tfp.v1 import create as create_v1_direct


def test_public_all_exports() -> None:
    assert set(tfp_pkg.__all__) == {"TFPModule", "create", "create_v1"}


def test_create_aliases_match() -> None:
    a = create()
    b = create_shim()
    c = create_v1()
    d = create_v1_direct()
    assert isinstance(a, TFPModule) and isinstance(b, TFPModule)
    assert isinstance(c, TFPModule) and isinstance(d, TFPModule)
    assert a.name == "tfp.v1"
