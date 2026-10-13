# Corner: fpf_bridge — Layer 11, the LLM Reasoning Bridge (`sphere/fpf_bridge/`, `specs/canon/fpf_bridge_v7.md`)

**Status:** IMPLEMENTED, v7, 2026-06-27. The newest corner in the system, and the only one whose
entire reason for existing is to make contact with something Hesperia cannot make deterministic: an
LLM.

## Why this corner exists at all

Every layer below this one (L1–L10) produces a structural *measurement* — vectors, states, rule
triggers — but no prose. At some point something has to turn "structural_state = focused_dominant,
dominant_area = A2, triggered_rules = [...]" into a sentence a person can read, and a sentence is
exactly the kind of artifact Hesperia is built to distrust unless its provenance is fully traceable.
fpf_bridge exists to answer one narrow question: how does a deterministic system hand its findings
to a fundamentally non-deterministic process (an LLM) without becoming non-deterministic itself?

## Why it is a bridge (pure consumer) and not an extension of sphere

The spec states the constraint as a guarantee, not a preference: "Sphere stays deterministic.
fpf_bridge is a pure consumer — zero modifications to existing sphere code," and lists eight files
under `sphere/` that are explicitly read-only from the bridge's perspective (`pipeline_runner.py`,
`state_classifier.py`, `engine.py`, `rule_engine.py`, `rule_types.py`,
`sphere/prolog_logic/engine.py`, `guard_runtime.py`, plus everything under `dynamism/`, `shadow/`,
`propagation/`). If the bridge could write back into sphere — say, to record which evidence the LLM
used — sphere would acquire a second source of truth that isn't purely a function of input text,
and every invariant Sigma/Gamma/Theta were built to guarantee (Era 3, see `corners/guards.md`)
would need to be re-verified against a system that no longer has one clean execution path. Keeping
the bridge strictly downstream and read-only is what lets it exist *without re-opening any of the
guarantees the rest of the castle is built on*.

## Why a state machine, not a raw JSON dump, is handed to the LLM

A 5-state, 13-transition state graph with 8 evidence-gated gates is a deliberately narrow interface.
The alternative — handing the LLM the full pipeline result dict and a free-text prompt — would let
the LLM's narrative wander to any conclusion the words happen to suggest, with no way to check
afterward whether that conclusion was actually supported by the measured evidence. By instead
compiling pipeline output into `EvidencePrimitive`s with calibrated trust values (FGR) and gating
each of the 13 transitions on specific evidence requirements, the bridge converts "can the LLM say
X" into "is there a legal transition that corresponds to X" — a question that can be checked
mechanically rather than trusted to the LLM's self-report.

## Why guards are pre-evaluated closures, not re-computed

`guard_bridge.py` wraps `guards.sigma.passed`, `guards.gamma.passed`, `guards.theta.approved` as
closures over already-computed sphere results rather than re-running Sigma/Gamma/Theta logic. This
is only possible — and only correct — because those three guards were designed from the start (Era
3) as cheap boolean-plus-detail verdicts meant to be carried forward, not expensive
recomputations. Re-deriving them inside the bridge would risk the bridge's copy drifting from the
sphere's copy after a future code change to either side; treating them as closures over fixed
results makes drift structurally impossible — there is only ever one Sigma verdict per pipeline
run, referenced from two places.

## Why the Prolog facts become `CustomProp` atoms instead of being re-interpreted

`logic_bridge.py` treats `prolog_logic.derived_facts` as pre-resolved booleans, not as Prolog
expressions to be re-evaluated inside the LLM's reasoning substrate. This preserves the same
single-source-of-truth principle as the guard closures: the Prolog engine (`sphere/prolog_logic/`)
already did the forward-chaining; the bridge's job is to expose the *result* as a fact the
LogicLayer's 7 declarative rules can reference, not to give the LLM-facing logic layer its own
copy of inference machinery that could produce a different answer from the same facts.

## Why three deep-learning extensions (attention, learned embeddings, reward) are specified but explicitly deferred

`fpf_bridge_v7_deep_learning_gaps.md` proposes attention extraction (which evidence the LLM actually
used), learned area embeddings (semantic, not just graph, similarity), and a reward signal
(acceptance-rate feedback on past interpretations) — and explicitly scopes all three as
"post-pipeline, post-bridge extensions… Sphere determinism is preserved," with the embeddings stored
separately from the canonical geometric embedding ("`sphere/topology/embedding.py` unchanged —
geometric embedding stays canonical") and reward/attention adjustments marked advisory-only, gated
behind env flags (`HESPERIA_FGR_FREEZE`, `HESPERIA_REWARD_LEARNING`) that default to not changing
production behavior. This is the same discipline as the METRIC wave's emit-gating (Era 7): a
capability can be fully specified and reviewable before it is allowed to touch any value a consumer
actually depends on.

## What FPF actually is, and what Hesperia takes from it

"fpf_bridge" names a real external framework, not an in-house abbreviation: **FPF, the First
Principles Framework**, is a ~51,300-line transdisciplinary reasoning specification (primary
author Anatoly Levenchuk, with LLM assistance) distributed as a single RAG-loadable document — an
"operating system for thought" built around holons (things that are simultaneously whole and
part), bounded contexts (meaning is only ever local to a context), and a universal aggregation
algebra (Γ) for combining parts into wholes under explicit invariants. None of that document ships
inside Hesperia; what Hesperia depends on is `fpf-thinking-map` (PyPI), an engineering substrate
that operationalizes a slice of FPF's abstractions — state graphs, evidence primitives, gated
transitions — as code an LLM-facing process can actually traverse, rather than a 51,300-line prose
spec a model would have to "interpret" freshly on every call (which would itself be exactly the
non-determinism Hesperia exists to avoid).

The specific piece of FPF theory this bridge leans on hardest is **FGR**: FPF Part B.3 defines
trust not as a single confidence number but as a tuple **⟨F, G, R⟩** — **F**ormality (how
rigorously a claim is expressed), **G** (the bounded-context slice the claim is scoped to claim
over), and **R**eliability (how well the claim is evidenced). `constants.py`'s "FGR tables" and
`evidence_mapper.py`'s `EvidencePrimitive`s are a direct application of that triple: every fact the
bridge hands to the LLM substrate carries not just a value but a calibrated trust profile, so the
state machine can gate a transition on "is this evidence formal/scoped/reliable enough," not just
"is this evidence present." This is the same falsifiability discipline as the rest of the castle
(see the Bedrock section of `00_INDEX.md`), applied to *how much an externally-sourced theory of
trust should be believed*, rather than invented ad hoc for this one corner.

**What is explicitly not borrowed:** the Sigma/Gamma/Theta guard triad (`corners/guards.md`) is
Hesperia-native, from Era 3 (`eras/03_engine_dynamics_v0.5.x.md`), years before fpf_bridge existed.
FPF's own Γ (Gamma) is an aggregation operator over wholes and parts — a different concept from
Hesperia's Gamma guard, which verifies execution *ordering*. The spec itself keeps the two
genuinely separate rather than implying derivation: "9 fpf built-in guards **+ 3 Hesperia guards
(Sigma/Gamma/Theta)**" is additive, not a 12-guard FPF design. See `provenance.md` for the full
audit of which named principles in this repo are externally sourced, Hesperia-native, or specified
without an existing implementation.

## Relationship to neighboring corners

- Strictly downstream of, and read-only against, the entire `sphere/` pipeline — every other corner
  in this folder except itself.
- Re-expresses, but does not replace, `corners/guards.md` (Sigma/Gamma/Theta as closures).
- Re-expresses, but does not replace, `corners/logic_guards.md` (logic_metrics,
  interpretation_metrics, prolog_logic.derived_facts as evidence/atoms).
- Is the first corner in the system whose correctness depends on an external package
  (`fpf-thinking-map`, PyPI) rather than being wholly self-contained — a dependency that is
  acceptable here specifically because the bridge is additive and removable without touching
  anything beneath it.
- **Extended by fpf_bridge_v7.2–v7.4** (`specs/canon/fpf_bridge_v7_2_evidence_expansion.md` and
  siblings, 2026-07-04, ratification-pending): widens the evidence surface documented above (still
  just 7 signal types as of this corner's last enrichment pass) to include L4/L5/L7 composites, KME
  primitives, and TRIZ's contradiction signal, plus a new `runtime/agentic_bridge/` consumer that
  hands this corner's `bridge_to_llm_prompt()` output directly to an external agent instead of only
  Hesperia's own internal single-shot LLM call. Same read-only-against-sphere guarantee, unchanged.
