# Era 7: The V7 Router — fpf_bridge, Layer 11 (2026-06-27 → present, unsealed)

## Evidence

```
$ git log 0.6.3..HEAD --oneline | wc -l
0
```

There are zero commits past `0.6.3` — the entire V7 router exists only as uncommitted working-tree
state plus two spec files that *were* committed ahead of the code (`specs/canon/fpf_bridge_v7.md`,
committed 2026-06-27; `specs/canon/fpf_bridge_v7_deep_learning_gaps.md`, committed 2026-06-29).

```
$ git status --short | grep -E 'fpf_bridge|llm_integration|sphere/fpf'
?? sphere/fpf_bridge/
?? tests/test_fpf_bridge.py
?? tests/test_llm_integration.py
?? tests/test_v7_engine_foundations.py
?? tests/fixtures/mock_pipeline_result.py
```

The spec itself (`specs/canon/fpf_bridge_v7.md`) records: "Version: v7, Status: IMPLEMENTED, Date:
2026-06-27, Author: Felix (Developer, Claude Code)." Both spec and code landed in the working tree
together, the spec describing 33 deterministic tests already passing
(`tests/test_fpf_bridge.py`).

## What this era actually is

This is the era where Hesperia, for the first time, has a designed path for an LLM to participate
in producing a structural narrative without becoming part of the deterministic measurement core.
The spec's own self-description is precise: a "Bridge between Hesperia's deterministic pipeline
output (L1–L10) and fpf-thinking-map's structured reasoning substrate. Produces a bounded semantic
field for LLM traversal — not raw JSON, but a state machine with evidence-gated transitions,
deterministic guards, and propositional logic constraints."

The bridge's design directly continues the pattern set in era 1 (guards) and reinforced in every
era since: rather than trusting the new, less-controllable component (the LLM) to behave well, the
architecture builds a bounded structure around it that limits what it is *able* to assert,
regardless of how it behaves. This is visible concretely in: the 5-state/13-transition graph
(bounding possible narrative trajectories), the 8 evidence-gated transitions (bounding what
conclusions can be reached without supporting evidence), the pre-evaluated guard closures (refusing
to let the LLM layer re-derive or second-guess Sigma/Gamma/Theta), and the explicit READ-ONLY file
list (bounding what the new code is even permitted to touch).

The companion deep-learning-gaps spec (`fpf_bridge_v7_deep_learning_gaps.md`, two days later, status
"requires Ethan ratification" — not yet built) is evidence of the same restraint pattern continuing
into the unbuilt future: even the proposed self-improvement loop (attention tracking, learned
embeddings, reward-based gate adjustment) is explicitly scoped as advisory and post-pipeline —
"Production gates unchanged until operator approves," gated behind env flags
(`HESPERIA_FGR_FREEZE`, `HESPERIA_REWARD_LEARNING`) defaulting to off, exactly mirroring the metric
wave's `HESPERIA_METRIC_EMIT` pattern one era earlier.

## Why this ordering was the minimal right move

Writing the bridge as a pure, read-only consumer (rather than refactoring the sphere pipeline to be
"LLM-aware," or letting the LLM write back into pipeline state) is the smallest possible new seam
that connects deterministic measurement to probabilistic narration without weakening either side.
A larger move — modifying `pipeline_runner.py` or `rule_engine.py` to natively support LLM
round-trips — would have reopened every guard invariant to renewed scrutiny (does Gamma's
"no_upstream_mutation" still hold if an LLM call can influence pipeline_runner behavior?) for a
benefit (tighter LLM integration) that a read-only consumer achieves anyway. The deep-learning-gaps
spec, by deferring all three proposed extensions to "post-pipeline, advisory only, operator-approved"
status rather than building them immediately, keeps this era's actual delivered surface area as
small as it could be while still closing the consumption and re-analysis gaps that motivated the
era in the first place (see `00_INDEX.md`'s Era 8 section, which uses the eight-eras-from-the-top
framing this file's evidence supports).

See [`corners/fpf_bridge.md`](../corners/fpf_bridge.md), [`corners/guards.md`](../corners/guards.md),
[`corners/prolog_logic.md`](../corners/prolog_logic.md).
