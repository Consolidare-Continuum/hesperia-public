"""Validate module contracts at load time."""

from __future__ import annotations

from typing import Any

REQUIRED_FIELDS = ("name", "version", "provides", "requires", "capabilities")
PHASES = ("preprocess", "project", "postprocess")


def validate_module_contract(module: Any) -> None:
    for field in REQUIRED_FIELDS:
        if not hasattr(module, field):
            raise ValueError(f"module_contract_missing:{getattr(module, 'name', 'unknown')}:{field}")
    if not str(getattr(module, "name", "")).strip():
        raise ValueError("module_contract_invalid_name")
    if not str(getattr(module, "version", "")).strip():
        raise ValueError(f"module_contract_invalid_version:{module.name}")
    provides = getattr(module, "provides")
    requires = getattr(module, "requires")
    capabilities = getattr(module, "capabilities")
    def _valid_cap_map(x: Any) -> bool:
        return isinstance(x, dict) and all(isinstance(k, str) and isinstance(v, list) and all(isinstance(i, str) for i in v) for k, v in x.items())

    if not ((isinstance(provides, list) and all(isinstance(x, str) and x for x in provides)) or _valid_cap_map(provides)):
        raise ValueError(f"module_contract_invalid_provides:{module.name}")
    if not ((isinstance(requires, list) and all(isinstance(x, str) and x for x in requires)) or _valid_cap_map(requires)):
        raise ValueError(f"module_contract_invalid_requires:{module.name}")
    output_schema = getattr(module, "output_schema", None)
    if not isinstance(output_schema, dict):
        raise ValueError(f"module_contract_missing_output_schema:{module.name}")
    if not isinstance(capabilities, dict):
        raise ValueError(f"module_contract_invalid_capabilities:{module.name}")
    for phase in PHASES:
        if phase not in capabilities or not isinstance(capabilities[phase], bool):
            raise ValueError(f"module_contract_invalid_phase_capability:{module.name}:{phase}")
        if capabilities[phase]:
            fn = getattr(module, phase, None)
            if not callable(fn):
                raise ValueError(f"module_contract_missing_phase_impl:{module.name}:{phase}")
    configure = getattr(module, "configure", None)
    if not callable(configure):
        raise ValueError(f"module_contract_missing_configure:{module.name}")

