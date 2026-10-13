# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

# Prolog-style Logic Layer: symbolic inference (optional L9b).
from sphere.prolog_logic.rule_compiler import (
    parse_rule,
    parse_fact,
    compile_knowledge_base,
)
from sphere.prolog_logic.knowledge_base import (
    build_knowledge_base,
    add_fact,
    add_rule,
    query_predicate,
)
from sphere.prolog_logic.inference_executor import (
    infer,
    evaluate_rule,
    derive_new_facts,
)
from sphere.prolog_logic.engine import compute_prolog_inference

__all__ = [
    "parse_rule",
    "parse_fact",
    "compile_knowledge_base",
    "build_knowledge_base",
    "add_fact",
    "add_rule",
    "query_predicate",
    "infer",
    "evaluate_rule",
    "derive_new_facts",
    "compute_prolog_inference",
]
