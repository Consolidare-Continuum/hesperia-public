# Corner: Prolog Inference — the L9b Symbolic Layer in Focused Detail

**Location:** `sphere/prolog_logic/` (engine.py, knowledge_base.py, rule_compiler.py,
inference_executor.py, explanation_graph.py), `specs/canon/prolog_rules_example.pl`.

**Born:** added as a distinct sub-layer at `63febce1 Layer-10 interpretation, USF consolidation,
Prolog L9b, multi-step propagation, fingerprint drift` (v0.4.1 era), referred to in the fpf_bridge
spec as "L9b."

## Why this is a distinct concern

Layer-9's declarative rules (`specs/canon/logic_rules.yaml`, covered in `corners/logic_guards.md`)
are independent threshold checks: each rule fires or doesn't based on one fact crossing one
boundary (`entropy < 0.35`, `curvature > 1.20`). Some conclusions Hesperia needs to draw are not
expressible as a single threshold — they are compositions of several already-derived facts
(`elevated_risk`, `propagation_wave`, `transition_risk` — the exact predicate names the
fpf_bridge's LogicLayer later consumes as "pre-resolved booleans"). A flat list of independent
threshold rules cannot express "fact A and fact B together imply elevated risk, but neither alone
does" without becoming an unmanageable combinatorial list of compound rules.

A Prolog-style knowledge base with an explicit `rule_compiler.py` and `inference_executor.py` is
the minimal addition that supports composing facts through true logical inference without writing
imperative branching logic that would defeat the "no thresholds in Python" discipline Layer-9
itself follows. `explanation_graph.py` exists specifically because a composed conclusion is only
auditable if the system can show *which* underlying facts and *which* inference steps produced it —
the same explainability requirement `docs/foundations/theory_description.txt` demands of concept resolution
("explainable trace: for every concept hit, you can show which span matched which rule and why one
sense won over alternatives") applied here to composite risk/state predicates instead of lexical
matches.

## What would break without it

Without the Prolog inference layer, composite conclusions like `elevated_risk` (which the
fpf_bridge's `elevated_risk` BLOCK rule depends on directly) would have to be hand-coded as nested
conditionals somewhere in Python, with no single place recording *why* a combination of facts
implies a higher-order risk predicate. That would silently violate the "no thresholds in Python"
discipline `logic_rules.yaml` enforces for Layer-9 proper, and would make every composite rule a
one-off, untraceable piece of imperative logic instead of a declarative, explainable fact.

## How it relates to neighbors

The Prolog layer consumes Layer-9's already-derived facts (`corners/logic_guards.md`) and metrics
computed by `sphere/metrics/` and `sphere/dynamism/` (`corners/propagation_dynamics.md`). Its
output — `prolog_logic.derived_facts` — is the direct input to the fpf_bridge's `logic_bridge.py`,
which compiles the facts into a 7-rule LogicLayer using all 6 propositional operators (AND, OR,
NOT, IMPLIES, IFF, XOR) — meaning this corner is the layer immediately below the V7 bridge in the
execution flow, and the bridge treats its facts as fixed, never re-derived (see
`corners/fpf_bridge.md`).
