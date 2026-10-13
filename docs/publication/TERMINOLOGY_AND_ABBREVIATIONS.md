# Terminology and abbreviations (academic nomenclature register)

A paper cannot assume a reviewer already knows what `FGR`, `USF`, or `KDI` stand for, and this
documentation program cannot either — every abbreviation used across `docs/foundations/`,
`docs/iso/`, and `docs/publication/` is registered here, once, with its verification status. This
is the single nomenclature table a paper's "Terminology" or "Notation" section should be built
from; do not re-expand an abbreviation ad hoc in a new document without checking here first.

## How to read the `Status` column

- **VERIFIED** — the full expansion is stated explicitly in source code, a spec, or an existing
  `docs/foundations/` file. Citation given.
- **INFERRED** — the abbreviation is used consistently and its meaning is unambiguous from context
  (formula, usage pattern, surrounding spec text), but no file spells out the expansion in words.
  Flagged so a co-author can confirm rather than have it silently asserted as fact.
- **PROPOSED** — a candidate expansion offered where none exists anywhere, specifically because a
  reviewer will ask and "no one ever named it" is not an acceptable answer in a publication. Marked
  for the author's explicit accept/reject, not asserted as established terminology.
- **UNRESOLVED** — genuinely unclear; do not use in a publication without resolving first.

## 1. Pipeline and architecture

Productization-language note: terms such as `accountable AI`, `deterministic validation`, `forced
adoption market`, and `status quo competitor` are **verified as repo terminology**, but specifically
as a **dated Upcelerator-derived wording layer**. When used outside the productization docs, route
them back through `UPCELERATOR_SOURCE_MAP.md` and, where relevant, `METHODS.md` or
`VALIDATION_EVIDENCE.md` so wording does not outgrow evidence.

| Abbreviation | Expansion | Status | Source |
|---|---|---|---|
| L1–L11 | Layer 1 through Layer 11 (the numbered pipeline stack; L1–L9 canonical math, L10 declared placeholder, L11 the fpf_bridge) | VERIFIED | `docs/foundations/00_INDEX.md`, `output_catalog.md` |
| Core / TFP / COBALT / MRT | Not abbreviations — branch-scope names: core = sealed engine, TFP and COBALT = branch applications on top of core, MRT = closed branch on a different grid | VERIFIED | `AGENTS.md`, `docs/foundations/agentic_orientation.md` |
| LLM | Large Language Model | VERIFIED | standard field term, used throughout |
| USF | Universal Structural Fingerprint | VERIFIED | `corners/interpretation_usf.md`, `specs/canon/usf_schema.json` |
| BFS | Breadth-First Search | VERIFIED | standard graph-theory term; L2 traversal (`corners/topology_geometry.md`) |
| E2E | End-to-End | VERIFIED | `runtime/pipeline/run_e2e_all.py`, used throughout release docs |
| API | Application Programming Interface | VERIFIED | standard term |
| HTTP | HyperText Transfer Protocol | VERIFIED | standard term |
| CLI | Command Line Interface | VERIFIED | standard term |
| JSON / YAML | JavaScript Object Notation / YAML Ain't Markup Language | VERIFIED | standard data-format terms |
| MVP | Minimum Viable Product | VERIFIED | standard product-development term, used in this session's own framing |
| accountable AI | Not an abbreviation — productization shorthand for AI outputs that can be justified, audited, and traced rather than merely generated | VERIFIED (as repo productization wording) | `UPCELERATOR_PRODUCTIZATION_QA.md` |
| deterministic validation | Not an abbreviation — product/category phrasing for Hesperia's source-side deterministic checking and report generation | VERIFIED (as repo productization wording) | `UPCELERATOR_PRODUCTIZATION_QA.md` |
| audit trace / evidence-grade audit trace | Not an abbreviation — buyer-facing wording for the evidence/provenance chain attached to a governed result | VERIFIED (as repo productization wording) | `UPCELERATOR_PRODUCTIZATION_QA.md`, `fpf_bridge`/router docs |
| forced adoption market | Not an abbreviation — productization shorthand for a market whose demand is driven by regulation, risk, and compliance pressure rather than discretionary hype | VERIFIED (as dated Upcelerator market wording) | `UPCELERATOR_SOURCE_MAP.md`, `UPCELERATOR_MARKET_AND_COMPETITION.md` |
| reactive paradigm | Not an abbreviation — Upcelerator competition label for post-hoc AI systems that monitor, evaluate, and explain outputs after generation | VERIFIED (as dated Upcelerator competition wording) | `UPCELERATOR_MARKET_AND_COMPETITION.md` |
| deterministic paradigm | Not an abbreviation — Upcelerator competition label for source-side systems that define, map, and guarantee meaning rather than only score outputs after the fact | VERIFIED (as dated Upcelerator competition wording) | `UPCELERATOR_MARKET_AND_COMPETITION.md` |
| status quo competitor | Not an abbreviation — the real incumbent framed in the archive as manual review, tolerated uncertainty, and "good enough" LLM usage rather than a named startup | VERIFIED (as dated Upcelerator competition wording) | `UPCELERATOR_MARKET_AND_COMPETITION.md` |

## 2. Governance and guard vocabulary

| Term | Expansion | Status | Source |
|---|---|---|---|
| Sigma / Gamma / Theta | **Not abbreviations** — Greek-letter codenames for three categorically distinct guard verdicts (static shape / dynamic execution-order / release-governance). Confirmed **not** derived from FPF's own "Γ (Gamma)" aggregation operator despite the shared letter. | VERIFIED (as codenames, not acronyms) | `corners/guards.md`, `provenance.md`'s explicit non-derivation note |
| FGR | Formality, Ground/Scope, Reliability | VERIFIED | `provenance.md` — FPF Part B.3, "Trust & Assurance Calculus" |
| FPF | First Principles Framework | VERIFIED | `provenance.md` — external, authored by Anatoly Levenchuk |
| fpf-thinking-map | Not an acronym — a PyPI package name (the Hesperia/Felix-side engineering artifact operationalizing FPF as executable Python) | VERIFIED | `provenance.md` |
| agentic bridge | Not an acronym — shorthand for `runtime/agentic_bridge/`, the external-agent, read-only wrapper around Layer 11 | VERIFIED | `AGENTS.md`, `specs/canon/fpf_bridge_v7_3_agentic_cursor_interface.md` |
| NFR / FR | Non-Functional Requirement / Functional Requirement | VERIFIED | `docs/iso/REQUIREMENTS_SPECIFICATION.md` (this documentation program's own convention, ISO/IEC/IEEE 29148-standard usage) |
| SQuaRE | Software Quality Requirements and Evaluation | VERIFIED | ISO/IEC 25010's own name for its model family, used in `docs/iso/QUALITY_MODEL.md` |
| LTS | Long-Term Support | VERIFIED | standard industry term, this documentation program's own framing |

## 3. L1 profile-mode vocabulary (34_SPEC N1)

| Abbreviation | Expansion | Status | Source |
|---|---|---|---|
| FPD | Family Profile Deviation | VERIFIED | `docs/specs/history/34_SPEC_N1__...txt` §7.1 (spelled out in prose) |
| APD | Area Profile Deviation | VERIFIED | same spec, §7.2 |
| FMP | Forbidden Mass Penalty | VERIFIED | same spec, §7.3 |
| ALTD | Altitude Deviation | VERIFIED | same spec, §7.4 |
| BVS | Budget Violation Score | VERIFIED | same spec, §7.5 |
| PCS | Profile Conformance Score | VERIFIED | same spec, §7.6 |
| FEDV | Family Expected Distribution Vector | **INFERRED** | Used as `FEDV[f]`, constrained `Σ FEDV ≈ 1` (a probability distribution over families) in `34_SPEC_N1`, but the spec never spells out the words — inferred from usage, not stated |
| AEDV | Area Expected Distribution Vector | **INFERRED** | Same pattern as FEDV, at area grain — same caveat |

## 4. KME (Knowledge Metrics Engine) — six primitives, verified

| Abbreviation | Expansion | Status | Source |
|---|---|---|---|
| KME | Knowledge Metrics Engine | VERIFIED | `corners/kme.md` |
| LD | LogicalDensity | VERIFIED | `core/domain/models.py` inline comment, `corners/kme.md` |
| COH | Coherence | VERIFIED | same |
| NC | NodeCoverage | VERIFIED | same |
| PR | PropagationRadius | VERIFIED | same |
| PV | PropagationVolume | VERIFIED | same |
| CI | ConcentrationIndex | VERIFIED | same — **disambiguation note:** "CI" elsewhere in software engineering commonly means Continuous Integration; within KME context it is always ConcentrationIndex. Qualify on first use in any document that discusses both. |

## 5. KME derived metrics (35 codes) — the open item this glossary exists to surface

**None of the 35 derived-metric codes have a stated full-word expansion anywhere in the codebase or
documentation** — verified by direct source read of `core/domain/derived_metrics.py` and
`corners/kme.md`; only `KSI` has any documented gloss at all ("KME-KSI-score," disambiguated from
"KSI-Inspector," `provenance.md`), and even that names the metric, not what K/S/I individually stand
for. This is exactly the situation the operator flagged: undefined abbreviations that will surface
as reviewer questions in a publication. Below are the 35 codes, their exact formulas (verified
letter-for-letter against `derived/calculator.py`), and a **PROPOSED** candidate expansion for each
— offered for author accept/reject, not asserted:

| Code | Formula (verified) | Proposed expansion (unverified — needs author decision) |
|---|---|---|
| `KDI` | `LD × COH` | Knowledge Density Index |
| `CSI` | `NC × PR` | Coverage-Spread Index |
| `SPI` | `CI` (direct) | Spread/Propagation Index |
| `TDS` | `PR × LD` | Traversal Density Score |
| `SSS` | `COH / PV` | Structural Support Score |
| `KCI` | `LD / PR` | Knowledge Concentration Index |
| `CCI` | `COH × NC` | Coherent Coverage Index |
| `SPS` | `PR × COH` | Spread-Propagation Score |
| `DCI` | `LD × NC` | Density-Coverage Index |
| `CSI2` | `CI × LD` | Concentration-Structure Index (2) |
| `KEF` | `PV / NC` | Knowledge Efficiency Factor |
| `ASS` | `(COH × LD) / PV` | Aggregate Structural Score |
| `CDR` | `PR / NC` | Coverage-Depth Ratio |
| `KCR` | `LD / NC` | Knowledge Concentration Ratio |
| `TCI` | `COH × LD × CI` | Triple Composite Index |
| `PEI` | `PR / PV` | Propagation Efficiency Index |
| `KE` | `PR / LD` | Knowledge Extent |
| `SCS` | `(LD × COH) / NC` | Structural Coherence Score |
| `CRI` | `CI × COH` | Concentration-Reinforcement Index |
| `KNS` | `NC × COH × LD` | Knowledge Network Score |
| `CII` | `NC / PR` | Coverage-Intensity Index |
| `TEP` | `PV × LD` | Total Energy Product |
| `KSI` | `(COH × LD) / PR` | Knowledge Structural Index (existing gloss: "KME-KSI-score," `provenance.md`) |
| `CDD` | `NC / PV` | Coverage-Density Delta |
| `SSR` | `PR / PV` | Spread-Support Ratio |
| `TER` | `CI / LD` | Tension-Efficiency Ratio |
| `CPC` | `(PR × NC) / PV` | Composite Propagation Coefficient |
| `KBS` | `(COH × NC) / PV` | Knowledge Balance Score |
| `TRI` | `(CI × LD) / PR` | Tension-Reinforcement Index |
| `IDE` | `(PR × COH) / NC` | Intensity-Depth Efficiency |
| `KPS` | `COH / PR` | Knowledge Propagation Score |
| `TBI` | `NC × PV` | Total Breadth Index |
| `KDI2` | `LD × PR × COH` | Knowledge Density Index (2) |
| `CDI` | `CI × NC` | Concentration-Distribution Index |
| `KVI` | `(LD × COH × PR) / PV` | Knowledge Value Index |

**None of the above 35 proposed expansions should be cited in a publication draft until the
project's own author(s) confirm or replace them.** They are offered as a starting point for a
one-time terminology-fixing pass, not as this documentation program's independent claim about what
the codes mean.

## 6. TRIZ vocabulary

| Term | Expansion | Status | Source |
|---|---|---|---|
| TRIZ | Teoriya Resheniya Izobretatelskikh Zadatch (Russian) — Theory of Inventive Problem Solving | VERIFIED | Standard external field name (Genrich Altshuller), `provenance.md`, `corners/triz_extension.md` |
| `LOUVAIN_SEED` | Not an abbreviation — Louvain is the algorithm's proper name (Blondel et al.'s modularity-maximization method, named for the University of Louvain) | VERIFIED | `parameter_catalog.md` §7 |

## 7. Metric registry / deferred formalization vocabulary

| Term | Expansion | Status | Source |
|---|---|---|---|
| GCS | Geodesic Sphere | VERIFIED | `provenance.md` |
| IPoW | Interior Point of World View | VERIFIED | `provenance.md` |
| BELL (`path_mass`) | Not resolved to a full expansion in any available source — a named, specified-but-unbuilt metric ("BELL_research SPEC") | UNRESOLVED | `provenance.md` — flagged there as "specified, not built"; do not expand without checking the (unrecovered) originating spec first |
| KSI-Inspector | Not an abbreviation of a phrase — a tool name, "KSI" here referring to the derived metric it inspects, distinct from the metric itself | VERIFIED (as a name, not an acronym) | `provenance.md`'s disambiguation note |

## 8. Evidence retrieval vocabulary (L4/L5, standard information-retrieval field terms)

| Abbreviation | Expansion | Status | Source |
|---|---|---|---|
| BM25 | Best Matching 25 | VERIFIED | Standard IR ranking function name; `core/layers/layer_4.py`'s `RETRIEVAL_MODE_ID = "LEX_BM25_V1"` |
| TF-IDF (referenced in BM25's lineage, not a separate Hesperia constant) | Term Frequency – Inverse Document Frequency | VERIFIED | Standard IR term |
| MRR | Mean Reciprocal Rank | INFERRED | `00_INDEX.md`'s L4 summary says "MRR-weighted alignment" without spelling it out; standard IR term, high-confidence inference |

## 9. Domain/corpus vocabulary

| Abbreviation | Expansion | Status | Source |
|---|---|---|---|
| TFP | Transference-Focused Psychotherapy | VERIFIED | `corners/corpus_wiring.md`: "TFP (Transference-Focused Psychotherapy) session-shaped text" |
| KL (divergence) | Kullback-Leibler (divergence) | VERIFIED | Standard information-theory term; `provenance.md` — explicitly one of the formalisms that did **not** survive into the shipped Core Math Contract |

## 10. Release/spec identifiers — proper-noun codes, not expandable abbreviations

| Term | What it actually is | Status | Source |
|---|---|---|---|
| `HSR-V7` | A project/campaign code prefix (`HSR-V7-2026-REGISTER`) — likely "Hesperia" + version marker, but no file spells out what "HSR" stands for | UNRESOLVED | Referenced in memory/campaign docs on the `hsr-v7-router-implementation` branch, not in `main`'s checked-out tree |
| `HSPR-01`/`HSPR-02` | Spec IDs on `docs/ENGINE-ANALYZE-CONTRACT.md` — likely a "Hesperia" prefix code, no expansion stated | UNRESOLVED | `docs/ENGINE-ANALYZE-CONTRACT.md` |
| `NN_SPEC` (e.g. `34_SPEC`) | Not an abbreviation — a sequential numbering convention for canonical specs, per `docs/DOC_INDEX.md`'s numbering scheme | VERIFIED (as a convention, not an acronym) | `00_INDEX.md`'s era narrative |
| T1–T20 | Modular kernel workflow gate task numbers (T1–T10, then T11–T20) | VERIFIED (as a numbering scheme) | `00_INDEX.md`'s "hesperia-engine-dynamics-v0.5.x" era |
| B0 / B1 | Dict B build tiers: B0 (fallback), B1 (hard-gated) | VERIFIED | `00_INDEX.md`'s v0.4.1_clean era summary |
| ACB / BAC | The two build directions for Dict C: ACB (corpus-driven, i.e. A→C→B direction) and BAC (concept-recovery, B→A→C direction) | INFERRED | `00_INDEX.md`'s corner summary for `lexicon_resolver.md` names both directions but does not spell out what each letter-order stands for beyond the A/B/C dictionary tiers already defined elsewhere |

## Maintenance rule

This glossary is registered in `docs/iso/DOCUMENTATION_TRACEABILITY_MATRIX.md`. Two obligations:
1. Any new document in this program that introduces an abbreviation not listed here must add a row
   before being marked `built` in the traceability matrix — an unregistered abbreviation is the same
   class of gap this glossary itself was created to close.
2. The §5 PROPOSED expansions and the three UNRESOLVED terms (§7's BELL, §10's `HSR`/`HSPR`) are
   this document's own open items — resolving them (by author confirmation or by locating the
   originating spec) is a follow-up task, not a defect in this glossary's completeness as a first
   pass.

## Navigation

← [`../README.md`](../README.md) (start here) · [`../iso/DOCUMENTATION_TRACEABILITY_MATRIX.md`](../iso/DOCUMENTATION_TRACEABILITY_MATRIX.md) (master registry)
Related: [`SCIENCE.md`](SCIENCE.md) (borrowed-science names, as distinct from this document's coined identifiers) · [`../foundations/corners/kme.md`](../foundations/corners/kme.md) (the 6 primitives and 35 derived metrics §4–§5 catalogue) · [`../foundations/output_catalog.md`](../foundations/output_catalog.md) §10 (where the derived-metric codes actually surface)
