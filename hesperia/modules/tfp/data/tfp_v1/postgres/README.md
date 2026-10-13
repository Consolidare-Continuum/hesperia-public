# TFP corpus Postgres (v1)

**Milestone: TFP v2 / 0.7.0**, promoted 2026-08-20 — see root `VERSION.yaml`'s `tfp_module_v1`
block for the full provenance. The "(v1)" in this title and the `tfp_v1/` directory name are the
stable *data-layout* identifier (`hesperia/modules/tfp/seal.py` and
`tools/validate_version_consistency.py` both depend on that exact string) — not a version claim.
The actual project milestone is v2/0.7.0.

**Instance:** existing `ops-method-pg` · altitudine `127.0.0.1:5433` · db `ops_method`  
**Schema:** `tfp_corpus` (isolated from `ops_method`)  
**Role:** `tfp_corpus_rw` / password `tfp_corpus_dev` — loopback local-dev only  
**Spec:** brain `governance/SPEC-ETHAN-TFP-CORPUS-POSTGRES.md`

## Status 2026-08-18

Phases 0–2 **done**. Live counts: **274** `source_document` / **49,322** `document_chunk`  
(`original` 137, `ru_2_cleaned` 94, `en_2_cleaned` 43). `original` RU = 94 / 14,987 chunks.

Dicts (Phase 4) and pgvector embeddings (Phase 5) stay gated. Do **not** ingest session transcripts. Do **not** DROP/ALTER `ops_method`. No new container.

## Status 2026-08-19 — `v0.6.9` checkpoint: real normalized corpus + structural dict wiring

Resolved the "normalized TFP corpus" investigation (`docs/recipes/chiron_tweaks/BACKLOG.md`):
`ru_2_cleaned`/`en_2_cleaned` confirmed final as content-identical to `original` (not a second
real corpus — three independent checks agree). The one real normalization artifact
(`tools/build_tfp_ru_corpus_clean.py`'s TASK-2 output, orphaned since 2026-03-20) is now live:

- **Phase 3** — `normalized_sentence` (16826 RU rows, no document FK by design — the source
  file's global dedup destroyed per-sentence provenance). `002_normalized_sentence_v0_1.sql` +
  `ingest_normalized_sentences.py`.
- **Phase 4a** — `concept_link`: structural wiring (concept/family/area), not document metadata.
  Runs the same `match_dict_a()`/`resolve_hit()` matcher already used in production, against
  every `normalized_sentence` row and every `document_chunk` row where `corpus_pack='original'`
  — sealed dict pack `v0_6_0_clr_v052_5` (283 concepts), free/local/deterministic, no OpenAI.
  `003_concept_link_v0_1.sql` + `link_corpus_to_structure.py`.
- **Phase 4b, DONE same day** — the *actual* ACB pipeline (`tools/dict_calibration/
  ru_tfp_corpus_align.py`, real OpenAI spend, 882 calls, gpt-4o-mini) run for real against the
  normalized-sentence corpus. 983 new dict_a entries, concept coverage 134/283 → 187/283 (+53).
  Merged (old sealed `dict_a.jsonl` + new 983 rows, `dict_b`/`dict_c`/`links.jsonl` unchanged — no
  new concepts, only new phrase links to existing ones) and **sealed as `v0_6_9`** —
  `assets/calibration/dicts/v0_6_9/`. **This is now the live pin** on `hesperia-analyze-tfp`
  (`:18881`, via systemd drop-in override, restarted + verified with a real request). Superseded
  internal `v052_5`/`v052_6` counter naming — `v0_6_9` is the one name for this checkpoint, not
  scattered pre-promotion labels. `tfp_module_v1.seal_requested: true` in root `VERSION.yaml`.

Tagged `v0.6.9` as the deterministic-wiring checkpoint (Phase 3 + 4a), ahead of whatever comes out
of Phase 4b landing as the "TFP v1 aligned" milestone once verified actually runnable end-to-end
(not just files existing) — see `assets/data/engine_dynamics_v060/VERSION.yaml`.

## Apply schema (Phase 0/1 — already applied)

```bash
bash hesperia/modules/tfp/data/tfp_v1/postgres/apply_schema.sh
```

DSN: `postgresql://tfp_corpus_rw:tfp_corpus_dev@127.0.0.1:5433/ops_method`

## Ingest (Phase 2 — already run)

`ingest.py` reads packs from `tfp_v1/corpus/` (gitignored bulk). On **prichindel**, cleaned packs also live at sibling `hesperia/modules/tfp/data/corpus/{ru,en}_2_cleaned` — copied into `tfp_v1/corpus/` so this layout matches.

Re-ingest only for delta (script is content_hash idempotent). Do not re-run as a default.

## Backup

`/data/hesperia/backups/tfp_corpus/tfp_corpus_latest.dump` on altitudine (`pg_dump -n tfp_corpus -Fc`).

SIGNED: DevOps (Abelard) | tfp_corpus Phase 0–2 verify+copy | 2026-08-18 | loopback
