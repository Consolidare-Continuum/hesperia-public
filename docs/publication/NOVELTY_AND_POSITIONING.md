# Novelty and positioning: innovation, not invention

This document exists to be pointed at instead of re-argued. Every later publication-facing document
(`METHODS.md`, `VALIDATION_EVIDENCE.md`) and every paper draft built from this documentation program
should cite this file for its novelty claim rather than restate or embellish it. The claim is
narrow and specific, because a broad or vague novelty claim is the fastest way to lose credibility
with a scientific reviewer who can `grep` the same code we can.

## The claim, stated once

**Hesperia does not introduce new mathematics. It introduces a specific architectural composition —
a deterministic, falsifiable measurement pipeline that must run and be governance-checked
*before* an LLM is allowed to speak, with the LLM's own output then re-measured and audited against
what went in.** The novelty is the composition and the governance boundary, not any single formula
inside it. This is the same distinction `docs/foundations/provenance.md` already draws file-by-file
for licensing/citation purposes; this document draws it once, at the level a reviewer or co-author
needs.

The founding memo's own sentence states the actual contribution better than a paraphrase would:
*"Do not allow raw wording to activate families directly unless routed through resolved concept
evidence or an explicitly marked fallback path."* Everything novel about Hesperia is downstream of
enforcing that one sentence mechanically, across eleven layers, with guards that fail closed.

In productization language, this same contribution can be stated more buyer-legibly, without
changing the technical claim: Hesperia is trying to make AI-assisted output **accountable** by
producing **deterministic validation** and an **audit trace**, rather than asking buyers to trust a
post-hoc explanation layer. The dated GTM wording for that framing lives in
`UPCELERATOR_PRODUCTIZATION_QA.md`; this document keeps the scientific/composition-level version.

## What is canonical (cited, not invented) — the load-bearing honesty check

Verified in `provenance.md`, restated here as the register a publication needs:

| Mechanism | Source | Where Hesperia uses it |
|---|---|---|
| Shannon entropy | Shannon, 1948 | `FAMILY_ENTROPY`/`NORMALIZED_FAMILY_ENTROPY` (L1), `structural_monotony` rule (`specs/canon/diagnostic_rules.yaml`) |
| Gini coefficient | Standard econometrics/inequality measure | `GINI_COEFFICIENT` (L1) |
| BFS graph traversal, clustering coefficient (Watts–Strogatz), circuit rank | Classical graph theory | L2 topology traversal |
| Cauchy–Schwarz, Pythagorean/trig identities, triangle inequality | Classical metric-space axioms | L5's trig/metric-space self-test |
| Markov-like discrete-time state-sequence stepping (explicitly *not* a fitted Markov chain — no learned transition probabilities, no stationary-distribution analysis) | Discrete-time dynamical systems | `core/math/core_math.py`'s `base_step` |
| Mean-field decay, leaky-integrate-and-fire-style energy law | Computational neuroscience / dynamical systems | `compute_h_total` |
| TRIZ (Altshuller) — narrow slice: 3 relation kinds, 4 of the 40 principles, no full 39×39 matrix | Genrich Altshuller, Theory of Inventive Problem Solving | `hesperia/extensions/triz/` |
| Louvain community detection | Blondel et al., modularity maximization | TRIZ innovation clustering, seeded (`LOUVAIN_SEED=42`) for reproducibility |
| FPF (First Principles Framework), FGR trust calculus | Anatoly Levenchuk, external transdisciplinary spec | `sphere/fpf_bridge/` via the `fpf-thinking-map` package |

None of the above is claimed as a Hesperia contribution anywhere in this documentation program.
Citing it as canonical is not a concession — it is what makes the actually-novel part legible: a
reviewer who can verify "yes, that's textbook Shannon entropy" can then evaluate the real claim on
its own terms instead of being asked to take the whole system on faith.

The same honesty applies to branch naming: KME and TRIZ are not publication-safe to describe as
"TFP mechanisms" or "COBALT mechanisms" merely because those branches validated or consumed them
first. They are core semantics with branch-specific applications unless a narrower spec explicitly
says otherwise.

## What is genuinely Hesperia's composition — the actual contribution

1. **The pre-LLM/post-LLM measurement boundary itself.** A deterministic pipeline (L1–L10) produces
   a bounded, replayable structural read of text *before* any LLM call. The LLM is then handed a
   fixed menu of legal next states (`sphere/fpf_bridge/`, Layer 11) — never the raw text, never the
   raw pipeline dict — and whatever it says is re-measured and compared against what went in,
   producing an ALLOW/WARN/REVIEW/BLOCK verdict. Neither the deterministic pipeline nor the guard
   triad borrows this boundary from an external spec; it is the system's organizing decision,
   stated in the founding memo and enforced end-to-end by `sphere/router/`.
2. **The guard triad as a sequenced, categorically-distinct verdict chain.** Sigma (static shape) →
   Gamma (execution-order soundness) → Theta (release/governance eligibility) is a Hesperia-native
   sequencing decision (`corners/guards.md`) — not derived from, and confirmed by direct `grep`
   *not* to overlap with, FPF's own "Γ (Gamma)" aggregation operator despite the shared Greek letter
   (`provenance.md`'s explicit non-derivation note).
3. **Shadow-run divergence as a governed acceptability gate**, not just a robustness metric —
   `SHADOW_DEVIATION_SCORE`'s three-term weighted composite (cosine similarity, symmetric
   difference, dominance delta) and the `SHADOW_ACCEPTABILITY_GATE` boolean it feeds are original
   compositions over standard similarity measures, purpose-built to answer "is this perturbation
   result trustworthy enough to inform the read," which is a domain-specific governance question,
   not a textbook one.
4. **The `contradiction_signal` / `CONTRADICTION_PRESSURE_SCORE` cross-layer thread** — a governance
   signal propagated through lexical, family, and calibration layers as a first-class value rather
   than an incidental side-flag (`eras/04_v0.5.8_contradiction_track.md`), letting the system
   represent "this text argues against itself" as a measured quantity the guard chain can act on.
5. **KME's six-primitive/35-derived-metric fingerprint as a comparability artifact.** The six
   primitives and their pure-algebra derived ratios are a Hesperia-native reduction; nothing here
   claims a new metric *theory*, but the specific choice of six bounded primitives, the
   `clamp01`/`safe_div` failure-handling discipline applied uniformly across all 35 derived metrics,
   and the fixed-order 41-element hashed fingerprint are original engineering decisions that make
   two structural reads comparable in a way no single upstream layer provides on its own
   (`corners/kme.md`). This is a comparability artifact over the core concept graph, not a
   branch-owned metric family.
6. **The FGR-calibrated evidence-primitive handoff to the LLM** — FGR (Formality/Ground/Scope/
   Reliability) itself is FPF's trust calculus (cited above, not invented), but *applying* it as the
   literal permission gate for what an LLM is allowed to narrate at what confidence level, wired
   through `sphere/fpf_bridge/constants.py`'s FGR tables, is Hesperia's application of that calculus
   to this specific problem — the theory is borrowed, the wiring is not.

## What is honestly unresolved or deferred — do not overclaim these

- `hesperia/extensions/dynamics/` (the field-dynamics Phase 1–4 subsystem, `corners/field_dynamics.md`)
  is real, tested, environment-gated code with no path to the current product surface. It is not
  evidence for a publication claim about product behavior until it is actually connected — citing it
  as "part of what Hesperia does" today would be a false claim per this document's own standard.
- The canonical per-layer specs (`34_SPEC`–`42_SPEC`, now restored to `docs/specs/history/`) predate
  and independently corroborate the current code, which strengthens a reproducibility claim — but
  the field-dynamics subsystem's own spec (`ETHAN_SEMANTIC_FIELD_DYNAMICS_SPEC.md`) remains
  unrecoverable from every source checked (`provenance.md`). Do not cite it as an existing document.
- `BELL path_mass` and the full IPoW/GCS formalization are specified but not (yet) built
  (`provenance.md`) — real future work, not present-tense capability.

## How to use this document

- A paper's "Related Work" section starts from the canonical table above, not from a literature
  search redone from scratch — every citation there is already `grep`-verified against running code.
- A paper's "Contribution" section starts from the six-item list above, in that order of
  confidence (items 1–2 are the most defensible architectural claims; items 5–6 are narrower but
  still original engineering decisions).
- Any reviewer or co-author question of the form "isn't this just X well-known technique?" should be
  answerable by pointing at the specific row in the canonical table that already concedes exactly
  that, followed by the specific composition-level claim that remains.
- Any productization or investor-facing restatement of this novelty claim should route through
  `UPCELERATOR_PRODUCTIZATION_QA.md` so the buyer-language layer stays explicitly time-bounded
  instead of silently replacing the scientific wording here.

## Navigation

← [`../README.md`](../README.md) (start here) · [`../iso/DOCUMENTATION_TRACEABILITY_MATRIX.md`](../iso/DOCUMENTATION_TRACEABILITY_MATRIX.md) (master registry)
Related: [`SCIENCE.md`](SCIENCE.md) (the full citation register beneath this document's canonical table) · [`METHODS.md`](METHODS.md) (what the system does, as distinct from what's novel about it) · [`../foundations/provenance.md`](../foundations/provenance.md) (the underlying per-name audit this document's canonical table summarizes)
