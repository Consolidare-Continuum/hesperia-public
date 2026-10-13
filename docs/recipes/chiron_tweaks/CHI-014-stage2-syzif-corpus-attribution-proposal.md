# CHI-014 — Stage 2 (syzif corpus → core Dict A/B/C attribution): readiness call + build proposal, not implemented

## 1. Task/goal

Operator judgment call, 2026-09-02: the syzif corpus (`hesperia/modules/default/corpus/syzif/`)
is **judged trustworthy enough** to start Stage 2 — the term/family attribution + Dict A/B/C
rebuild named as unbuilt in `docs/foundations/genesis_taxonomy_provenance.md` since 2026-07-30 and
tracked as the top open item in `BACKLOG.md`. This entry is Chiron's required output for that
call (§5b feature theorizing — new capability, not a documented-parameter toggle, so proposed
here and built by Felix/Gena after Grace triage, not implemented by Chiron directly per spec §5).

**Execution plan**: [STAGE-2-BUILD-PLAN.md](STAGE-2-BUILD-PLAN.md) — the clean, repeatable
what/why/operate-from-it plan for whoever builds this, cross-linked from here so this doc stays
the evidence trail and that one stays the checklist.

## 2. Readiness basis (why "trustworthy enough" is defensible, stated with the actual numbers)

- 119/120 books structurally + word-level grinded, each tier carrying a stated, sampled residual
  error rate (`BACKLOG.md`, 2026-08-31 day-close entry) — not claimed perfect, but not silent
  either. Known accepted defects are small and catalogued (a few real alternate spellings
  "corrected," one meaning-inverting split, a couple of wrongly-split compounds).
- **2026-09-04 correction (Chiron)**: the line below originally proposed excluding
  *Moral Boundaries* (Tronto, doubled/garbled extraction end to end,
  `[UNRELIABLE-NEEDS-REEXTRACTION]`) from `corpus_dir` scope via a filter. On operator instruction
  it has instead been **removed outright** from `hesperia/modules/default/corpus/syzif/` (`git rm`,
  dev repo, recoverable from git history). **The corpus is now 119 books, permanently, gap at
  position #85** — not 119/120 pending a scope filter. This closes the exclusion item below: there
  is no longer a file to filter. 119 is the standing corpus size.
- Mirror-sync bug that could have left corpus drift between dev/CC prod is fixed at the source
  (`mirror-atomic-to-cc-srl.sh`, brain repo `3dfbf780`) and re-verified in sync 2026-09-01 — Stage
  2 work happens on the dev remote (`igareosh/hesperia`) regardless, so this isn't a hard blocker,
  but it removes a reason to distrust which corpus state is "the" corpus.
- Genuinely still open, not blocking but worth carrying into the build: short-token class
  (`fix_ocr_word_errors_llm.py`, 24,887 applied) was never re-audited with the offset-safe method
  the long-run pass got; the progress-file offset-drift issue means "how clean is it really" can't
  be answered from the progress JSONL alone, only a fresh scan. Neither of these is a reason to
  wait — they bound the corpus's residual error rate, they don't invalidate an attribution pass
  built to be re-runnable.

## 3. Correction to the existing "not built" claim — the extraction half already exists, generically

`genesis_taxonomy_provenance.md` §"What's still open (Stage 2, not built)" currently states: *"No
PDF/epub/docx extraction tooling and no term→family attribution tooling exist anywhere in the
repo today."* That was accurate in 2026-07-30 when written against the raw `books sphere list/`
source files. It is **no longer accurate for the extraction half**, for two independent reasons:

1. The corpus itself changed state since that line was written — `hesperia/modules/default/corpus/syzif/`
   is now pre-converted Markdown (the 2026-08-31 grind), not raw PDF/epub/docx. PDF/epub extraction
   is no longer the blocking step at all.
2. `tools/dict_calibration/` already contains a generic, corpus/catalog-agnostic ACB pipeline —
   confirmed by reading the actual function signatures, not assumed from the doc that describes
   the pattern (`docs/foundations/corners/lexicon_resolver.md` §"How Dict C is built"):
   - `extract_lexical.py::extract_corpus(corpus_dir, min_freq=2, max_ngram_types=200_000)` — walks
     `*.md` under `corpus_dir` directly, frequency-filtered n-grams up to 5 tokens. Takes a path,
     not a hardcoded corpus.
   - `normalize_llm.py::normalize_batch(rows, batch_size=24)` — LLM canonicalization of raw
     n-gram rows, no TFP-specific input.
   - `propose_llm.py::propose_concepts(normalized_rows, dict_b_rows, max_concepts=80, ...)` —
     takes the **target concept catalog as a parameter** (`dict_b_rows`), not imported from
     `hesperia/modules/tfp/`. Pointing this at a core Dict B catalog instead of TFP's is a
     parameter, not a rewrite.
   - `anchor_bind.py::anchor_drafts(drafts, concept_index, anchor_registry, ...)` — same: binds
     against whatever `concept_index` is passed in.

   This tooling lives under `tools/dict_calibration/`, not under `hesperia/modules/tfp/` or
   `research/clinical_tfp/` — **reusing it does not violate the operator's "no dependency on or
   reuse of the TFP module" instruction** (`genesis_taxonomy_provenance.md` §"What's still open"),
   because that instruction is about the TFP *module* (concepts, corpus, dictionaries), not this
   generic tool library. This reading should be confirmed by Felix/Gena before building, not
   assumed final by this proposal alone — flagging it explicitly rather than deciding it
   unilaterally, since it's an architecture-boundary question (§1 out-of-scope for Chiron).

   **2026-09-04 correction (Chiron)**: "generic" above is true of the **function signatures**
   only — checked further, it is false of the **prompt content**. `normalize_llm.py`'s `SYSTEM`
   string reads verbatim *"You normalize **clinical / psychodynamic** surface text... preserve
   **psychological** meaning"*; `propose_llm.py`'s reads *"You map lexical phrases (**Russian
   and/or English clinical / TFP discourse**)... use dotted ids like **tfp.domain.name**."* Both
   are hardcoded to the TFP domain and TFP's ID convention, not parameterized. Two separate
   consequences, not one:
   - `normalize_batch` is very likely **not worth running at all** against syzif — its actual job
     (aggressive filler removal, speech-disfluency collapse) is a spoken-transcript problem; the
     119 books are already-published, already-OCR-grinded prose with no filler/disfluency layer
     to strip. Deterministic normalization (case-folding, lemmatization) already happens upstream
     in the engine's frozen `core/lexical/normalization.py`-style layer; an LLM pass over already-
     clean book n-grams buys little and costs real money at 119-books' n-gram volume (the single
     largest row count in the pipeline, per the still-unsized item in §4). Proposed: **skip
     normalize_batch for core/default**, feed `extract_corpus`'s rows straight to concept
     proposal.
   - `propose_concepts` (still needed — the actual concept-mapping step) **cannot run unmodified**:
     its `SYSTEM`/`USER_TEMPLATE` need rewriting for a general 288-family core vocabulary before
     use, or output will be steered toward clinical framing and `tfp.*`-shaped IDs regardless of
     what `dict_b_rows` catalog is passed in. This is real, scoped work — a prompt rewrite, not a
     parameter swap — and changes what "reuse the pipeline" means: reuse the *orchestration*
     (`extract_corpus`/`propose_concepts`/`anchor_drafts` call shape), not the prompt content
     as-is. Still Felix/Gena's call to confirm and scope, not resolved here.

## 4. What's actually missing before this pipeline can run against syzif

- **No core Dict B catalog for the current 288 `AREA_FAMILY_MAP` concepts exists yet.** Checked
  the only candidate on disk, `assets/lexicon/frozen/dict_b_v040_from_a_v0413.json` — it's a
  3,169-row flat word→something table from the v0.4.0 generation, predates both the sealed v0.6.x
  dict shape and the 2026-07-30 genesis taxonomy adoption entirely. It is not usable as
  `dict_b_rows`/`concept_index` for `propose_concepts`/`anchor_drafts` as-is.
  **Real first build step**: synthesize a 288-row seed Dict B (one row per `AREA_FAMILY_MAP`
  family: `concept_id`, `preferred_label` = family name, `family_ids`/`area_ids` from the map's
  own `area_index × 24 + local_index` numbering in `core/topology/invariant_catalog.py`) before
  any corpus alignment can anchor against it. This is mechanical (derived straight from the
  already-sealed `AREA_FAMILY_MAP` dict, no new judgment calls) but is real work, not a config
  toggle — sizing it honestly so it isn't discovered mid-build.
- ~~**Corpus scope filter**: `extract_corpus(corpus_dir=...)` needs to exclude the
  `[UNRELIABLE-NEEDS-REEXTRACTION]` file~~ — **closed 2026-09-04**: the file was removed from the
  corpus rather than filtered, so `extract_corpus` needs no exclusion logic for it.
- **Anchor threshold / concept-catalog size**: TFP's run used `min_score=0.52`,
  `catalog_limit=400`. With only 288 core concepts (smaller, coarser-grained than TFP's ~283
  clinical concepts derived from Russian session transcripts) these defaults are a starting point,
  not a proven fit for this corpus/catalog pairing — first real run should sanity-check anchor
  rate and false-positive rate the same way TFP's Phase 4a-4c did (sampled, not assumed), before
  treating any resulting Dict A/C as ship-ready.
- **`propose_llm.py` prompt rewrite (added 2026-09-04)**: `SYSTEM`/`USER_TEMPLATE` are hardcoded
  to "clinical/TFP discourse" and `tfp.*`-shaped concept IDs (see §3 correction). Needs a
  core/default-domain rewrite before this step can run correctly against the 288-family catalog —
  scoped work, not a parameter change. `normalize_llm.py`'s equivalent problem is resolved by
  skipping that step entirely (see §3), not by rewriting it.

## 5. Config

N/A — no calibration YAML/`DEFAULT_CONFIG` toggle exists for this; it's a new build artifact
(seed Dict B + Dict A/C output files), not a documented-parameter flip. Out of Chiron's §5
direct-edit authority for that reason, consistent with routing this as a proposal.

## 6. Invocation

N/A — spec only, not implemented. Sketch for whoever builds it (not a commitment to this exact
shape): `extract_corpus("hesperia/modules/default/corpus/syzif/")` (no exclusion pattern needed —
the unreliable file is gone, not filtered, as of 2026-09-04) →
~~`normalize_batch(...)`~~ (dropped 2026-09-04 — not worth running against clean book prose, see
§3) → `propose_concepts(normalized_rows, core_dict_b_seed_rows)` **using a core-domain
`SYSTEM`/`USER_TEMPLATE`, not the TFP-hardcoded default** (§4) →
`anchor_drafts(drafts, core_concept_index, core_anchor_registry)` → new Dict C entries, same
format TFP's `v0_6_9/dict_a.jsonl`/`links.jsonl` used, but seeded from the 288-family core catalog
instead of the TFP concept set, and living under its own `assets/calibration/dicts/` version
directory (not mixed into any `v0_6_9`/`tfp_cal_wave` directory — those are TFP-tier, per the
same module-independence instruction this proposal already flagged in §3).

## 7. Expected output shape

A new core-tier Dict B seed (288 rows) + Dict A/C entries anchored against it, sized by however
many of the 288 families the syzif corpus's real n-gram distribution actually covers (TFP's
analogous run covered 134/283 deterministically, 203/283 after LLM alignment — no reason to
assume 288/288 here; report the real number, not a target).

## 8. Validation evidence

None yet — pre-implementation proposal. Once built, same discipline as the TFP Phase 4 runs:
`tools/calibration_release_gate.py` + the existing pytest calibration suite before calling
anything shippable; a real `hesperia_router_inquire face=core` call before/after on a real
document to confirm the new Dict A/C entries are actually reachable through the live caller path,
not just present on disk; full pytest suite run to confirm zero regression on `default`/`clinical_speech`/
`scientific`/`psychodynamic` profiles (none of which should be touched by a core-only Dict
addition).

## 9. Rollback

New files only (seed Dict B, new Dict A/C version directory) — nothing overwrites an existing
sealed dict. Rollback is "don't pin the new version," same mechanism as every prior TFP dict
version swap in this repo.

## 10. Handoff

Per spec §5b: this is a new-capability proposal, not a documented-parameter toggle — Chiron
proposes, does not implement. Routed via `inbox.md` (2026-09-02 entry) → Grace triage → **Felix**
(or Gena) to build, once triaged. Corpus-scope and threshold-tuning judgment calls in §4 are
flagged for whoever builds it, not resolved here.

---
SIGNED: Chiron | Claude Code context (Felix engine) | 2026-09-02 | Stage 2 readiness call + build proposal, not implemented — operator judged the 119/120-grinded corpus trustworthy enough to proceed
