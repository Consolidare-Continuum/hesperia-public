# Deprecated frozen lexicon assets

## `v06/` (formerly `lexicon/frozen/v06`, symlinked as `v0_5_0`)

Retired 2026-07-30. `dict_a_v06.jsonl` is synthetic placeholder data — every token
is a fake string encoding indices (e.g. `access_100_10`, `area10_217_11`), zero
real vocabulary anywhere in the file. It was, until this retirement, the file
`core/attribution/attribution.py` (now `core/attribution/_deprecated/
attribution_v06.py`) loaded as the **production default** attribution dictionary
via `HESPERIA_ATTRIBUTION_MODE=v06` in `runtime/pipeline/analyze.py` — meaning the
production default had never had a real calibrated dictionary.

Core now uses `core.attribution.attribution_shared` unconditionally (no mode
switch) — see `docs/foundations/attribution_layer.md`. That pipeline loads real
curated lexicon content from `lexicon/curated/A_CORE_STAR_MAP_v0_4_1_3.json` +
frozen B0/B1, not this placeholder.

`core.attribution.attribution_shared.load_dict_a_v06()` (an optional fallback
loader used by `runtime/pipeline/r1_r4_pipeline.py`'s surface-map branch) degrades
gracefully when this directory is absent — returns `{}`, and the caller falls
back further to whatever `dict_a` was already resolved. Moving this directory
does not break r1_r4 (verified).

Real dictionaries sourced from the sphereV genesis book corpus are future work
— see `docs/foundations/genesis_taxonomy_provenance.md` and the "Stage 2" scope
in this session's plan history. They will not reuse this placeholder file or its
naming.
