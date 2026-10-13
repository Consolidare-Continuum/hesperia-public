# Methods (paper-shaped pipeline description)

This document describes the Hesperia pipeline at the granularity a paper's Methods section needs —
enough to reproduce and evaluate the approach, not the full engineering derivation. Full detail for
every claim below lives in `docs/foundations/` and is cited, not repeated. See
`docs/publication/NOVELTY_AND_POSITIONING.md` for what in this method is canonical vs. original
composition — this document describes *what the system does*, not *what's new about it*.

Naming discipline matters here: **core** means the sealed measurement engine; **TFP** and
**COBALT** are branches/applications on top of that core; **MRT** is a closed branch on a different
grid. A mechanism first validated on one branch is not renamed into branch-exclusive ownership
unless the cited spec explicitly scopes it that way.

## 1. Problem setting

Given free text, produce a bounded, falsifiable structural measurement, then — optionally — let a
language model narrate that measurement in natural language, under the constraint that the
narration is checked against the measurement rather than trusted at face value. The method is a
two-stage pipeline: a deterministic measurement stage (Sections 2–4) and a governed narration stage
(Section 5). In the dated productization wording preserved in
`UPCELERATOR_PRODUCTIZATION_QA.md`, this same method is the engine behind **deterministic
validation** and an **evidence-grade audit trace** for regulated teams.

## 2. Lexical resolution (the only stage that touches raw text)

Text is matched against a controlled lexicon in two tiers: Dict A (surface span matching, no
family/area authority) and Dict B (disambiguated concept resolution). The founding design
constraint — "do not allow raw wording to activate families directly unless routed through resolved
concept evidence or an explicitly marked fallback path" — is enforced here and nowhere else in the
pipeline. Full mechanism: `docs/foundations/corners/lexicon_resolver.md`.

## 3. Deterministic measurement cascade (Layers 1–9)

Nine layers, each a closed-form deterministic computation over the previous layers' outputs, each
tracing to an independently-recovered canonical spec (`34_SPEC`–`42_SPEC`, `docs/specs/history/`):

1. **Structural activation census (L1)** — coverage, dominance, entropy, altitude statistics over
   attributed tokens. 27 variables, verified. (`output_catalog.md` §1)
2. **Topology traversal (L2)** — bounded BFS from the dominant concept over a fixed graph topology;
   reachability, clustering, cross-area leakage. 27 variables, verified. (§2)
3. **Baseline/shadow comparison (L3)** — a perturbed second run compared to the first via cosine
   similarity, Jaccard, and signed deltas, producing a governed acceptability gate. 25 variables,
   verified. (§3)
4. **Evidence retrieval quality (L4)** — BM25 retrieval scored against the structural read for
   family/area alignment. 25 variables, verified. (§4)
5. **Counter-evidence and axiom self-test (L5)** — falsification-style negative-evidence retrieval,
   plus a live self-test of the trig/metric-space identities the system's own angle computations
   depend on. 25 variables (7 of 13 axiom residuals reserved for a non-deterministic-input mode not
   yet exercised), verified. (§5)
6. **Dynamical stability scaffold (L6)** — 4 live variables (depth-growth ratio, a Fibonacci-style
   growth-deviation test, a global stability score, a coherence index); 21 documented
   no-perturbation identity constants reserved for a future perturbation-analysis pass. (§6)
7. **Cross-layer consistency and decision (L7)** — 10 boolean cross-layer gates, a trust tier, and
   two aggregate scores: a four-factor confidence product and a priority-encoded decision status
   code. 25 variables, verified against the recovered spec. (§7)
8. **Unit standardization (L8)** — re-expresses L1–L7 scores onto a fixed `[0,1000]`/`[0,100]` scale
   under a declared rounding/clamp policy; introduces no new measurement. 30 variables. (§8)
9. **Human-facing labels (L9)** — the terminus: 6 confidence bands, 6 governance pillars, 5
   categorical brand labels, 4 action triggers, all derived from L1–L8 with no further measurement.
   25 variables, verified against the recovered spec. (§9)

Execution order is not a convention; it is an enforced, checkable invariant
(`sphere/pipeline/pipeline_runner.py`; `docs/iso/REQUIREMENTS_SPECIFICATION.md` NFR-D3/D4).

## 4. Certification (the guard triad)

Before any output is trusted, three categorically distinct verdicts are evaluated in a fixed order:
Sigma (static artifact shape — e.g. every area-level output is a fixed 12-slot vector), Gamma
(dynamic execution-order soundness), Theta (release/governance eligibility). Full invariant list:
`docs/foundations/layers/GUARDS_sigma_gamma_theta.md`.

## 5. Governed LLM narration (Layer 11)

The certified measurement is projected — not handed raw — into a bounded state machine: 5
structural states (`focused_dominant`, `distributed_balanced`, `unstable_transition`,
`tension_elevated`, `diffuse_spread`, each string-verified against source), a fixed menu of
evidence-gated legal transitions, and FGR-calibrated trust tuples per evidence item. An LLM narrates
only inside this menu. Its own output is then re-measured and compared against the input measurement,
producing one of four verdicts: ALLOW, WARN, REVIEW, BLOCK. Mechanism: `sphere/fpf_bridge/`,
`sphere/router/audit.py`; full reasoning: `docs/foundations/corners/fpf_bridge.md`.

## 6. Two analytical layers, read-only against the above

- **KME** (Knowledge Metrics Engine): 6 bounded primitives reduced from the activation graph, 35
  pure-algebra derived ratios/products (formulas verified letter-for-letter against source), and a
  41-element hashed fingerprint enabling cross-run/cross-document structural comparison. Never
  written back into the measurement cascade. KME is core semantics, not TFP-only; branch usage does
  not change that. (`output_catalog.md` §10, `corners/kme.md`)
- **TRIZ** (contradiction/innovation analytics): a narrow, explicitly-scoped slice of Altshuller's
  framework (3 relation kinds, 4 of 40 principles) applied read-only over the same concept graph,
  exporting three named decision-intelligence products. TRIZ is likewise core analytics rather than
  COBALT-only; some COBALT workflows simply consume it. (§11, `corners/triz_extension.md`)

## 7. What this method does not include

`hesperia/extensions/dynamics/` — a tested, environment-gated alternate calibration/dynamics
subsystem — has no path into either live product surface described above and is therefore not part
of this method as evaluated. See `docs/foundations/corners/field_dynamics.md` and
`docs/publication/NOVELTY_AND_POSITIONING.md`'s "do not overclaim" section.

## 8. Reproducibility pointer

Exact constants, seeds, and version pins needed to reproduce any specific numeric claim from this
method are catalogued in `docs/publication/REPRODUCIBILITY_PACKAGE.md`, not restated here.

Terminology precision rule for publication drafts built from this Methods section: speak in terms
of the math actually implemented. Use **Markov-like** for the deterministic state-sequence stepping
shape in `core/math/core_math.py`, and **Shannon entropy** for the entropy measures; do not upgrade
those claims to fitted Markov models or Kolmogorov-complexity machinery unless the codebase
actually changes to implement them.

## Navigation

← [`../README.md`](../README.md) (start here) · [`../iso/DOCUMENTATION_TRACEABILITY_MATRIX.md`](../iso/DOCUMENTATION_TRACEABILITY_MATRIX.md) (master registry)
Related: [`NOVELTY_AND_POSITIONING.md`](NOVELTY_AND_POSITIONING.md) (what's novel about this method) · [`VALIDATION_EVIDENCE.md`](VALIDATION_EVIDENCE.md) (what's actually proven to work) · [`REPRODUCIBILITY_PACKAGE.md`](REPRODUCIBILITY_PACKAGE.md) (constants/seeds/pins) · [`../foundations/output_catalog.md`](../foundations/output_catalog.md) (full per-layer variable detail behind §3)
