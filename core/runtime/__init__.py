"""Canonical runtime entrypoint package.

Module implementations (dict_a, dict_b, topology, metrics) live in
hesperia/modules/default/ — universal/domain-agnostic capabilities, Class A in
docs/specs/HESPERIA-CORE-MODULES-AND-BRANCHES.md. core/ must never import
hesperia.modules.* directly (enforced by tools/check_core_module_boundary.py) —
resolve them via core.engine.module_loader.load_module()/module_aliases.py instead.
"""
