# Deprecated lexicon assets

Orphaned/superseded lexicon assets — no runtime or tooling importer as of the 2026-07-30
consolidation pass (see `docs/archive/ARCHIVE-MANIFEST.md`).

- `A_CORE_STAR_MAP_v0_4_1_1.json` — only loaded by the now-retired
  `core/attribution/_deprecated/lexical_loader.py`. (A checksum-pinned copy remains at
  `lexicon/frozen/A_CORE_STAR_MAP_v0_4_1_1.json` as an immutable release artifact — that one was
  intentionally left in place, not archived, since `lexicon/frozen/` is a release ledger.)
- `A_CORE_STAR_MAP_v0_4_1_2.json` — zero references anywhere in the repo. Superseded by
  `_v0_4_1_3.json`, the live asset used by `structural.py`/`attribution_shared.py`.
- `A_CORE_STAR_MAP_v1.json` and `B_SURFACE_LEX_FIELD_v1.json` — referenced only by the
  now-retired `lexical_loader.py` and the standalone, non-runtime
  `lexicon/validation/validate_lexical.py`.

Live equivalents: `lexicon/curated/A_CORE_STAR_MAP_v0_4_1_3.json`,
`lexicon/frozen/v06/dict_a_v06.jsonl`. See
[docs/foundations/attribution_layer.md](../../docs/foundations/attribution_layer.md).

`FAMILY_SPEC_v0_6.json` was intentionally **not** archived — it's used by live tooling
(`lexicon/validation/validate_dict_a.py`), not dead.
