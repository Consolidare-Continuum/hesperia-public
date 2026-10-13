"""TFP module path compatibility shim."""

from __future__ import annotations

from hesperia.modules.tfp.v1 import TFPModule


def create() -> TFPModule:
    return TFPModule()

