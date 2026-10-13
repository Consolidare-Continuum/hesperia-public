# Start here: three documentation tiers, one source of truth

This file exists for fast orientation — human or agent — before diving into any specific document.
Read this, then jump directly to what you need; you should not need to read all three tiers in
full for most tasks.

## The three tiers, in dependency order

```
docs/foundations/   ← engineering reasoning, source-verified. Everything else cites this.
      ↑
docs/iso/           ← standards-mapped project documentation, cites foundations/
      ↑
docs/publication/   ← scientific-publication track, cites foundations/ (and sometimes iso/)
```

**Rule:** claims flow downward only. `docs/iso/` and `docs/publication/` never introduce a new
factual claim about the system without citing the `docs/foundations/` file it traces to. If you're
about to write a new fact in `iso/` or `publication/`, check `foundations/` first — it's probably
already there.

**Productization-language rule:** buyer-facing phrases such as `accountable AI`,
`deterministic validation`, `evidence-grade audit trace`, `forced adoption market`, or
`status quo competitor` live in the publication/productization docs as a **dated companion
vocabulary**. Use them to make Hesperia legible, not to smuggle in uncited technical claims.

## Fastest entry points by task

| If you need to... | Start at |
|---|---|
| Understand the whole system, top-down | [`foundations/00_INDEX.md`](foundations/00_INDEX.md) |
| Start an agentic/code-aware cold run safely | [`foundations/agentic_orientation.md`](foundations/agentic_orientation.md) |
| Find every calibration constant and what it does to the output | [`foundations/parameter_catalog.md`](foundations/parameter_catalog.md) |
| Defend why a parameter has its value and what theory family it comes from | [`foundations/parameter_rationale_and_theory.md`](foundations/parameter_rationale_and_theory.md) |
| Find every user/LLM-facing output variable | [`foundations/output_catalog.md`](foundations/output_catalog.md) |
| Check what's canonical/cited vs. Hesperia-native | [`foundations/provenance.md`](foundations/provenance.md) |
| See the master registry of every ISO/publication document, its status, and its verification commit | [`iso/DOCUMENTATION_TRACEABILITY_MATRIX.md`](iso/DOCUMENTATION_TRACEABILITY_MATRIX.md) |
| Understand system architecture by stakeholder viewpoint | [`iso/ARCHITECTURE_DESCRIPTION.md`](iso/ARCHITECTURE_DESCRIPTION.md) |
| Close questions about whole-project purpose / when Hesperia is cyber-safe | [`iso/PURPOSE_AND_CYBER_SAFETY_STATEMENT.md`](iso/PURPOSE_AND_CYBER_SAFETY_STATEMENT.md) (Referat **348**) |
| Check what's required, functionally and non-functionally | [`iso/REQUIREMENTS_SPECIFICATION.md`](iso/REQUIREMENTS_SPECIFICATION.md) |
| Integrate against `/analyze` or `/product/interpret` | [`iso/OPERATOR_GUIDE.md`](iso/OPERATOR_GUIDE.md) |
| Build a buyer-facing deterministic validation report or evidence-grade audit trace | [`iso/OPERATOR_GUIDE.md`](iso/OPERATOR_GUIDE.md), then [`publication/VALIDATION_EVIDENCE.md`](publication/VALIDATION_EVIDENCE.md) |
| State the novelty claim for a paper (innovation, not invention) | [`publication/NOVELTY_AND_POSITIONING.md`](publication/NOVELTY_AND_POSITIONING.md) |
| Get the time-bounded productization / MVP / buyer-language orientation | [`publication/UPCELERATOR_PRODUCTIZATION_QA.md`](publication/UPCELERATOR_PRODUCTIZATION_QA.md) |
| Translate Hesperia into accountable-AI / buyer-language terms without losing technical discipline | [`publication/UPCELERATOR_PRODUCTIZATION_QA.md`](publication/UPCELERATOR_PRODUCTIZATION_QA.md), then [`publication/METHODS.md`](publication/METHODS.md) |
| Trace which Upcelerator files said what and how their claims may be reused | [`publication/UPCELERATOR_SOURCE_MAP.md`](publication/UPCELERATOR_SOURCE_MAP.md) |
| Reuse the dated market/competition baseline without laundering it into timeless truth | [`publication/UPCELERATOR_MARKET_AND_COMPETITION.md`](publication/UPCELERATOR_MARKET_AND_COMPETITION.md) |
| Reuse the regulation-driven / forced-adoption / status-quo-competitor framing | [`publication/UPCELERATOR_MARKET_AND_COMPETITION.md`](publication/UPCELERATOR_MARKET_AND_COMPETITION.md) |
| Cite the exact scientist/work behind a specific formula | [`publication/SCIENCE.md`](publication/SCIENCE.md) |
| Look up what an abbreviation means | [`publication/TERMINOLOGY_AND_ABBREVIATIONS.md`](publication/TERMINOLOGY_AND_ABBREVIATIONS.md) |
| Reproduce a specific numeric claim | [`publication/REPRODUCIBILITY_PACKAGE.md`](publication/REPRODUCIBILITY_PACKAGE.md) |

## Full tier contents

### `foundations/` — engineering reasoning (pre-existing, source-verified)

Entry point: [`foundations/00_INDEX.md`](foundations/00_INDEX.md), which itself indexes 22 corner
docs, 11 layer docs, 8 era docs, and the reference/catalog files. Do not re-list them here —
`00_INDEX.md`'s own "Map of the rest of this package" section is the authoritative index and this
file would drift from it if duplicated. The companion agentic entrypoint is
[`foundations/agentic_orientation.md`](foundations/agentic_orientation.md): read that when the job
is "work in the repo safely" rather than "learn the architecture from bedrock." The companion
parametric-academic entrypoint is
[`foundations/parameter_rationale_and_theory.md`](foundations/parameter_rationale_and_theory.md).
For buyer-language or productization routing, foundations is bedrock, not the final stop — hand
off into `publication/` once the engineering claim is understood.

### `iso/` — standards-mapped project documentation

| Document | Standard | Status |
|---|---|---|
| [`DOCUMENTATION_TRACEABILITY_MATRIX.md`](iso/DOCUMENTATION_TRACEABILITY_MATRIX.md) | ISO/IEC/IEEE 15289 | Master registry — check here first for what's built vs. open |
| [`ARCHITECTURE_DESCRIPTION.md`](iso/ARCHITECTURE_DESCRIPTION.md) | ISO/IEC/IEEE 42010 | 7 viewpoints + Appendix A (exhaustive corner/layer/era register) |
| [`REQUIREMENTS_SPECIFICATION.md`](iso/REQUIREMENTS_SPECIFICATION.md) | ISO/IEC/IEEE 29148 | FR/NFR traced to exact invariant IDs |
| [`QUALITY_MODEL.md`](iso/QUALITY_MODEL.md) | ISO/IEC 25010 (SQuaRE) | 8 characteristics; Security cites conditional L1–L6 / Referat 348 evidence |
| [`LIFECYCLE_PROCESS.md`](iso/LIFECYCLE_PROCESS.md) | ISO/IEC/IEEE 12207 | Formalizes the existing seal/release discipline |
| [`OPERATOR_GUIDE.md`](iso/OPERATOR_GUIDE.md) | ISO/IEC/IEEE 26511/26512 | Practical `/analyze` vs. `/product/interpret` guidance |
| [`PURPOSE_AND_CYBER_SAFETY_STATEMENT.md`](iso/PURPOSE_AND_CYBER_SAFETY_STATEMENT.md) | — (closing statement) | Descriptions → purpose; cyber-safe only under named evidence (Referat **348**) |
| [`evidence/REFERAT-348-….pdf`](iso/evidence/REFERAT-348-legislatie-cibernetica-licentiere-module-ULIM-2026-10-12.pdf) | Operator research PDF | ULIM whitepaper bound into ISO evidence |

### `publication/` — scientific-publication track

| Document | Purpose | Status |
|---|---|---|
| [`NOVELTY_AND_POSITIONING.md`](publication/NOVELTY_AND_POSITIONING.md) | The invention-vs-innovation statement - cite, don't re-argue | Load-bearing; read first in this tier |
| [`UPCELERATOR_PRODUCTIZATION_QA.md`](publication/UPCELERATOR_PRODUCTIZATION_QA.md) | Dated productization, MVP, and buyer-language orientation from Upcelerator 2026 source material | Time-bounded truth layer; preserve wording, keep caveats |
| [`UPCELERATOR_SOURCE_MAP.md`](publication/UPCELERATOR_SOURCE_MAP.md) | Canonical intake map for the Upcelerator 2026 archive, with evidence classes and propagation rules | Use before spreading archive wording further |
| [`UPCELERATOR_MARKET_AND_COMPETITION.md`](publication/UPCELERATOR_MARKET_AND_COMPETITION.md) | Dated market boundary, TAM/SAM/SOM logic, and competition framing from the plain-text Upcelerator set | Productization baseline; keep assumptions attached |
| [`SCIENCE.md`](publication/SCIENCE.md) | ~35 named scientific/engineering works, 11 disciplines, 5-level extent taxonomy | The citation register beneath `NOVELTY_AND_POSITIONING.md` |
| [`TERMINOLOGY_AND_ABBREVIATIONS.md`](publication/TERMINOLOGY_AND_ABBREVIATIONS.md) | Every abbreviation, verified/inferred/proposed/unresolved | 35 KME metric codes flagged PROPOSED, pending author confirmation |
| [`METHODS.md`](publication/METHODS.md) | Paper-shaped pipeline description | |
| [`VALIDATION_EVIDENCE.md`](publication/VALIDATION_EVIDENCE.md) | What's actually provable, cited exactly (76 tests re-run, exit 0) | |
| [`REPRODUCIBILITY_PACKAGE.md`](publication/REPRODUCIBILITY_PACKAGE.md) | Pins, seeds, tolerances — read fresh from `VERSION.yaml` each time | Caught and fixed one stale pin example in `foundations/corners/calibration.md` |

## For an agent picking up this project cold

1. Read this file.
2. Read [`foundations/agentic_orientation.md`](foundations/agentic_orientation.md) if you are about
   to act broadly as an agent; read [`foundations/00_INDEX.md`](foundations/00_INDEX.md) if you
   need system understanding. For a single narrow fact, use the table above instead.
3. Read [`iso/DOCUMENTATION_TRACEABILITY_MATRIX.md`](iso/DOCUMENTATION_TRACEABILITY_MATRIX.md) to
   see what's `built` vs. still `todo`/`draft`, and each document's last-verified commit — if your
   `HEAD` has moved past that commit for a row you're about to rely on, re-verify before trusting it.
4. Before adding a new fact anywhere in `iso/` or `publication/`, check whether `foundations/`
   already states it — cite, don't re-derive.
5. Before adding a new abbreviation, check
   [`publication/TERMINOLOGY_AND_ABBREVIATIONS.md`](publication/TERMINOLOGY_AND_ABBREVIATIONS.md)
   first; before citing a scientific work, check
   [`publication/SCIENCE.md`](publication/SCIENCE.md) first.
6. Before spreading any Upcelerator-derived market or buyer-language claim, classify it first in
   [`publication/UPCELERATOR_SOURCE_MAP.md`](publication/UPCELERATOR_SOURCE_MAP.md) so dated
   framing, estimates, and open hypotheses do not silently blend together.
7. Register anything new in the traceability matrix before considering it done.
