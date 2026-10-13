"""Alias map for dynamic module loading (SSOT for core.engine.module_loader)."""

from __future__ import annotations

MODULE_ALIASES: dict[str, str] = {
    "nlp": "hesperia.modules.nlp.basic",
    "dict_a": "hesperia.modules.default.dict_a_module",
    "dict_b": "hesperia.modules.default.dict_b_module",
    "topology": "hesperia.modules.default.topology_module",
    "tfp": "hesperia.modules.tfp.v1",
    "metrics": "hesperia.modules.default.metrics_module",
    # Back-compat aliases.
    "nlp.basic": "hesperia.modules.nlp.basic",
    "core.dict_a": "hesperia.modules.default.dict_a_module",
    "core.dict_b": "hesperia.modules.default.dict_b_module",
    "topology.core": "hesperia.modules.default.topology_module",
    "tfp.v1": "hesperia.modules.tfp.v1",
    "metrics.base": "hesperia.modules.default.metrics_module",
}
