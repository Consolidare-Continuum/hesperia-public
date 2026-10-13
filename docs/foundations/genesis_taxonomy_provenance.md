# Genesis taxonomy provenance — where the family names came from

**2026-08-31 update (Chiron)**: the genesis book corpus described below as lost with
`sphereV_0.1_.zip` (Ethan trash-out, 2026-08-07) has been recovered and is now the
**canonical book/author source corpus for default/core Hesperia**, committed at
`hesperia/modules/default/corpus/syzif/` (120 books, sequence #1-120, no gaps/duplicates at
recovery time; `repair_text.py` reconstructed alongside it per the same pipeline documented
below). This is a **canon-source
designation, not a functional-wiring claim**: nothing in the sealed pipeline reads this text
today — the "Stage 2" gap named at the bottom of this doc (extraction + term-to-family
attribution to rebuild Dict A/B/C from real book text) is still unbuilt, no tooling for it
exists anywhere in the repo, and building it is Felix/Gena sealed-pipeline work, not something
this update does. What changed: the source corpus a future Stage 2 build would draw from is no
longer missing, and is now the designated canonical one (not a candidate to be re-sourced or
second-guessed) for that future build.

**2026-09-04 update (Chiron)**: `85 Moral boundaries - Joan C. Tronto` — flagged
`[UNRELIABLE-NEEDS-REEXTRACTION]` on 2026-08-31 (doubled/garbled extraction end to end) — has been
**removed** from `hesperia/modules/default/corpus/syzif/` (`git rm`, dev repo, history retains the
content). The corpus is now **119 books, gap at position #85, not 120/no-gaps** — the "no
gaps/duplicates" property stated above described the corpus's state at recovery, not its current
state. This was a deletion, not the "excluded pending re-extraction" scope-filter CHI-014
originally proposed (see that doc's own 2026-09-04 correction) — 119 is the standing corpus size
for any Stage 2 build.

2026-07-30: the operator decided to adopt the original genesis book-corpus-derived family
taxonomy into the sealed canon matrix, replacing the family names that had been in
`core/topology/invariant_catalog.py`'s `AREA_FAMILY_MAP` since 0.7.0 sealed. This doc records
where that taxonomy came from and what was and wasn't changed, so a future agent doesn't have to
re-derive it the way this session did.

## Source

`sphereV_0.1_.zip` — a genesis-era design archive found in `.cache_to_sort_out/` in the brain
repo (`/data/altitudine/prichindel.com`), dated Oct–Nov 2025 (predates the current Hesperia repo's
naming; "sphere" was the working name before "Hesperia"). Contains:

- `sphere/areas_120_authors_books.csv` / `.xlsx` — 120 real books, exactly 10 per area (12 areas ×
  10 = 120), each tagged with its area, author, title, and notes/tags. This is the source corpus
  the family taxonomy was derived from (real books like *The Ethics of Care*, *Discipline and
  Punish*, *On Liberty*, *Propaganda*, *The Lucifer Effect* — one theme per family concept,
  roughly).
- `sphere/families.txt` — the complete, original 288-row family taxonomy: 12 areas × 24 families,
  tab-delimited `number / area / family`. Confirmed exact 12×24=288 shape, 10 books/area in the
  CSV, before this taxonomy was adopted.
- `sphere/source/books sphere list/` — 125 raw book files (PDF/epub/docx).
- `hesperia/modules/default/corpus/syzif/` — the same ~121 books pre-cleaned to Markdown, with `repair_text.py`/
  `spellcheck_suggestions.py` already run. Better starting point than the raw files for any future
  text-extraction work (Stage 2, not built yet — see below). **Now 119 books** (one removed
  2026-09-04, see update note above) — this bullet describes the corpus's recovery-time state.

## What was adopted vs. kept from the 0.7.0 seal

**Adopted from genesis**: the 24 family *names* within each area (`AREA_FAMILY_MAP`'s values).

**Kept from the 0.7.0 seal**: the area *order* — GOOD, CARE, ORDER, CONTROL, INDIFFERENCE, HARM,
DESTRUCTION, CHAOS, FREEDOM, TRUTH, CREATION, DECEIT. Genesis's own internal ordering (by
family-number block in `families.txt`) is different: GOOD, HARM, TRUTH, DECEIT, ORDER, CHAOS,
FREEDOM, CONTROL, CARE, INDIFFERENCE, CREATION, DESTRUCTION. Since `family_id = area_index × 24 +
local_index`, adopting genesis's area order too would have renumbered all 288 family IDs. That
renumbering was considered and explicitly rejected in favor of keeping the current sealed order —
family ID 0-287 mean the same area they meant before this change, only the name at each position
changed.

Family names were normalized to the file's existing convention (hyphenated Title-Case, no bare
spaces or ampersands) while adopting them: genesis's "Music & rhythm" → "Music-and-rhythm",
"Sandbox testing" → "Sandbox-testing", "Price controls" → "Price-controls", trailing-space typos
in the source (`"Mediation "`, `"Roles "`) trimmed.

## Why this was safe to do

Verified before making the change: nothing outside `invariant_catalog.py` hardcodes specific
family name strings — `core/propagation/invariant_enforcer.py` and `tests/test_invariant.py` only
do structural membership checks (`family_name in AREA_FAMILY_MAP[area_name]`), not name-specific
ones. The production dictionary the names would otherwise need to stay compatible with
(`assets/lexicon/frozen/v06/dict_a_v06.jsonl`) turned out to be synthetic placeholder data with zero real
vocabulary anyway — see `docs/foundations/attribution_layer.md` — so there was no real calibration
to preserve compatibility with.

## What's still open (Stage 2, not built)

The matrix/taxonomy swap only changes *names*. Hesperia's actual dictionaries (Dict A/B/C) still
need to be built from this same genesis book corpus — extracting real text from the corpus above,
attributing terms to families, and computing weights. No PDF/epub/docx extraction tooling and no
term→family attribution tooling exist anywhere in the repo today (confirmed by repo-wide search).
This must be built fresh — the operator was explicit that it must have **no dependency on or
reuse of the TFP module** (`hesperia/modules/tfp`, `research/clinical_tfp`) or any other
extension/module; core stays independent. The operator's framing for this future work: rebuild
the ACB dictionaries (Dict A → Dict C → Dict B, the corpus-driven build direction already
documented in `docs/foundations/corners/lexicon_resolver.md`) sourced from this sphereV corpus.
Not scoped or started in this pass.
