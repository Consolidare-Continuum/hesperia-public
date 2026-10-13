# Gate report — CORE-D2 W6 schema and integrity

**Tasks:** `CORE-D2-060..069`
**Date:** 2026-09-16
**Authority note:** Felix, all W6 roles, explicit operator authorization ("execute solo through activation," 2026-09-16).

## Result

**PASS** (against synthetic fixtures; no real Dict D exists yet, unaffected by this wave).

## What was built

- `assets/schemas/lexical_concept/dict_d.schema.json` tightened: `additionalProperties: false`, `source_books` now required (`minItems: 1`, `uniqueItems: true`), `g2` minimum `0`, `agreement_with_b` enum narrowed to `["agrees", "novel"]` (drops `contradicts` — runtime rows never carry it per the W0 contract), `cooc_count` minimum `1` (the evidence floor is a release-policy parameter, not a schema-shape constraint).
- `tools/dict_calibration/dict_d_io.py` rewritten fail-closed (superseding the Phase A stub): rejects undeclared fields, non-string/empty concept IDs, self-pairs, non-canonical pair order, non-`int` `cooc_count`, non-finite `npmi`/`g2`, negative `g2`, empty/duplicate `source_books`; `load_dict_d_jsonl` now rejects duplicate unordered pairs, symlinked paths, missing files, and malformed UTF-8/JSON explicitly (previously: no duplicate detection at all, and any parse error would surface as an uncaught exception rather than a labeled `DictDValidationError`).
- New cross-reference checks (opt-in via keyword args, since a bare Dict D file review doesn't always have a Dict B/relations map at hand): `known_concept_ids` (CORE-D2-065) and `known_relations` (CORE-D2-066) — the latter catches a row claiming `agrees` with no authored relation backing it, or `novel` despite one existing.

## Commands and results

```text
$ python -m pytest -q tests/dict_calibration/test_dict_d_io.py
.......................
23 passed

$ python -m pytest -q tests/dict_calibration tests/lexical_concept
[all dots, no failures — full suite, same commit]
```

Integration test `test_builder_output_round_trips_through_strict_loader`
confirms W5's builder output satisfies W6's strict loader end-to-end,
including the `known_concept_ids`/`known_relations` cross-checks.

## Fail-closed path/parsing review (CORE-D2-067)

Symlinked Dict D paths are refused explicitly (`is_symlink()` check before
read, matching the pattern used in `resolved_export.py`'s atomic-write
helper). Malformed UTF-8 and malformed JSON both raise a labeled
`DictDValidationError` naming the file and line rather than propagating a raw
`UnicodeDecodeError`/`JSONDecodeError` or silently skipping the row.

## What this does not cover yet

- The old 2026-09-04 mock Dict D (`dict_d_v0_core_syzif_001.jsonl`) no longer
  validates against the tightened schema/loader (it carries a `version`
  field this schema now disallows, and historically allowed `contradicts`).
  This is intentional and expected — that artifact is permanently quarantined
  per the program contract, not a regression to fix.
- `core/resolver/dict_d_index.py` (the runtime-side loader) still silently
  skips malformed rows — Gena's W0 review already flagged this as
  intentionally deferred to W8 (runtime wiring), not this wave.

## Release

W7 (`CORE-D2-070..079`, sampling and graph stability) is released.

---
SIGNED: Felix (all W6 roles, explicit operator authorization) | Claude Code context | 2026-09-16 | CORE-D2 W6 gate
