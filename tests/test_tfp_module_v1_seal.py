# HESPERIA — TFP-V1-09: seal hook behavior.
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
from __future__ import annotations

import os

import pytest

from hesperia.modules.tfp.seal import enforce_tfp_module_seal_on_project, tfp_module_seal_effective


@pytest.fixture
def _restore_seal_env() -> None:
    old = os.environ.get("HESPERIA_TFP_MODULE_SEALED")
    yield
    if old is None:
        os.environ.pop("HESPERIA_TFP_MODULE_SEALED", None)
    else:
        os.environ["HESPERIA_TFP_MODULE_SEALED"] = old


def test_seal_off_when_unset(_restore_seal_env) -> None:
    os.environ.pop("HESPERIA_TFP_MODULE_SEALED", None)
    assert tfp_module_seal_effective() == "off"


def test_seal_block_raises(_restore_seal_env) -> None:
    os.environ["HESPERIA_TFP_MODULE_SEALED"] = "block"
    with pytest.raises(RuntimeError, match="TFP module v1 seal"):
        enforce_tfp_module_seal_on_project()
