# Task brief: syzif corpus residual OCR cleanup (for Cursor)

**Context**: this is a self-contained brief for a fresh Cursor session — you have no memory of the
work that produced this file. Read this fully before touching anything.

## What this is

`hesperia/modules/default/corpus/syzif/` (dev repo `igareosh/hesperia`, mirrored to prod `Consolidare-Continuum/hesperia`
via the gated `scripts/hesperia/mirror-atomic-to-cc-srl.sh` in the brain repo) is the 120-book
corpus that Hesperia's `core/topology/invariant_catalog.py` `AREA_FAMILY_MAP` (12 areas × 24
families, 288 total) was derived from — see `docs/foundations/genesis_taxonomy_provenance.md`. It
feeds Stage 2 (unbuilt: term/family attribution, Dict A/B/C rebuild), which needs clean text first.

## What's already done (2026-08-31, commits `771a0431` dev / `18fb7ff` CC and everything before them
in the same day's history — read `docs/recipes/chiron_tweaks/BACKLOG.md` top-to-bottom for the full
trail, this brief only summarizes)

1. `repair_text.py` — mechanical: CRLF normalize, `ftfy` mojibake fix, ASCII-hyphen line-wrap joins.
2. `clean_corpus_artifacts.py` — structural: ligature-space breaks (`defi nite`→`definite`),
   soft/Unicode-hyphen line-wrap joins (different codepoints than repair_text.py's ASCII case),
   `(cid:NN)` PDF glyph-ID leaks, running headers/footers (book/chapter titles repeated per page,
   frequency-detected), standalone page numbers, HTML/CD-ROM nav leftovers.
3. `fix_ocr_word_errors_llm.py` — LLM word-level fixes for short (<15 char) single-word typos:
   sends book/author/sentence-context/flagged-word to gpt-4o-mini, fixes only >=70% confidence,
   rejects otherwise. 24,887 applied.
4. `fix_ocr_word_errors_llm_longrun.py` — same idea for long (>=15 char) glued/duplicated
   multi-word runs (a structurally different artifact — text-extraction lost the spaces, and
   sometimes duplicates a word). Needed a different prompt and two independent algorithmic safety
   nets that don't trust the model's self-report:
   - **Coverage check** (`coverage_ratio()`): sequential word-order alignment against the
     correction, not bag-of-letters — verifies every letter of the *original* flagged run is
     accounted for (allowing legitimate word-doubling collapse and the corpus's own "of"→"off"
     rendering quirk).
   - **Symmetric leak check** (same function, same commit `f43aff8f`): every word of the
     *correction* must also be traceable back to the original — catches the model completing from
     its own background knowledge (a real book title, a person's name, a quote) rather than the
     actual corrupted text. Found and fixed after the first version only checked one direction.
   - **Over-completion length guard**: correction can't exceed ~1.3× the original's letter count.
   6,218 applied total across two rounds (first pass conservative old prompt, second pass redone
   fresh with the fixed checks + reinforced prompt — old-prompt corrections were never reused once
   the checks/prompt changed, to avoid mixing quality tiers).

Every tier has a **stated, evidenced residual error rate** in `BACKLOG.md` — nothing was declared
clean by assumption. Known accepted defects (small, catalogued, not hidden): a few real alternate
spellings got "corrected" to more common spellings (`pacificist`→`pacifist`), one meaning-inverting
case (`automaticallylydelegitimized`→"automatically legitimized", dropped "de-"), a couple of real
single compound words got wrongly split (`intertemporally`→"inter temporally").

## What's still open — this is the actual task

### 1. Known architectural problem: position-based tracking degrades across passes

Every script tracks suspects by `file:char_offset`, and every `--apply` shifts every subsequent
character's offset in that file. Progress files (`ocr_llm_progress.jsonl`,
`ocr_llm_longrun_progress.jsonl`) accumulate entries scored at different corpus states, so after a
few apply rounds most cached entries no longer line up with a fresh `find_suspects()` scan (the
scripts *do* safely detect and skip true mismatches before writing — see the `orig != row["word"]`
guard in both apply loops — so this has never corrupted anything, but it does mean a fresh scan and
the cached progress diverge more each round, and "how many suspects are really still open" can't be
answered by grepping the progress file directly; you have to intersect a *fresh* `find_suspects()`
scan against progress by key each time, the way the scripts' own `main()` does internally).

**If you're going to run another apply round on this corpus**, consider fixing this properly first:
key suspects by a content fingerprint (e.g. a hash of a fixed-width window around the flagged span,
or the flagged word + surrounding N chars) instead of raw offset, so progress survives edits. Not
started — this is a real "candidate for fixing" in its own right, not just a footnote.

### 2. The residual long-run pool, sized honestly as of the last check

A fresh scan found only ~1,595 of 6,251 current long-run (>=15 char) suspects still line up with
cached progress at all (see problem #1 — the rest are stale-offset duplicates of already-resolved
content, not confirmed new problems). Of the 1,595 that do line up:

- **1,352 the model outright rejected.** Sampled 20 at random — nearly all are legitimate single
  words the model correctly declined to force-split: real English words
  (`nonmaterialistic`, `parallelepipeds`, `macrostructures`, `irreconcileably` — a real alternate
  spelling), and a cluster of genuine German/Dutch technical vocabulary concentrated in Hayek's
  *Constitution of Liberty* and Peirce's *Collected Papers* (`Sozialversicherung`,
  `Zentralbibliothek`, `rechtshistorisch`, `kapitalistischen`, `Rijksuniversiteit`,
  `Mengenfunktionen`). This is the safe, correct behavior we built toward — **do not** interpret
  this pool as "1,352 unfixed errors." A few plausibly should split
  (`doubleconsciousness`→"double consciousness", `recordsmanagement`→"records management") but the
  conservative default is arguably right given the German/Dutch-term false-positive risk right next
  to them. One item worth a second look: `potentionialist` (possibly OCR for "potentialist") — a
  single instance in the sample, not a confirmed pattern.
- **166 the model proposed a fix for that failed the coverage/over-completion/no-op check.** Every
  one sampled had `correction == word` exactly — the model agreeing these are fine as-is but
  mislabeling the verdict "fix" instead of "reject". Not real defects; already correctly excluded.

**Net read**: there is not much real remaining garbling in the long-run pool. A further round
(bigger context window, stronger model) would likely mostly reconfirm "these are real words," not
find new fixable errors. Diminishing returns, not a known gap — verify this assessment holds before
sinking real API spend into another round; don't just assume it does either.

### 3. Not attempted at all

- The short-token class (`fix_ocr_word_errors_llm.py`) was never re-run with the improved
  algorithm/prompt the long-run script got — it may or may not have similar residual issues; wasn't
  checked, because the failure modes found were specific to the long-run multi-word-glue class.
  Worth a similar audit before assuming the short-token 24,887 is fully clean beyond its stated
  ~85-90% spot-check.
- Stage 2 itself (term/family attribution, Dict A/B/C rebuild) — explicitly out of scope here, a
  much bigger build; per Chiron's own spec (`governance/SPEC-ETHAN-CHIRON-HESPERIA-CALIBRATION-ENTITY.md`
  in the brain repo) sealed-pipeline-adjacent work like this is proposed by Chiron, not implemented
  solo — goes to Felix/Gena after Grace triage, once this corpus is judged trustworthy enough.

## How to work in this repo (learned the hard way this session, don't repeat it)

- **Dev repo** = `igareosh/hesperia`. The canonical up-to-date checkout on this host is
  `/data/hesperia/hesperia` — **not** `/data/workspaces/hesperia`, which was stale by several
  commits mid-session and caused real confusion; `git log -1` both before trusting either one.
- **Prod** ("CC_ hesperia") = `Consolidare-Continuum/hesperia`, checked out at
  `/data/consolidare-continuum/hesperia`. Never edit directly — promote via
  `CC_PUSH_PERMISSION=1 bash scripts/hesperia/mirror-atomic-to-cc-srl.sh` from the **brain repo**
  root (`/data/altitudine/CC_.com`), which needs explicit operator permission in the invoking chat
  per that script's own hard gate. Always use the path `scripts/hesperia/mirror-atomic-to-cc-srl.sh`
  (a symlink) from the brain repo root — the real file lives under `scripts/hesperia/deploy/` and
  invoking it by that longer path breaks its own relative `REPO_ROOT` computation.
- **Before any apply**: dry-run, spot-check a real random sample (not just the first N — that
  under-represents failure modes), quantify, only then apply. Every pass in this file's history
  found something a smaller/lazier check would have missed.
- Test small before running the full corpus — a 60-item free API test caught the confusion-table
  approach's ~35-40% error rate before it touched a single file; always worth the few minutes.

## Cursor pass result (2026-08-31, IDE only — no new scripts)

Session: `execution_host=altitudine`, worktree `/data/hesperia/hesperia`.

| Brief item | Result |
|------------|--------|
| §1 fingerprint keys before next apply | Confirmed needed; **not coded** this pass. Evidence: ~3,120 whole-token progress/`fix` rows still in corpus; Moral boundaries alone ~2,594 (book is doubled extraction — re-extract, don’t patch). |
| §2 long-run residual pool | **Assessment holds** — reject pool ≈ real words + Moral-boundaries noise; no API re-round. |
| §3 short-token re-audit | Progress≠corpus (offset drift). Do not blind-replay JSONL. Named Chiron wording + a few clear English compounds fixed in prose; URL-path tokens held. |
| Stage 2 | Still out of scope. |

Detail + fix table: `BACKLOG.md` entry **2026-08-31 (6th pass)**.

SIGNED: Chiron (Hesperia calibration entity) | task brief for Cursor | 2026-08-31
SIGNED: Cursor | IDE residual wording + brief answers | 2026-08-31 | no new scripts
