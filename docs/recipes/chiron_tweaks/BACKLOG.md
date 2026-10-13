# Chiron-tweaks backlog

## 2026-09-04 — Dict D pre-creation research preserved as its own artifact

Full code-research report (the pass grounding CHI-015 §8a) saved verbatim as
[`research/DICT-D-PRE-CREATION-RESEARCH-2026-09-04.md`](../../../research/DICT-D-PRE-CREATION-RESEARCH-2026-09-04.md),
per operator instruction — dev repo only (`research/` mirrors to prod only via the gated
`mirror-atomic-to-cc-srl.sh` promotion; prod's git remote is `no_push` and CLAUDE.md forbids direct
prod edits regardless, so this was not written to `/data/consolidare-continuum/hesperia/` directly).
CHI-015 §8a now links to it as the evidence trail; CHI-015 stays the operative spec, this file is
the raw preserved record.

## 2026-09-04 — CHI-015 §8a: Dict D's design verified against live resolver/pipeline code

Follow-up research pass (operator asked: D's real relations to A/B/C, outcomes/programmable
features, backward adjustments to core flows/activations). Traced `resolve_hit`
(`core/resolver/resolver.py`), `coherence_from_related` (`core/resolver/context.py:26-39` — real
formula: `0.15 * |related_concept_ids ∩ sibling candidates|`, graded not binary), and every
downstream consumer through `core/hexmap/`, `core/propagation/`, `hesperia/extensions/triz/`.

Confirmed in code, not just asserted: hexmap/propagation see only the final `concept_id → weight`
map, never resolver provenance — D's blast radius genuinely stays inside `core/resolver/`, no
hexmap/propagation changes needed. Found a real dormant precedent worth reusing:
`dlcr_policy.yaml`'s `sequential_association_weight`/`association_boost` (same-document recency,
not corpus-level — not D, but the closest existing wiring shape). Found and corrected one factual
error: CHI-015 §0 called B "288 labeled dots" — 288 is the area×family slot geometry, not a Dict B
concept count (core/default's real `dict_b_seed.jsonl` has 11 rows today). Full findings folded
into CHI-015 §8a (new), with §9/§10 updated to name two concrete integration-path options instead
of an unscoped "add a config key."

## 2026-09-04 — CHI-015 filed: Dict D (concept×concept co-occurrence) spec'd at max reliability

Operator asked for Dict D spec'd at max reliability, closing the concept×concept gap first, then
mapped for downstream placement. Filed:
[CHI-015](CHI-015-dict-d-concept-cooccurrence-spec.md) — Stage 9 in `STAGE-2-BUILD-PLAN.md`, hard
sequencing after Stage 8 (needs a real resolved corpus to count over, cannot read raw text
independently of the resolver). Design grounded in `projects/ops-method/`'s
`it_cta_relation_invent.py` precedent (typed relation invention, `review_status='pending'`, never
auto-approved) — same discipline, different storage substrate (D is versioned flat JSONL, not a
mutable Postgres table).

Key design calls: paragraph-level co-occurrence window (engineering choice, stated as such, not a
forced one); NPMI + log-likelihood (G²) significance test rather than raw PMI, to close the known
rare-pair PMI trap; fully deterministic core computation, no LLM in the build itself; an
`agreement_with_b` field (`agrees`/`novel`/`contradicts`) against B's authored `related_concept_ids`
as the disagreement-surfacing mechanism; never auto-merged into B. Placement map covers: resolver
`coherence_from_related` scoring input (new `params_combo/PC-*` candidate), Colombo's wiki-status
review queue, Dict C BAC-recovery prioritization, a new coverage/drift metric, and a flagged (not
scoped) TRIZ cross-family bridge use.

## 2026-09-04 — normalize_batch dropped, propose_llm prompt found TFP-hardcoded (not a generic reuse)

Checked `tools/dict_calibration/normalize_llm.py` and `propose_llm.py` directly (not just their
signatures, per CHI-014 §3's "generic pipeline" claim). Both `SYSTEM` prompts are hardcoded to the
TFP domain: `normalize_llm.py` — *"You normalize clinical / psychodynamic surface text... preserve
psychological meaning"*; `propose_llm.py` — *"clinical / TFP discourse... tfp.domain.name"* ids.
The function signatures are genuinely parameterized (`corpus_dir`, `dict_b_rows`); the prompt
content is not.

Two decisions, filed into CHI-014/`STAGE-2-BUILD-PLAN.md` same day:
- **`normalize_batch` dropped for core/default entirely** — its job (filler/disfluency removal) is
  a speech-transcript problem the 119 already-clean, already-grinded books don't have. Feed
  `extract_corpus`'s rows straight to concept proposal.
- **`propose_concepts` needs a core-domain prompt rewrite before use** — real scoped work, not a
  parameter swap. "Reuse the pipeline" now means reuse the orchestration shape, not the prompt
  text as shipped.

## 2026-09-04 — Moral Boundaries removed from syzif corpus (not filtered)

Operator instruction, direct: delete `85 Moral boundaries - Joan C. Tronto
[UNRELIABLE-NEEDS-REEXTRACTION].md` from `hesperia/modules/default/corpus/syzif/` rather than
carry it as a Stage 2 scope-filter exclusion (the plan CHI-014 §2 had proposed). Executed via
`git rm` on the dev repo (`igareosh/hesperia`, `/data/hesperia/hesperia`), staged not committed at
time of writing. Prod (`Consolidare-Continuum/hesperia`) untouched — this is dev-only until a
separately gated mirror promotion.

**Effect on Stage 2 sizing**: corpus is now **119 books, standing, gap at position #85** — not
119/120-pending-exclusion. `extract_corpus()` needs no scope-filter logic for this file anymore;
there is nothing left to filter. `CHI-014` §2/§4/§6, `STAGE-2-BUILD-PLAN.md` (stage 2 row), and
`docs/foundations/genesis_taxonomy_provenance.md` updated same day to stop describing this as an
open exclusion item. 119 is the corpus, standing — not a placeholder for a future re-extraction.

## 2026-09-02 — operator judgment call: corpus trustworthy enough, Stage 2 proposal filed

Operator, asked directly whether to start Stage 2 now or close the remaining grind items first
(re-extract *Moral Boundaries*, short-token re-audit, fingerprint-key fix — all still open, see
2026-08-31 entries below): **judged the 119/120-grinded corpus trustworthy enough, start Stage 2**,
the small cleanup items to continue in parallel rather than gating the bigger build.

Proposal filed: [CHI-014](CHI-014-stage2-syzif-corpus-attribution-proposal.md) — sizes the real
build (a missing 288-row core Dict B seed, not missing extraction tooling — `tools/dict_calibration/`
already has a generic, corpus/catalog-agnostic ACB pipeline that was only ever pointed at TFP's
Russian corpus; genesis_taxonomy_provenance.md's "no extraction tooling exists" claim is stale for
that reason). Routed via `inbox.md` → Grace triage → Felix/Gena to build, per spec §5b (new
capability, not a documented-parameter toggle — Chiron proposes, doesn't implement).

## 2026-08-31 — day close: syzif corpus grind, honest state, and one unresolved bug found in prod sync

End-of-day summary for whoever reads this cold, dev or prod side. Full blow-by-blow is the 8
dated entries below (newest first) — this is the roll-up, not a replacement for them.

**What happened today, in order**: recovered/committed the 120-book syzif corpus and
`repair_text.py` (this session's true start, before the entries below); mechanical cleanup;
structural artifact grind (`clean_corpus_artifacts.py` — ligatures, glyph-ID leaks, running
headers, page numbers, nav junk, and a soft/Unicode-hyphen join found only after a real bug in the
same script silently dropped writes on some files, both fixed same pass); word-level OCR fixes via
LLM with sentence context, in two size classes, each needing its own safety nets after real
failure modes turned up on inspection (content-loss, then a hallucination leak the first coverage
check didn't catch); a Cursor session picked up a written handoff brief and found the single
biggest remaining problem — one book, *Moral Boundaries* (Tronto), isn't word-level-fixable at all,
it's doubled/garbled extraction end to end — and flagged/renamed it rather than let it keep
polluting progress-file signal.

**Today's struggle, most honestly**: almost nothing in this pass worked correctly on the first
try. Every stage — the structural script, the confusion-table word-fixer, the first LLM long-run
prompt, its coverage check, that check's own duplicate-collapse logic — had a real bug or a real
precision gap that only surfaced by actually sampling output broadly and reading it, not by
trusting a summary stat. None of those bugs shipped silently; each is written up in its own entry
below with what broke and how it was caught. That pattern held until the very last thing found
today, still open:

**Unresolved as of day close — prod sync can silently orphan files**: `mirror-atomic-to-cc-srl.sh`
(brain repo `scripts/hesperia/deploy/`) syncs dev → CC via `git archive <tree> | tar -x` into the
CC clone. `tar -x` only adds/overwrites — it never deletes a file that was renamed or removed on
the dev side. Caught concretely today: renaming `85 Moral boundaries - Joan C. Tronto.md` to
flag it unreliable synced correctly as an *add* of the new flagged name, but left the old,
unflagged, doubled-garbled file still sitting in CC prod under its original name — exactly
undoing the point of the flag, silently. **Not fixed tonight**: CC prod is deliberately
receive-only (its own pre-commit hook blocks local commits without `CORPORATE_ALLOW_COMMIT=1` +
explicit operator go — a real boundary, not bypassed), and a one-off manual delete there wouldn't
fix the mechanism anyway — the next dev-side rename or delete would orphan another file the same
way. Real fix is in the sync script itself (e.g. wipe-then-reextract preserving the existing
`PRESERVE` list, or `rsync -a --delete`), owned by Grace/Abelard per that script's own header, not
patched here. **Concrete consequence**: as of day close, CC prod (`Consolidare-Continuum/hesperia`)
still carries the stale unflagged `85 Moral boundaries - Joan C. Tronto.md` alongside the correctly
flagged copy — anyone reading straight from `hesperia/modules/default/corpus/syzif/` in CC prod should know that and
prefer the `[UNRELIABLE-NEEDS-REEXTRACTION]` copy, ignore the bare-named one, until the sync
mechanism is fixed and re-run.

**State, plainly**: 119 of 120 books structurally and word-level grinded with documented, sampled,
evidenced residual error rates per tier (none claimed perfect) — full detail in the entries below.
1 book (*Moral Boundaries*) flagged unreliable, needs re-extraction, explicitly out of the "grinded"
count. Stage 2 (term/family attribution, Dict A/B/C) untouched, waiting on this corpus being judged
trustworthy enough — operator/Grace call, not this session's to make.

## 2026-08-31 (8th pass) — 85 Moral Boundaries renamed and flagged unreliable, excluded from corpus-clean claims

Acting on the 7th-pass finding below (doubled/garbled extraction end to end, ~2,594 of ~3,120
corpus-wide flagged short-token rows traced to this one file, word-level patching cannot fix it):
renamed `85 Moral boundaries - Joan C. Tronto.md` → `85 Moral boundaries - Joan C. Tronto
[UNRELIABLE-NEEDS-REEXTRACTION].md`, with an in-file `<!-- UNRELIABLE ... -->` notice at the top
so the flag survives even if someone opens the file directly rather than via directory listing.
Content untouched — this is a flag, not a fix; re-extraction from source (PDF/epub) is the actual
remedy, not scoped or started.

**Effect on prior claims**: all "clean/grinded" statements for the syzif corpus in this file's
earlier entries implicitly included this file's raw doubled-text content as part of "120 books" —
that was never true for this one book specifically (confirmed 7th pass, acted on here). Going
forward, corpus-state claims should read as **119 books grinded, 1 flagged out**, not 120, until
re-extraction happens and this file is re-admitted (and renamed back) on its own evidence.

## 2026-08-31 (7th pass) — short-token outside-MB grind (IDE, no new scripts)

Continued Chiron residual brief: cleared safe short-token `fix` proposals still
present outside Moral boundaries, then finished the Weick/Ordinary Men/Tarski/Johnson
focus leftovers with bibliography-true untangles (not progress hallucination chains).

**Counts (strict whole-token, hyphen/apostrophe not a boundary):**
- Outside-MB short remain: **518 → ~144** after safe batch + focus pass (recount at push).
- Moral boundaries still **re-extract**, not token-patch (~2.6k progress noise).
- Held: URL-path tokens; Ordinary Men citation-swap hallucinations (applied real cites instead).

## 2026-08-31 (6th pass) — IDE residual wording (no new scripts); Chiron brief answered

Cursor session executed [TASK-SYZIF-CORPUS-RESIDUAL-CLEANUP.md](TASK-SYZIF-CORPUS-RESIDUAL-CLEANUP.md)
without new tooling — brain/MCP awareness + direct file edits on
`/data/hesperia/hesperia` (`igareosh/hesperia`).

**Answers to the brief:**

1. **Offset-key drift (architecture)** — confirmed live. Short-token progress
   records many `verdict=fix` rows whose original tokens still sit in the
   corpus as whole words (~3,120 after word-boundary check; **~2,594 of those
   are `85 Moral boundaries - Joan C. Tronto.md` alone**). That book is not a
   word-level residual pool — it is **doubled/garbled extraction text** end to
   end; IDE token patches cannot salvage it. Re-extract / re-convert that one
   source before treating progress against it as evidence. Fingerprint keys
   remain the right fix before any further `--apply` round; not implemented
   this pass (operator: no new scripts).
2. **Long-run reject pool** — assessment **holds**. Fresh sample of rejected
   lowercase long tokens is dominated by real vocabulary
   (`intersectionality`, `antisymmetrical`, German/Dutch tech terms) plus
   Moral-boundaries doubling noise — not a large hidden garble pool. No further
   API spend justified for that class.
3. **Short-token class** — bigger residual than “spot-check ~85–90% of applied”
   alone: progress vs corpus diverge because offset apply skipped after drift.
   Do **not** blind-replay progress JSONL — many chained high-conf “fixes”
   (Ordinary Men) look like offset-mismatched hallucinated substitutions.

**IDE wording fixed this pass (prose only; URLs held):**

| Token | Fix | File |
|-------|-----|------|
| `potentionialist` | `potentialist` | `94 Moral Disengagement - Bandura Albert.md` |
| `doubleconsciousness` | `double consciousness` | `6 Reverence for live revisited - Albert Schweitzer.md` |
| `inter temporally` | `intertemporally` (revert bad long-run split) | `101 Poverty and famines - Amartya Sen.md` |
| `crisismanagement` | `crisis management` | `113 The Upside of Down - Thomas Homer-Dixon.md` |
| `userfriendliness` | `user-friendliness` | `105 The Innovators Dilemma - Clayton M. Christensen.md` |
| `userparticipants` | `user participants` | `106 Democratizing Innovation - Eric von Hippel.md` |
| `situationallyweak` | `situationally weak` | `16 Violence a Micro-sociological level - Randall Colins.md` |
| `entertainmentaudience` | `entertainment audience` | same Collins |
| `machinelanguage` | `machine language` | `103 The Design of Design - Frederick P. Brooks…` |
| `characterstring` | `character string` | same Brooks |
| `firstgeneration` | `first-generation` | same Brooks |

**Held on purpose:** `recordsmanagement` / `ScientificManagement` /
`PracticeOfManagement` / `safetystandards` inside **URL paths** — not prose OCR.
`pacificist`, `Bditors`, `Ulliversity`, `I.ouis` — already gone from corpus
(earlier applies). Stage 2 still out of scope.

## 2026-08-31 (5th pass) — long-run reclaim: fixed alignment check + closed a hallucination leak it exposed

Targeted the biggest pool the 4th-pass entry left unresolved: 5,237 long-run candidates the
coverage check had downgraded. Root cause confirmed: `\b(\w+)(\1)\b` needs a word boundary between
the two repeats, which doesn't exist inside a no-space glued blob, so it could never actually
collapse a duplicate like "RootsRoots" — a real de-dup ("RootsRootsooffCaring" -> "Roots of
Caring") scored 0.65 and got thrown out with genuine content-loss cases. Replaced with sequential
word-order alignment against the correction (allow each word once or twice consecutively, small
fuzzy slack for the corpus's "of"->"off" rendering pattern). Free re-check against the existing
pool (no API calls) reclaimed 2,655.

Validating that on a broader sample surfaced a second, unanticipated leak: the alignment only
checked one direction (original's content must survive in the correction) — it never checked that
every word in the *correction* traces back to the original, so a handful of results had small
hallucinated additions the length-ratio over-completion check was too coarse to catch:
"accountooffmoral" -> "...moral **development**", "sharesomesomeooffthe" -> "...the
**privileges**", "consequencesofofsuch" -> "...such **an ideology**" — each individually small
enough to stay under the 1.3x length threshold. Fixed: any correction word (>=3 chars) unmatched
anywhere in the walk now fails the check, symmetric to the content-loss direction. Also reinforced
the prompt (explicit "off"=="of" rule, explicit no-addition rule) and redid all 9,391 long-run
suspects fresh against both fixes together, rather than patch old-prompt corrections — 3,139
applied (`f43aff8f`/CC `51d25bd`), on top of the 4th-pass entry's 3,079, for 6,218 long-run fixes
total. All three flagged hallucination cases reverified as correctly excluded (still present,
unfixed, in the corpus) before commit, not just assumed fixed.

**Still open**: ~2,276 long-run suspects the model itself rejects outright (genuinely ambiguous,
untried: bigger context window or a stronger model, both cheap given the small pool), and whatever
fraction of the remaining content-loss/over-completion-excluded pool a further prompt/algorithm
round could still reclaim — not attempted further this pass, diminishing-returns territory rather
than a known gap.

## 2026-08-31 (4th pass) — OCR word-level errors closed via LLM (sentence-context, two safety nets), corpus now word-level grinded

Closes the item the 3rd-pass entry below left open — that entry's two non-LLM attempts (dictionary
edit-distance, confusion-table) are still accurate history, kept below unedited. What actually
worked: sentence-context judgment via API, not pattern matching — the same lesson both non-LLM
attempts pointed at (neither had context to tell real rare vocabulary from garbling).

**Also found and fixed along the way, unrelated to the LLM work**: a silent write-skip bug in
`clean_corpus_artifacts.py` (`8db1d00d`) — it compared cleaned output against an already-mutated
intermediate variable instead of the true original, so a file needing only one fix stage had its
write silently dropped even though stats counted the change correctly. Also added a **soft/Unicode
hyphen line-wrap join** (`\xad`, U+2010, U+2011 — different codepoints from the ASCII `-`
`repair_text.py` handles): 18,608 joins, found via `"chal\xad\nlenge"` for `"challenge"` surfacing
during suspect review.

**LLM approach** (`fix_ocr_word_errors_llm.py` + `fix_ocr_word_errors_llm_longrun.py`, gpt-4o-mini):
sends book title, author, sentence context, and the flagged word/run; model either fixes with
stated confidence >=0.70 or rejects — never guesses under threshold. Split by flagged-token length,
different risk profile each:

- **Short (<15 chars, single-word typos)**: 24,887 applied (`84b4c21f`). ~85-90% correct on a
  100-item random sample; known residual defects accepted as "+- reliable" (operator's framing,
  not silently absorbed): `ditTeren`->`differen` (not a real word), `automaticallylydelegitimized`
  ->`automatically legitimized` (drops "de-", inverts meaning), `pacificist`->`pacifist` and
  `accessary`->`accessory` (both real alternate spellings, not errors).
- **Long (>=15 chars, glued/duplicated multi-word runs)**: needed a second, different prompt and
  two independent deterministic checks the model's self-report couldn't be trusted alone for
  (`f6b77efd`) — see that commit message for the concrete over-completion examples (hallucinated a
  person's name, a full quote, a full canonical book title, all plausible-sounding and all
  unverifiable from the actual corrupted span). 3,079 applied after both checks; 5,237 + 1,446
  candidates the model proposed were rejected by the coverage/over-completion checks, not applied.

**State**: dev `f6b77efd` / CC `11815b9`, both clean, both in sync. Structural grind
(ligatures/cid/headers/pagenums/nav/soft-hyphens) plus word-level OCR correction (28,000+ real
fixes total across both LLM passes) is now the corpus floor. Not claiming zero remaining defects —
every accepted tier carries a stated, evidenced residual error rate, not silence. What's still
genuinely open: the ~2,276 long-run tokens the model itself rejected (no attempt made), and the
5,237+1,446 caught-and-excluded long-run candidates (never re-tried with a third strategy) —
neither blocks Stage 2, both are just unresolved, not silently declared clean.

## 2026-08-31 (3rd pass, tried and rejected) — OCR word-level errors: confusion-table auto-fix is not safe, do not apply as-is

Tried to close the item the 2nd-pass entry below left open. Two approaches, both dead-ended on
real evidence, not assumption — script kept as report-only (`fix_ocr_word_errors.py`), nothing
applied to any file, dev/prod both untouched by this attempt:

1. **Brute-force dictionary edit-distance** (singleton token + not in system dict + unique match
   within edit distance 2): dropped for speed *and* precision. One single book (`4 Governing the
   Commons`) has 2,901 singleton non-dictionary tokens — most are legitimate rare proper
   nouns/place names (`Yoram`, `McCubbins`, `Trumpington`, `Williamstown`, `Sabon`...) a generic
   dictionary doesn't know, not OCR noise. Exhaustive search against the full ~74k-word dictionary
   timed out past 60s on that one file alone.
2. **OCR glyph-confusion table** (rn/m, cl/d, ll/n, vv/w, B/E, O/D, etc. — substitution patterns
   specific to print/scan misreads, accept only if exactly one substitution lands on a known-good
   word): fast (3s/file), but a hand-check of a 60-item sample from the full-corpus dry-run
   (1,535 candidate fixes, 65 flagged ambiguous and already skipped) found roughly 35-40% wrong or
   nonsensical, not the nearly-zero-false-positive bar the 2nd pass held. Concrete wrong fixes:
   `BRCA`→`BREA` (a real gene name mangled), `CIOs`→`Clos`, `BBN's`→`Ben's` (real acronyms),
   `Eric's`→`Erie's`, `herd's`→`hero's` (real possessives — a dictionary-lookup bug on `'s` forms,
   not even genuine OCR garbling), `Correia`→`Correla`, `Pinar`→`Pillar`, `Banet`→`Ballet` (real
   surnames/place names replaced with unrelated dictionary words). Genuine catches exist in the
   same sample (`Miigram`→`Milgram`, `VlLFREDO`→`Vilfredo`, `Bditors`→`Editors`,
   `Ulliversity`→`University`) — the problem is there's no cheap way to tell which is which without
   sentence context, which neither a dictionary check nor a fixed confusion table has.

**Conclusion**: this needs context-aware review, not a blind pattern/dictionary pass — the same
class of tool as the vision-model re-OCR already used once in `projects/olga-tfp-book-ocr/` (brain
repo, one Russian book, GPT-4o against page photos), or an LLM text pass with surrounding-sentence
context, not a spellchecker. Neither is scoped or started. `fix_ocr_word_errors.py` stays in the
tree as a **report-only** diagnostic (`--json`, no `--apply`) — useful for sizing the problem or
feeding a future LLM-assisted pass's candidate list, not for blind auto-correction.

**Corpus state as of this entry**: unchanged since the 2nd-pass commit (`fc38bcbe` dev /
`ad437e7` CC) — structural grind (ligatures/cid/headers/pagenums/nav) is the current floor, word-
level OCR correctness is still an open item, not a regression from this attempt. 

Commit `0ff6d4c3` (dev, `igareosh/hesperia`), mirrored to CC (`Consolidare-Continuum/hesperia`
`6f11f13`) same session. Follows directly on the entry below (same-day, same corpus) — that
entry's mechanical `repair_text.py` pass (CRLF/mojibake/hyphen-join) was already committed;
this pass adds five more artifact classes `repair_text.py` doesn't touch, found by direct
inspection of the committed 120-book text, not assumed:

- **Ligature-space breaks** — PDF `fi`/`fl`/`ffi`/`ffl` glyph extracted with a stray space:
  `defi nite`→`definite`, `refl ect`→`reflect`, `diffi cult`→`difficult`. 2,649 joins, concentrated
  in a few books (Hayek alone: 1,450). Verified no false-positive risk — no English word ends bare
  in `fi`/`fl`/`ffi`/`ffl`, checked against real corpus context before applying, not assumed.
- **`(cid:NN)` PDF glyph-ID leaks** — font `ToUnicode` map failed, literal placeholder token
  survived instead of the character. 9,786 removed (Pearl's *Causality* alone: 3,390 → 0).
  Unrecoverable without the original PDF/font — removed, not reconstructed.
- **Running headers/footers** — book/chapter titles, and in at least one case (Hume, scraped from
  `oll.libertyfund.org`) the source website's own header/URL/generator tag, repeated on every
  printed page and now splitting sentences mid-paragraph in the flowing text. Detected by
  in-file line-frequency (>=5 verbatim repeats, short, no sentence punctuation), first occurrence
  kept as a structural trace, rest removed: 19,077 lines.
- **Standalone page-number lines** (digit-only, strict-uppercase-roman-only): 1,863 removed.
- **HTML/CD-ROM nav leftovers** (`[Click here]` etc., Peirce *Collected Papers* only — that source
  was clearly an HTML/hyperlinked edition): 235 removed.

104/120 files changed content. Tool: `hesperia/modules/default/corpus/syzif/clean_corpus_artifacts.py`
(idempotent — safe to re-run; `--dry-run --json` re-audits without writing).

**Deliberately not touched — needs a human/per-book call, not a blind regex**: per-chapter and
end-of-book Notes/Bibliography/References/Index. 86/120 files carry candidate headings; several
put real argument in chapter-end notes, not just citations — e.g. Sacks (`10 The Dignity of
difference`) has four separate `NOTES` blocks at 22%/45%/60%/67% through the file, not one
end-block, so a naive "truncate from first Notes heading" would have deleted ~80% of the book.
Candidates (line number + text + %-position) are in `clean_corpus_artifacts.py --dry-run --json`
under `"backmatter"` — not acted on here.

**Second-pass inspection, still fully open** (per the entry below, spot-checked again just now on
`4 Governing the Commons - Elinor Ostrom.md`: `Bditors`/`Ulliversity`/`I.ouis` for
`Editors`/`University`/`Louis` are still there, untouched by this pass — different bug class,
character-level OCR misreads, not spacing/glyph-ID/layout). This pass's regexes are structural —
they can't and don't touch word-internal substitution errors. Options for that pass, not decided
here: (a) dictionary/spellcheck-suggestion pass like the abandoned genesis `spellcheck_suggestions.py`
(vowel-substitution variant generation + frequency lookup, narrower scope than full OCR redo), (b)
vision-model re-OCR against original scans if they still exist, following the pattern already used
once in `projects/olga-tfp-book-ocr/` (brain repo) for a single Russian book — not wired to this
corpus. Whichever direction, this is the blocker named in the entry below before Stage 2 can trust
the corpus as a term-attribution source.

## 2026-08-31 — default/core (not TFP): Stage 2, wire syzif book corpus in — sequenced after a text-quality grind pass

Candidate, not started. This session (2026-08-31) recovered and committed `sphere/source/
syzif/` (120 books, canonical per `docs/foundations/genesis_taxonomy_provenance.md`), via
`markitdown` conversion + a reconstructed `repair_text.py` (CRLF normalize, `ftfy` mojibake fix,
hyphen line-joins, blank-run collapse — mechanical cleanup only). The underlying OCR scans carry
real word-level errors that mechanical cleanup doesn't catch — spot-checked in `4 Governing the
Commons - Elinor Ostrom.md`: "Bditors" (Editors), "Ulliversity" (University), "I.ouis" (Louis).
**Before Stage 2 starts**: a real grind pass across all 120 files fixing OCR word errors — not
scoped or started this session.

**Stage 2 itself** (named in `genesis_taxonomy_provenance.md`, unbuilt since 2026-07-30, still
unbuilt as of this note — no extraction/attribution tooling exists anywhere in either repo,
confirmed by search both dates):

1. Extract real text from the 120 books in `hesperia/modules/default/corpus/syzif/` — done 2026-08-31, grind pass
   above still owed before this is a trustworthy source.
2. Attribute terms/passages from that text to specific families (the 288-row `AREA_FAMILY_MAP`
   in `core/topology/invariant_catalog.py` — currently only the family *names* came from the
   genesis corpus, not real term-level content).
3. Compute weights from that attribution and rebuild Dict A → Dict C → Dict B (the calibration
   `.jsonl` packs the default-core lane, `hesperia-analyze-dev.service` :18880, actually runs on).

This is sealed-pipeline-adjacent (new attribution/weighting logic feeding the live dictionaries,
not a documented-parameter toggle) — Chiron proposes per spec §5b, does not implement alone.
Hand to Felix/Gena once the grind pass is done and this is Grace-triaged.

## 2026-08-20 — correction: the 8 disambiguation renames below broke live scoring, reverted

While starting the corpus-calibration-parameters pass right after shipping the renames below,
checked whether `corpus_support()`'s Postgres FTS lookup was still healthy for the renamed
concepts — it wasn't. `dict_b.jsonl`'s `preferred_label` is not display-only: `hesperia/modules/
tfp/data/tfp_v1/postgres/corpus_grounding.py::corpus_support()` feeds it straight into
`plainto_tsquery()`, and `core/resolver/resolver.py::resolve_hit()` feeds it into
`label_token_overlap()` for live concept-resolution scoring. Appending a disambiguating suffix
broke both: `plainto_tsquery` ANDs every token, so `"splitting (C-1003)"` zeroed out matches that
`"splitting"` alone gets 1178 real hits on (same pattern confirmed for all 8: `devaluation` 148,
`Изменения` 1698, all → 0 with the suffix attached). Reverted all 8 labels to their original
values (Hesperia repo `fd06f88b`) — the label collision was cosmetic (`concept_id` already
disambiguates everywhere the system depends on identity), not worth degrading two live-functional
consumers to fix. The dedupe (61765→203 rows) is unaffected and stays. Lesson for next time:
`preferred_label` is a load-bearing field in at least two live paths, not just a trace/display
string — any future edit to it needs the same "check every consumer, not just the ones you
already know about" discipline this correction was caught by.

## 2026-08-20 — duplicate-label concept group review (the "8 more groups" item from Phase 4e, below)

Operator direction: dig into the 9 groups one by one now that the TFP corpus is in Postgres,
executing in order (2) rename to disambiguate, (3) dedupe, (1) collapse noise.

**Dug all 9 duplicate-`preferred_label` groups (21 concepts)** in `assets/calibration/dicts/
v0_6_9/dict_b.jsonl` against `dict_a.jsonl`/`dict_c.jsonl` evidence plus `family_ids`/`area_ids`.
Findings by group:

- `identity_diffusion` (`TFP_CLUSTER_003`/`011`, both F4/A2) and `splitting_cluster`
  (`TFP_CLUSTER_014`/`015`, both F5/A3): both members carry real, distinct thematic content —
  left untouched.
- `devaluation`/`idealization`/`splitting` (`C-1009`/`TFP_DEVALUATION`, `C-1008`/
  `TFP_IDEALIZATION`, `C-1003`/`TFP_SPLITTING`): **not duplicates** — different `family_ids`/
  `area_ids` entirely (e.g. `C-1009` F4/A4 vs `TFP_DEVALUATION` F10/A3), just a coincidental
  English-label collision between two independent catalog regions (`C-10xx` "core" scheme vs
  `TFP_*` scheme). Same pattern independently found in `Изменения` (`B_A10_F15/16/17_002`) and
  `Управление` (`B_A10_F6/7_002`) — a systematic `_002 = first word of the `_001` sibling's
  label` truncation convention across all 24 families in area A10, which only actually collides
  where two families' first words happen to match.
  **Action taken**: renamed 8 concepts' `preferred_label` to disambiguate, mechanically (append
  `concept_id` for the `C-10xx` trio, append `family_id` for the `B_A10_F*` five) rather than
  inventing new clinical phrasing: `C-1009`→`"devaluation (C-1009)"`, `C-1008`→
  `"idealization (C-1008)"`, `C-1003`→`"splitting (C-1003)"`, `B_A10_F15_002`→
  `"Изменения (F15)"`, `B_A10_F16_002`→`"Изменения (F16)"`, `B_A10_F17_002`→
  `"Изменения (F17)"`, `B_A10_F6_002`→`"Управление (F6)"`, `B_A10_F7_002`→`"Управление (F7)"`.
  Shipped, verified live (see below).
- **File-hygiene finding, unrelated to the label collisions**: every concept in `dict_b.jsonl`
  had many byte-identical duplicate rows (61,765 rows for 203 concepts, worst case
  `TFP_TRANSFERENCE` at 2,282 copies) — no `surface_form` field exists in dict_b to differentiate
  them, so this isn't the "variants/synonyms" pattern `CHIRON-TFP-DEPLOYMENT-MAP.md` §5 assumed.
  Confirmed functionally inert first — `core/engine/lexical_concept/pipeline.py::_merge_dict_b()`
  already dedupes to first-row-per-`concept_id` on every load, so this was pure file bloat, not a
  live behavior bug. **Action taken**: rewrote `dict_b.jsonl` keeping only the first row per
  `concept_id` — 61,765 → 203 rows, byte-identical effective content. Shipped.
- `denial` (`TFP_CLUSTER_006`/`007`/`009`, F8/A3) and `devaluation_cluster` (`TFP_CLUSTER_004`/
  `012`/`013`, F10/A3, same slot as `TFP_DEVALUATION`): **initially judged `007`/`009`/`012`/`013`
  as noise** (thin, mostly-generic `dict_a.jsonl` evidence: 2/4/2/1 entries each, several
  non-thematic) and collapsed them into `006`/`004` respectively, same treatment as the
  already-closed `TFP_CLUSTER_005`→`004` precedent. **Caught before it stuck**: live-verifying
  the change through `router-inquire`/`face=tfp` (the real caller path, not a proxy) surfaced
  `assets/data/engine_dynamics_v060/dict_b/dict_b_tfp.jsonl` — a **separate, richer legacy
  registry** `sphere/router/engine_analyze_bridge.py::_dlcr_dict_b_registry()` reads for trace
  labels, distinct from the sealed pack's stripped `"definition": "concept_only_promotion_v052_3"`
  rows. That file has real `alt_labels`/`definition`/`related_concept_ids` for every one of these
  concepts — `TFP_CLUSTER_007`'s `alt_labels` are genuine denial-defense phrases ("не было", "меня
  не было"), `009`'s are literally "отрицания"/"и отрицания" ("of denial"), each with
  `related_concept_ids: ["TFP_DENIAL"]` or `["TFP_DEVALUATION"]`. **None of this was noise** — the
  sealed pack's thin `dict_a.jsonl` coverage for these concepts was a promotion gap (the rich
  `alt_labels` never got wired into the live phrase matcher), not evidence the concepts were bad.
  **Reverted the collapse in full** (restored `dict_b.jsonl` rows + the 9 `dict_a.jsonl` redirects,
  verified byte-identical to the pre-collapse `dict_a.jsonl`) before it ever reached a second
  session. `TFP_CLUSTER_004`/`005`/`006`/`007`/`009`/`012`/`013` all stand as before, only the
  earlier `005`→`004` collapse (Phase 4e, evidence-checked at the time) remains in effect.

**Real next candidate, surfaced by the revert, not yet built**: promote the legacy registry's
`alt_labels` into `dict_a.jsonl` as proper phrase-match entries for `TFP_CLUSTER_004/005/006/007/
009/012/013` (deterministic, free — same class of fix as Phase 4a's `concept_link` wiring), and
add the missing `TFP_DENIAL` parent concept itself to the sealed pack (`dict_b.jsonl` + a
`dict_a.jsonl` entry) — it exists cleanly in `dict_b_tfp_ru_v060.jsonl`/`dict_b_tfp.jsonl`
(`alt_labels: ["отрицание", "не признаю", "как будто не было"]`, real Russian definition) but was
never promoted, the same way `TFP_DEVALUATION`/`TFP_IDEALIZATION`/`TFP_SPLITTING` were. This would
give `denial` a working root concept for the first time and properly ground its three sub-clusters
instead of leaving them under-lexicalized. **Not started this session** — deliberately not forced
after the collapse mistake; needs its own verified pass, same discipline as Phase 4b's ACB work.

**Verification for everything shipped this session**: backups taken before any edit
(`/tmp/chiron_dictb_backup_2026-08-20/`); calibration-relevant pytest subset + full ~470-test
suite run twice (against edited and pre-edit dicts) — identical 21 pre-existing failures both
times (baseline drifted from the documented 15 since 2026-08-19, unrelated to this session; none
of the 21 involve dict content, including the hash-sensitive `test_dlcr_pipeline_v1_gold_digests`,
which passes both ways); 2 real sessions (`11-09-2023`, `23-05-2024`) rerun through
`internal_review` post-revert, gate passes both, values unchanged from the last documented
baseline; live `router-inquire face=tfp` call against a real devaluation/idealization/splitting
sentence, verified through the actual caller path, not a proxy. `hesperia-analyze-tfp`/
`hesperia-analyze-dev` restarted and reverified after the fix and again after the revert.
**Formal thinking-map gate note**: no Hesperia domain map exists yet, and hand-assembling a
custom `LogicLayer`/`GateCheck` gate through the primitive `fpf_thinking_map` API turned into its
own sub-project — flagged as a real gap (see spec §3) rather than forced through; the safety case
here rests on the direct verification above instead.

## Next session — planned 2026-08-18 EOD, start here

**Cold-start checks first** (cheap, do before anything else): `systemctl status
hesperia-analyze-tfp hesperia-analyze-dev` (both should be active); `git log -1` on both
`/data/hesperia/hesperia` and `/data/workspaces/hesperia` (should match, currently `5c88b809`);
`cat governance/hesperia_work_mode.txt` (should be `IDLE`); has the operator run the `git config`
fix yet (if so, batch-amend the day's affected commits, don't do it one at a time); has Colombo
placed either queued wiki page yet.

**Then, the actual next move — one action that feeds three open backlog items at once**: only 4
of the 14 real sessions on prichindel have been run through the fixed pipeline so far
(`1-11-09-2023`, `14-12-2023`, `15-12-2025`, and `22-08-2024` partially — it never reached the
gate, blocked pre-gate by the TRIZ uniformity check). The other 10 — `02-03-2026`, `15-02-2024`,
`20-02-2025`, `20-10-2025`, `21-08-2025`, `23-05-2024`, `24-02-2025`, `24-04-2025`, `26-12-2024`,
`28-10-2024` — haven't been touched at all. Running them through
(`HESPERIA_DLCR_STRUCTURAL=1 HESPERIA_CALIB_DICT_VERSION=v0_6_0_clr_v052_5 python3 tools/
gena_tfp_bundle_run.py -i hesperia/modules/tfp/data/tfp_v1/corpus/sessions/<date>.md --with-kme
--with-triz --with-topology --gate-profile internal_review`, same as today's runs — pull each
`.md` from prichindel via `scp`/`rsync` first, corpus dir is gitignored/local-only) is the single
highest-leverage thing to do next, because n=4 real sessions isn't enough evidence for any of:

- Whether the A10/"процесс лечения" dominance pattern is real bias or coincidence (n=3 real so
  far, all agreeing — worth knowing if that holds at n=10+ before spending more effort on it).
- Whether `dict_a_max_accepted=120` genuinely needs revisiting (every real session so far
  saturates it — is that universal or an artifact of picking long sessions first).
- Whether `CHI-001`'s `S`-scale needs rescaling, and what a real percentile distribution across
  more than 2 real sessions actually looks like.
- Whether the TRIZ uniformity near-miss on `22-08-2024` recurs on other real sessions or was a
  one-off.

Gather the data first (this is still "gather," not "recalibrate" — don't jump straight to
changing any of `dict_a_max_accepted`, the uniformity threshold, or `S`'s scale from a bigger n
without looking at what the bigger n actually shows). The recalibration pass proper comes after,
once there's a real spread to recalibrate against instead of 2-4 points.

## Evidence gathered, 2026-08-19 — all 10 remaining sessions run, n=13 real sessions now available

All 10 ran clean through the pipeline (`internal_review` gate, same invocation as above). Results:

- **`contradiction_grounding_zero_lex_share` gate check: FAILS on all 10/10 new sessions**, and it's
  the *only* failing check on every one of them (everything else — schema, audit path, dynamics
  metadata, structural checks — passes clean). Values: `0.602–0.877` against the `MAX_ZERO_LEX_SHARE
  = 0.6` cap in `tools/tfp_calibration_audit.py`. **Root-caused same day, 2026-08-19 — see below.**
  It's not a gap in Gena's family-grain fix (`1660c89f`); it's the same root cause as the
  `dict_a_max_accepted=120` item directly below. Merged into one finding.
- **A10 dominance: CONFIRMED, not coincidence.** Real `areas_final` mass share (the authoritative
  post-inhibition distribution used by the audit's `FINAL_AREA_DISTRIBUTION_COLLAPSED` check, not a
  proxy) — A10 is the top area in **all 10** new sessions, mass share `0.61–0.96`. Combined with the
  3 original real sessions, that's A10 dominant in 13/13 real sessions that reached this stage. The
  n=3 pattern was real, not luck. Root cause not yet investigated (is this genuine session content,
  e.g. TFP transcripts structurally centering on treatment-process discussion, or an artifact of the
  area/family rollup math) — checked whether it shares the dict_a_max_accepted root cause below, it
  does not cleanly (see root-cause note), stays a separate open item.
- **`dict_a_max_accepted=120` saturates on all 10 new sessions too, and is now root-caused — see
  below.** Same mechanism as the gate failure above, not two separate problems.

### Root cause, 2026-08-19: `dict_a_max_accepted` truncates by document position, not salience

Traced via `core/lexical/matcher.py::match_dict_a()` + real bundle data (`13_contradiction_
reconciliation.json`, `04_dlcr_full.json`) across all 11 sessions with fresh output on disk
(10 new + a clean rerun of `11-09-2023`, the one session that passes the gate — no old bundle
survived to compare against, reran fresh per the "no stale checked-in exports" rule below).

**Mechanism**: `match_dict_a()` sorts all raw candidate hits by `span_start` (document position)
first, resolves overlaps, then does `accepted = accepted[:max_accepted]` — a flat cut by *reading
order*, not by concept/family diversity or salience. For `02-03-2026`: **120 accepted, 3,440
rejected** (`lexical_hits_accepted`/`lexical_hits_rejected` in `04_dlcr_full.json`) — the cap keeps
3.4% of raw matches, discarding the rest regardless of which family they'd have grounded. No
per-family floor or diversity-aware selection exists in the matcher.

**Consequence, measured directly**: for each session, `families with ≥1 accepted hit` /
`distinct families appearing in generated contradiction pairs` (call it `hit_ratio`) predicts
gate pass/fail almost exactly:

| session | zero_lex_share | canonical pairs | families in pairs | families hit | hit_ratio | gate |
|---|---|---|---|---|---|---|
| 11-09-2023 | 0.547 | 340 | 21 | 12 | **0.571** | **PASS** |
| 20-10-2025 | 0.659 | 378 | 24 | 12 | 0.500 | fail |
| 24-04-2025 | 0.601 | 301 | 25 | 10 | 0.400 | fail |
| 26-12-2024 | 0.688 | 432 | 28 | 10 | 0.357 | fail |
| 21-08-2025 | 0.742 | 384 | 31 | 14 | 0.452 | fail |
| 20-02-2025 / 24-02-2025 | 0.760 | 387 | 24 | 12 | 0.500 | fail |
| 02-03-2026 | 0.772 | 479 | 24 | 11 | 0.458 | fail |
| 15-02-2024 | 0.834 | 459 | 31 | 8 | 0.258 | fail |
| 28-10-2024 | 0.870 | 332 | 35 | 12 | 0.343 | fail |
| 23-05-2024 | 0.877 | 252 | 23 | 8 | 0.348 | fail |

The one passing session isn't qualitatively different content — it just happened to have its
family-relevant lexical matches land early enough in the transcript to survive the position-order
cut. Every other real session's later-discussed families get zero literal grounding purely because
the cap runs out before the matcher reaches them, not because matches don't exist there. The value
`120` itself has no TFP-specific rationale on record — `assets/data/engine_dynamics_v060/
domain_packs.yaml` shows `tfp: dict_a_max_accepted: 120` is identical to `clinical_speech: 120`,
and `docs/foundations/parameter_synergies.md` §6 (the only doc section mentioning this param) is
about an unrelated env-gate topic. Looks copy-pasted from a shorter-input profile, never
re-tuned for full ~30–40 min TFP transcripts.

**Fix directions considered**:
1. Raise `dict_a_max_accepted` well past 120 for the `tfp` profile specifically — simplest, but
   still position-ordered, so it only delays the same failure mode on longer transcripts, doesn't
   eliminate it structurally. **Skipped** — (2) fixes the mechanism at the existing budget, no need
   to also grow it.
2. Redesign `match_dict_a()`'s truncation to be family/diversity-aware (e.g. round-robin across
   families, or a per-family minimum floor before filling the remainder by position/priority) —
   fixes the mechanism, not just the symptom. **Chosen and implemented, 2026-08-19 — see below.**
3. Leave the cap alone, revisit whether `contradiction_grounding_zero_lex_share`'s `0.6` bound (or
   the family granularity it's measured at) is the wrong lever entirely, given the topology-derived
   contradiction generator produces a dense near-complete pairwise set within a dominant area
   (24–35 distinct families in play per session) that no reasonably-sized literal-hit budget will
   ever fully cover. **Not touched — turned out moot**, see below.

### FIXED, 2026-08-19: direction 2 implemented — 11/11 real sessions now pass the gate

Kept scoped to avoid the "touches shared profiles" risk called out above:

- **`core/lexical/matcher.py::match_dict_a()`**: new optional `diversity_key` param (PO-31). When
  given, the cap round-robins across `diversity_key(hit)` groups (each group's hits still consumed
  in position order) instead of a flat position slice, then re-sorts survivors back to document
  order before returning — callers (sequential-association / textual-recency logic) depend on
  `accepted` being in span order, so selection can reorder but the returned list can't. **Omitting
  `diversity_key` (the default) is byte-for-byte the old behavior** — this is the mechanism that
  keeps `scientific`/`clinical_speech`/`psychodynamic` untouched.
- **`core/engine/lexical_concept/pipeline.py`**: new `_hit_family_diversity_key()` helper, derives
  the family key (`A10_F10`) straight from the hit's primary `candidate_concept_ids[0]` via the
  existing `concept_id_to_area_family()` parser (no new dict_b lookup needed — the concept_id
  itself already encodes area/family). Wired into both `match_dict_a()` call sites that feed
  `lexical_concept_counts` (whole-session + per-segment), gated behind a new policy flag so it's
  opt-in per profile.
- **`assets/data/engine_dynamics_v060/domain_packs.yaml`**: `tfp` pack only gets
  `dict_a_family_diversity: true`. `scientific`/`clinical_speech`/`psychodynamic`/`default` are
  provably unaffected — the flag defaults false/absent for all of them.

**Verification**:
- 4 new unit tests in `tests/lexical_concept/test_matcher_caps.py` (legacy-behavior-unchanged
  case, diversity-spreads-the-cap case, single-group-degrades-to-flat-cut case) — all pass.
- All 11 real sessions rerun through the full `internal_review` gate: **11/11 now pass**, zero
  failures. `23-05-2024` (worst case, was `0.877`) → `0.218`; families-with-a-hit went `8→19` of 23
  in play. `11-09-2023` (the one session that already passed) improved too, `0.547→0.356` — no
  regression on the previously-passing case.
- Full Hesperia pytest suite (`tests/`, ~470 tests) run twice: once against the fix, once against
  pre-fix `fb73f698` in an isolated `git worktree` (not a `git stash` — a stash was tried first and
  timed out mid-run with the working tree left stashed; caught and restored before anything else
  touched the tree, then redone via worktree to avoid touching shared state a second time). Same
  **15 failures in both runs, identical test IDs** — all pre-existing (stale golden hashes, a
  version-string drift, unrelated architecture checks), none caused by this change. Zero
  regressions.

Direction 3 (the gate's own `0.6` bound / granularity) turned out moot: the mechanism fix alone
cleared every real session without needing to loosen the threshold. Revisit only if a future
session's content genuinely can't reach `0.6` even with fair family coverage.

- **TRIZ `uniformity` gate: passed cleanly on all 10 new sessions** (`validation_uniformity_check:
  true`). The `22-08-2024` near-miss (`0.3043>0.30`) did not recur — looks like a genuine, narrow
  one-off catch rather than a systemic threshold problem. Lower priority now.
- **`CHI-001`'s `S` (`truth_point_accumulation`) real distribution, n=10**: `0.131–0.402`, median
  ~`0.25`. Confirms the earlier read that raw `ts_rank_cd`-based S rarely approaches 1.0 — now
  there's enough spread to do a real percentile-based rescale instead of guessing.

Not yet actioned — this is the evidence for the recalibration pass, not the recalibration itself.
Operator call needed on priority order, especially given the zero_lex_share gate result is new
information that wasn't anticipated (everything else here confirms/refines what was already
suspected; that one changes the picture).


## Cadence (operator, 2026-08-18)

Gather genuine tweaks first — real ones, based on: parameters already available, new parameters
worth creating, existing TFP parameters worth revising, or the tweaks/recipe structure itself
worth rearranging. Once there's a real body of them, do a recalibration pass that treats the
accumulated tweaks as input: what needs recalibrating, what needs repopulating (dicts, corpus,
thresholds), now that the ground truth under them has moved. Not a one-tweak-at-a-time-and-ship
loop — gather, then recalibrate, as a deliberate second pass.

This file is the gathering surface: a candidate lands here with enough context to start without
re-deriving, moves to its own `CHI-<NNN>` (or `PC-<NNN>`, if it turns out to be a combo of existing
params rather than new capability) once it's actually built and validated, and gets struck through
(not deleted — history stays visible) here when it ships.

## Candidates, surfaced during CHI-001's work (2026-08-18), not yet built

- ~~`dict_a_max_accepted` cap (revise existing param)~~ — **FIXED 2026-08-19**, see the "Evidence
  gathered" → "FIXED" section above. Root-caused as document-position truncation starving family
  coverage; fixed via a diversity-aware matcher redesign, not a raw number change. 11/11 real
  sessions now pass.
- **TRIZ `uniformity` gate near-miss on `22-08-2024` (revise existing param, maybe)** —
  `hesperia/extensions/triz/family_weights_sparsify.py::UNIFORMITY_FRAC_MAX = 0.30`. Tripped at
  `0.3043` — 1.4% over, with `--with-triz` correctly passed (not the known missing-flag
  mis-invocation class). First real near-boundary trip seen; one data point isn't enough to know
  if `0.30` needs revisiting or if this session is a genuine (if narrow) real anti-degeneracy
  catch. Needs more real sessions through it before concluding either way.
- ~~A10 ("процесс лечения"/treatment-process) dominance across sessions~~ — **INVESTIGATED
  2026-08-20, real evidence gathered, see [CHI-003](CHI-003-a10-dominance-decay-vs-cumulative.md).**
  `areas_final` (the authoritative whole-session softmax, no decay) shows A10 dominant 14/14 real
  sessions — confirmed real and reproducible. But feeding the same real per-turn data through the
  actual sealed Phase1Theta decay model (`hesperia/extensions/dynamics/phase1.py`, standalone
  read-only diagnostic, no pipeline touched) agrees with `areas_final` in only 5/14 sessions —
  disagreement replacement is almost always A1, a real pattern. Evidence points toward
  "accumulation artifact" (front-loaded treatment-frame discussion never decays out of the
  whole-session sum), not proof — Field Dynamics' constants were never calibrated against TFP data
  (zero references anywhere in the TFP pipeline before this diagnostic). Whether decay-weighted-
  recency or whole-session cumulative mass is the theoretically correct read of "dominant clinical
  theme" is a TFP-theory question, routed to Colombo (`inbox.md`, 2026-08-20) — not resolved here.
  Not closed as "done," closed as "root-caused with real evidence and handed to the right owner,"
  which is what the note above actually asked for.
- **`CHI-001`'s `S`-scale calibration (recalibrate an existing tweak, not a new one)** — raw
  `ts_rank_cd` values ran small (~0.001–0.4) against real sessions, so `S·W` rarely approaches
  1.0. Needs either a real-evidence-based rescaling (percentile-normalize against a real-session
  distribution once there are enough sessions run) or a documented reason the raw scale is fine
  as a diagnostic-only signal. This is exactly the kind of thing the "recalibrate" pass below is
  for — don't force it standalone.
- ~~`ru_2_cleaned`/`en_2_cleaned` are still byte-identical to `original`~~ — **RESOLVED, 2026-08-19,
  final.** Not a "not started yet" item — closed the investigation. Three independent checks
  (Postgres `content_hash`, the 2026-03-24 backup tarball diff, Papra's own `deduped_hash` ingest
  log) all agree these packs never diverged from `original`, ever, at any point checked. Verdict:
  `ru_2_cleaned`/`en_2_cleaned` **are** `original` — use `corpus_pack='original'` as the sole real
  source for any structural/document-level grounding; the other two pack values exist for
  schema/history reasons only, not as a second real corpus. `governance/SPEC-ETHAN-TFP-CORPUS-
  POSTGRES.md` §4 updated with the full evidence chain (brain repo).
  **The real normalized corpus was somewhere else entirely** — `tools/build_tfp_ru_corpus_clean.py`
  (Ethan "TASK 2", 2026-03-20, real lowercase/OCR-strip/sentence-split/dedupe cleaning) produced
  `assets/data/engine_dynamics_v060/corpora/tfp_ru_cleaned_sentences.jsonl` (16826 RU sentences),
  confirmed exhaustively unreferenced anywhere in either repo except its own builder — built for a
  dict-expansion pipeline (`gen_tfp_ru_dict_pack.py`, "TASK 1 seed") that got superseded by the
  Codex stack (`build_ru_tfp_dictionary_stack.py`) before ever consuming it. **Now ingested**,
  2026-08-19: `tfp_corpus.normalized_sentence` (`002_normalized_sentence_v0_1.sql` +
  `ingest_normalized_sentences.py`, commit `4eaa399e`), deliberately separate from
  `source_document`/`document_chunk` since the builder's global dedup destroyed per-sentence
  source provenance — no doc_id to attach rows to, by design.
  **Phase 4a done, 2026-08-19, `v0.6.9` checkpoint**: deterministic structural wiring, free/local
  — `003_concept_link_v0_1.sql` + `link_corpus_to_structure.py`, same `match_dict_a()`/
  `resolve_hit()` matcher already used in production (sealed pack `v0_6_0_clr_v052_5`), run
  against every `normalized_sentence` row and every `document_chunk` row where
  `corpus_pack='original'`. **1,724,099 concept_link rows** (252,986 from sentences, 1,471,113
  from chunks); **134 of 283 concepts** got at least one deterministic link (47% — the literal-
  matching floor Phase 4b is meant to push higher). Area distribution: A10 dominant again
  (826,554 rows, 42%) — independent corpus-wide confirmation of the same A10-dominance pattern
  found earlier this day at the session level, via a completely different measurement.
  **Phase 4b, DONE same day**: `run_ru_tfp_corpus_align` against the real normalized-sentence
  corpus (16826 sentences → 87871 raw phrases → 6000 capped), **882 OpenAI calls, gpt-4o-mini,
  ~66 min wall-clock**. Real result: 983 new dict_a entries, concept coverage **134/283 → 187/283
  (+53)**. Verified functionally live (not just written to disk) two ways: raw lexical match
  count on a real session rose 8470→8491 with the new pack, and `POST /analyze` on `:18881`
  responded correctly post-restart. **Merged and sealed as `v0_6_9`**
  (`assets/calibration/dicts/v0_6_9/` — old sealed `dict_a.jsonl` + the 983 new rows;
  `dict_b`/`dict_c`/`links.jsonl` unchanged, no new concepts, only new phrase links to existing
  ones) — superseding the `v052_5`/`v052_6` internal counter naming entirely, one name for this
  checkpoint. **Live pin on `hesperia-analyze-tfp` (`:18881`)** via a systemd drop-in override
  (`/etc/systemd/system/hesperia-analyze-tfp.service.d/override.conf`, easily reversible — remove
  + restart to roll back to the prior pin). `tfp_module_v1.seal_requested: true` in root
  `VERSION.yaml`. `:18880` (default/core lane) untouched throughout.
  **Phase 4c, in progress (launched 2026-08-19 12:36 UTC)**: same alignment re-run with
  `gpt-5-mini` instead of `gpt-4o-mini` — same corpus, same `max_phrases=6000`/`passes=3` scope,
  for a direct coverage comparison against `v0_6_9`'s 187/283. Required a real code fix first
  (`tools/dict_calibration/openai_json.py`, commit `dca808f1`): gpt-5-family models reject any
  non-default `temperature` on Chat Completions (confirmed live, 400 error) — extended the
  existing model-family detection to skip it for `gpt-5`/`o1`/`o3`/`o4`. Quality spot-check before
  committing to the full run: given 14 real concepts + a real corpus phrase
  ("разрывы альянса"), correctly linked it to the exact matching concept at 0.95 confidence and
  correctly declined the ambiguous ones — sharper judgment than the pass-1-only equivalent check
  would suggest. Real pricing fetched live (not memorized): gpt-5-mini $0.25/1M in, $2.00/1M out
  vs gpt-4o-mini's $0.15/$0.60 — real per-call token usage measured (1202 prompt + 639 completion,
  576 of which are hidden reasoning tokens) puts the full 882-call run at **~$1.39**, not blindly
  estimated. Output: `outputs/dict_calibration/ru_tfp_align_gpt5mini_2026-08-19/` (gitignored).
  **Attempt 1 killed mid-run, real cost lost**: the run's process got torn down by a session/
  harness restart between pass 1 and pass 2 (outside this tool's control — `run_ru_tfp_corpus_align`
  only ever wrote per-pass *summary counts*, not the actual accumulated links, to disk — those
  lived in memory only until the very end). Pass 1 alone (294 real paid calls, ~$0.46 of spend)
  found 1405 raw links / 594 phrases / **97 concepts covered on pass 1 alone** — already beating
  gpt-4o-mini's full 3-pass result on trend — but none of that data was recoverable, only the
  summary counts survived.
  **Fixed the actual gap** (`tools/dict_calibration/ru_tfp_corpus_align.py`, commit `4ea3e093`):
  now writes `pass_N_checkpoint.jsonl` (the real accumulated links, same shape as the final
  output) after every pass, not just counts — a future kill only costs the in-progress pass, not
  everything before it.
  **Attempt 2, relaunched properly detached** (`setsid`+`nohup`+`disown`, `PPID=1`, own session
  leader — survives session/harness restarts this time, confirmed via `ps`). Status file:
  `outputs/dict_calibration/ru_tfp_align_gpt5mini_2026-08-19/RUN_STATUS.txt` (durable, in-repo —
  check that first in a future session, not session-scoped `/tmp` paths). Expected ~6-8h total
  based on attempt 1's pass 1 timing (2h28m for pass 1 alone — gpt-5-mini's reasoning-token
  overhead makes it noticeably slower per call than gpt-4o-mini, not just costlier).
  **Attempt 2 completed clean, ~7.5h total** (started 18:01, pass 1 done 19:20, pass 2 done
  22:23, pass 3/final done 01:28 — matches the checkpoint files timeline exactly, no interruption
  this time). Real final result: **207/283 concepts covered** (2773 unique phrases, 2773 dict_a
  rows) vs gpt-4o-mini's 167/283 — genuinely better, but **not a strict superset**: of 841 phrases
  both runs happened to map, only 181 (22%) agree on the concept. Checked whether disagreement
  correlates with confidence (it does, cleanly): agreement is 73% at confidence≥0.9, falling to
  11% at confidence≥0.4 — the bottom confidence tier alone is ~half of all overlapping phrases
  and nearly all the disagreement. This is a real reliability signal, not noise to wave away.
  **Merge decision**: kept the already-live baseline (134 deterministic + 983 gpt-4o-mini rows,
  187/283, empirically proven in production since this morning) untouched, and added only
  gpt-5-mini rows at **confidence≥0.7** (1853 of 2773 rows — the tier where two independently
  disagreeing models still agree often enough, ~35%+, to be worth trusting) — a **+16 net new
  concepts (187→203/283)**, not the full +51 the unfiltered union would claim. Lower floors were
  computed and rejected: conf≥0.6 gets +31 more concepts but only 20% agreement in that band;
  conf≥0.5 worse still. Renumbered the new rows (`RU-TFP-00984..02836`, no collision — both runs'
  own numbering restarts at `RU-TFP-00001`) and appended in place to the same `v0_6_9/dict_a.jsonl`
  (pre-merge backup kept locally during the operation, not committed — git history is the real
  rollback path). Verified on a real session before touching anything live: gate still passes,
  raw match count rose again (8491→8580), `zero_lex_share` improved (0.218→0.183). Full 11-session
  regression check run before cutover (see below for pass/fail).
  **Phase 4d: collapsed the "aspect N" taxonomy over-split, 2026-08-19/20.** Investigated the 80
  concepts still uncovered after Phase 4c — 79 of them turned out to be numbered "aspect 2/3/4/5"
  sub-splits of already-covered base concepts (31 families, e.g. `Разрывы альянса` covered but
  `Разрывы альянса — аспект 2..5` not), one genuine outlier (`TFP_CLUSTER_005`, not aspect-shaped,
  left untouched). **Correction to an earlier claim before acting on it**: first said these had
  "zero lexical evidence" — checked `dict_c.jsonl`/`links.jsonl`/the loose `dict_a/*.jsonl` stack
  (none of which feed live matching, but hold prior-calibration provenance) and found all 80 *do*
  have some reference there. Sampled the actual entries before trusting that as a real
  contradiction: the "evidence" is either a synthetic self-referential row whose `normalized_form`
  is literally the concept's own label verbatim (`"разрывы альянса — аспект 2"` — not naturalistic
  Russian, nobody says that), or an extremely generic single word (`"лечению"`, `"активизируются"`)
  far too non-specific to reliably indicate one narrow sub-concept over any other. Confirms rather
  than contradicts the original read, more precisely stated.
  **Collapse mechanism**: removed all 550 `dict_b.jsonl` rows for the 79 concept_ids (same-
  concept promotion rows, not 79 rows — some had 100+), 283→204 remaining. Redirected the 169
  `dict_c.jsonl`/`links.jsonl` rows that referenced them to their base concept_id instead of just
  deleting (audit-trail cleanliness — these files aren't runtime-read by the live matcher, but
  leaving dangling concept_id references would be sloppy). Verified no hard-coded `== 283`
  assertion anywhere before removing (`ru_tfp_corpus_align.py` only warns, doesn't fail). Backups
  of all three modified files kept locally during the operation, not committed (git history is the
  rollback path). Verified on a real session before touching anything live: gate still passes,
  `zero_lex_share` identical (0.18254) — exactly expected, since these concepts were never being
  matched to begin with; removing unreachable catalog entries doesn't change matching behavior on
  real text. Full 11-session regression run before cutover (see below for pass/fail).
  **Phase 4e: `TFP_CLUSTER_005` dug into, corrected the earlier "genuine gap" call, 2026-08-20.**
  Turned out to be the same class of artifact as Phase 4d, different generative pattern: label
  "Corpus lexical bundle (devaluation)" is an auto-generated lexical-clustering tag, not a
  hand-authored concept, and it's not unique — `TFP_CLUSTER_004/005/012/013` all share that exact
  label, same area/family (A3/F10). `004` has real substance (12 rows, `"искажения"` — thematically
  plausible) and is covered; `005`'s own thin content (`"взрослом"`, `"и аналитик"`, `"настоящей"`,
  `"обогащает"`, `"средствами"`) has zero semantic connection to devaluation — noise from an
  earlier pass, not signal. Confirmed by checking siblings: of 24 concepts across the whole
  catalog that share a duplicate `preferred_label` with another concept_id (9 groups — found while
  checking this, a wider pattern than just `TFP_CLUSTER_*`, includes `Изменения`/`Управление`
  area/family variants and `splitting`/`devaluation`/`idealization` split across the `TFP_*` and
  `C-NNNN` naming schemes), `TFP_CLUSTER_005` was the *only one* that stayed uncovered — its
  equally-thin siblings `012`/`013` both got some (likely also-noisy) match. Not a real semantic
  gap, just unlucky.
  **Collapsed `005`→`004`** (1 `dict_b.jsonl` row removed, 204→203; nothing in `dict_c.jsonl`/
  `links.jsonl` referenced it, 0 redirects needed — consistent with it being genuinely orphaned).
  Verified on a real session, full 11-session regression before cutover, same rigor as 4d.
  **The other 8 duplicate-label groups (23 concepts): reviewed 2026-08-20, see the dated section
  at the top of this file.** 5 of the 9 groups turned out to be coincidental label collisions
  between unrelated catalog regions, not duplicates (renamed to disambiguate); 2 groups had real
  distinct content on both members (left alone); the remaining group's initial "noise" verdict for
  `TFP_CLUSTER_007/009/012/013` was wrong (a promotion gap, not noise) and the attempted collapse
  was reverted before it stuck — see the top section for the full story and the real follow-on
  candidate it surfaced (promoting `dict_b_tfp.jsonl`'s `alt_labels` + the missing `TFP_DENIAL`
  root concept into the live matcher).
- **Dicts into `tfp_corpus` (Phase 4, `SPEC-ETHAN-TFP-CORPUS-POSTGRES.md` §5) / `pgvector`
  embeddings (Phase 5)** — both still explicitly gated, not started. Phase 4 in particular would
  let `corpus_grounding.py` join concept metadata directly in SQL instead of loading
  `dict_b.jsonl` from disk on every pipeline run.

## Structure/rearrangement candidates (not yet actioned)

- `docs/recipes/` now has three shapes (generic single-param, `params_combo/` PC-NNN,
  `chiron_tweaks/` CHI-NNN). Worth revisiting once there are ~5+ `CHI-*` entries whether that's
  still the right split, or whether some tweaks are really "combo recipes that happen to also add
  a helper module" and the PC/CHI line needs a clearer test.
- `agents/chiron/CHIRON-TFP-DEPLOYMENT-MAP.md` (brain repo) is the node-by-node reference; as
  tweaks accumulate it may be worth adding a "tweaks applied, in order" section there rather than
  only in this backlog + the recipe index, so a future session gets the full sequence in one place.
