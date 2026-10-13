# Stage 2 build plan — syzif corpus → core Dict A/B/C

See also [CHI-015](CHI-015-dict-d-concept-cooccurrence-spec.md) — Stage 9, concept×concept
co-occurrence dictionary ("Dict D"), spec'd at max reliability, sequenced strictly after this
plan's Stage 8 lands (needs a real resolved corpus to count over).

Companion to [CHI-014](CHI-014-stage2-syzif-corpus-attribution-proposal.md), which carries the
full evidence trail (why the extraction-tooling claim was stale, why no core Dict B catalog
exists yet, cost/precedent from the TFP build). This file is the plan itself: what gets built,
why, and what we operate from it once it lands — written to be handed to whoever builds it and
re-run again later, not re-derived from scratch each time.

## Why we're building this

- The core/default lane's only existing Dict A (`assets/lexicon/frozen/v06/dict_a_v06.jsonl`) is
  **confirmed synthetic placeholder data with zero real vocabulary** (found during the 2026-07-30
  genesis-taxonomy safety check, `genesis_taxonomy_provenance.md`). The 288 `AREA_FAMILY_MAP`
  families have names; nothing behind them is grounded in real text.
- The same mechanism, run against TFP's corpus, is proven to work and worth the cost: 0/283 → 134/283
  concepts covered deterministically, → 203/283 after LLM alignment, with measured improvement to
  `zero_lex_share` and raw match counts on live sessions (`BACKLOG.md`, Phase 4a–4c).
- The source corpus for the core lane now exists and is judged trustworthy (119 books grinded and
  clean; the 1 unreliable book, *Moral Boundaries*, was removed outright 2026-09-04 rather than
  filtered — see CHI-014 §2's correction. 119 is the standing corpus size, not 119/120 pending
  anything).
- Every future core-lane calibration pack (`CHI-*`, `params_combo/PC-*`) currently tunes weights
  around an ungrounded dictionary. This is the prerequisite that makes those tweaks measure
  something real instead of adjusting knobs on synthetic data.

## What we build (pipeline stages, in order)

| # | Stage | Input | Output | Tool (exists already) |
|---|-------|-------|--------|------------------------|
| 1 | Core Dict B seed | `AREA_FAMILY_MAP` (`core/topology/invariant_catalog.py`) | 288-row seed: `concept_id`, `preferred_label`=family name, `family_ids`/`area_ids` | none — new, mechanical derivation, no LLM |
| 2 | Corpus extraction | `hesperia/modules/default/corpus/syzif/*.md` (119 books — the unreliable file was removed 2026-09-04, no exclusion pattern needed) | Frequency-filtered n-gram table (up to 5 tokens) | `tools/dict_calibration/extract_lexical.py::extract_corpus()` |
| ~~3~~ | ~~Normalization~~ **dropped 2026-09-04** | — | — | `normalize_llm.py::normalize_batch()` exists but isn't worth running — its job (filler/disfluency removal) is a speech-transcript problem, not a published-book-prose one; skip and feed Stage 2's rows straight to Stage 4 |
| 4 | Concept proposal | Stage 2's rows + Stage 1's seed catalog | Draft phrase→concept bindings | `propose_llm.py::propose_concepts()` — **needs a core-domain `SYSTEM`/`USER_TEMPLATE` rewrite first**; the existing prompt is hardcoded to "clinical/TFP discourse" and `tfp.*`-shaped IDs regardless of which `dict_b_rows` catalog is passed in (found 2026-09-04, see CHI-014 §3/§4) |
| 5 | Anchoring | Stage 4's drafts + Stage 1's concept index | Dict C entries (phrase, exactly one concept, `priority=99`) | `anchor_bind.py::anchor_drafts()` |
| 6 | Merge + version | Stages 1–5 output | New `assets/calibration/dicts/v0_core_syzif_001/` bundle (`dict_a.jsonl`, `dict_b.jsonl`, `dict_c`/`links.jsonl`) — **its own version directory, never mixed into a `tfp_*`/`v0_6_9` directory** | — |
| 7 | Coverage report | Stage 6 | `X/288 families covered`, confidence-tier breakdown | same reporting shape as TFP Phase 4a–4c |
| 8 | Validation gate | Stage 6 | `calibration_release_gate.py` verdict + pytest pass + live before/after `router-inquire` diff | `tools/calibration_release_gate.py`, existing pytest calibration suite |

Stage 1 and Stage 6/7/8 are new glue; stages 2–5 are the existing TFP toolchain pointed at a
different `corpus_dir`/`dict_b_rows` — no new extraction or attribution logic to write.

## Stage 4 design lock (Grace triage 2026-09-04) — fold, not chat-only

**Single LLM touchpoint (accurate description of the landed pipeline):** Stage 2/9 has
exactly one LLM call surface — `propose_concepts`. Normalization is dropped. Anchoring is
deterministic (`anchor_drafts` SequenceMatcher similarity). Dict D (Stage 9) is deterministic
(counting + NPMI/G²). All LLM cost and LLM-induced variance live in that one function.

**Area/family-scoped catalog batching (required change vs today's `propose_llm.py`):**
`_catalog_rows` currently hands each batch a flat truncated catalog (`dict_b_rows[:limit]`,
TFP-era `catalog_limit=400`). For core/default: scope each batch's catalog slice to the
candidate phrase's likely area/family neighborhood. A 288-row seed fits one prompt without
truncation; grouping gives real disambiguation (ORDER phrases must not compete against a
flat list that happens to lead with CHAOS).

**Note them all (audit trail, not automatic):** Persist full raw batch output — every
candidate proposed, accepted or rejected, with stated confidence — to a checkpoint file
regardless of anchor outcome. Today only `min_score` survivors become Dict C; rejected
proposals must still land on disk (`pass_N_proposals_raw.jsonl` or equivalent).

**D operates afterwards — via indirection:** D does **not** read the proposal log. D reads
Stage 2's **resolved corpus** (accepted proposals → Dict C → resolver over real text). The
proposal log is for audit/review; D's input is what survived resolution. Same upstream LLM
step; two different downstream consumers.

## What we operate from it, once it lands


- The live core/default lane (whichever face serves it — confirm the exact `router-inquire`
  face name before build, don't assume) starts returning **real, corpus-grounded concept hits**
  for the 288 families instead of zero/synthetic ones.
- **`X/288` becomes the standing operating baseline** — the number every future default-lane
  calibration claim gets measured against, the same role TFP's `203/283` plays today.
- A **re-runnable pipeline**, not a one-off artifact: when the corpus changes (more books added
  later), stages 2–8 re-run into a new version directory. Nothing
  overwrites the sealed bundle in place — rollback is "don't pin the new version," identical to
  every prior TFP dict-version swap in this repo.
- Real evidence Colombo can cite to correct the Hesperia wiki's LIVE/DEAD status for any of the
  288 families' lexical grounding, instead of the wiki describing family names with no underlying
  text evidence.

## Repeatability discipline (carried over from TFP's own hard-won lessons — don't relearn these)

- Sample-validate every batch on real output, never trust a summary stat alone (TFP's 3rd/4th/5th
  passes each found a real bug only broad sampling caught).
- Confidence-tiered merge, never a blind union of everything a pass proposes (TFP kept baseline +
  only ≥0.7-confidence additions from a second model; the unfiltered union was checked and
  rejected).
- Checkpoint every pass to disk during the run, not just in-memory counts (TFP lost a full pass to
  a session restart before this was fixed — `pass_N_checkpoint.jsonl` pattern).
- Take a backup before any dict edit; git history is the real rollback path, the backup is a
  same-session safety net, not the rollback mechanism itself.
- Run the full pytest suite twice (pre/post), diff by test ID, before any cutover — not a
  pass/fail summary alone.

## Sizing — not guessed, size for real before committing

TFP's comparable run: 16,826 sentences → 882 LLM calls (gpt-4o-mini) ≈ $0.46 one pass; a
gpt-5-mini rerun of the same scope ≈ $1.39. The syzif corpus is 119 full books, not session
transcripts — likely a materially larger raw-token volume. **Before committing to a budget**: run
Stage 2 (`extract_corpus`) alone first, dry, and read the real row count it produces — that number
sizes Stage 4's actual LLM call volume (Stage 3 dropped; Stage 5 anchoring is free). Do not estimate from the TFP figures above as if they
transfer directly.

## Owner and gate

- **Chiron's part**: this plan, CHI-014's grounding, and the Stage-1 seed-catalog *structure*
  proposal (mechanical derivation from an already-sealed map — arguably inside Chiron's §5
  corpus-structure authority, flagged for Felix/Gena to confirm rather than decided unilaterally
  here, since it's adjacent to the module-independence boundary CHI-014 §3 already named).
- **Stages 2–8, and any LLM-cost-bearing run**: Felix (or Gena) once Grace-triaged, per
  `SPEC-ETHAN-CHIRON-HESPERIA-CALIBRATION-ENTITY.md` §5b — new capability, not a documented-
  parameter toggle, and `BACKLOG.md`'s own 2026-08-31 note already named this handoff explicitly.
- **Gate before anything ships or gets pinned live**: Stage 8's release-gate verdict + pytest pass
  + a real live call through the actual caller path, same bar every prior TFP dict cutover was
  held to. No stage after 6 is "done" on a written claim alone.

---
SIGNED: Chiron | Claude Code context (Felix engine) | 2026-09-02 | build plan, companion to CHI-014 — not implemented, stages 2–5/8 use existing tooling, stages 1/6/7 are new glue

---
SIGNED: Chiron | Claude Code context (Felix engine) | 2026-09-02 | build plan, companion to CHI-014 — not implemented
SIGNED: Triage (Grace) | Grace context | 2026-09-04 | Stage 4 design lock folded (area/family batching + note-all proposals + single-LLM claim + D indirection)
