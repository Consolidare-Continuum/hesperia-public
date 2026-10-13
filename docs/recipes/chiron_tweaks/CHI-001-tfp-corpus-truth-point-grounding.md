# CHI-001 — TFP contradiction-grounding truth-point score (L/S/W/T)

## 1. Task/goal

Give each topology-derived contradiction pair a second, independent evidence channel for
"is this concept actually present in the corpus" — on top of, not instead of, the existing
literal family-grain lexical check — so a pair the literal check calls ungrounded but the
corpus genuinely supports isn't silently indistinguishable from one with no support anywhere.

## 2. Theory

The literal family-grounding check (`GROUNDING_GRANULARITY = "family"`,
`runtime/pipeline/run_tfp_file_pipeline.py`) asks one narrow question: did *any* concept in the
same Dict-B family as this pair get a direct lexical hit in the input text. That's a real, useful
signal, but it conflates two different failure modes: the concept genuinely isn't discussed, or
it's discussed using different wording than the dict pack's exact family/area match expects.

The TFP research corpus (`tfp_corpus`, Postgres — 274 files / 49,322 chunks: Klein, Bion,
Kernberg, Clarkin-Yeomans et al.) is real, mostly-authoritative published clinical theory. If a
concept's own canonical label has genuine support somewhere in that corpus, that's independent
evidence the concept is a real, established construct — regardless of whether *this particular
input segment* happened to phrase it the way the family-match expects.

Three pieces, deliberately kept as three separate, honestly-scoped signals rather than folded
into one opaque number:

- **`L`** — the existing binary family-grain check. Cheap, already gates `internal_review`.
- **`S`** — does the concept's dict_b `preferred_label` have real textual support anywhere in the
  corpus (Russian full-text search rank, not raw string similarity — see §3).
- **`W`** — how many *independent source documents* corroborate that support, not just how many
  chunks. A concept surfacing across several different books/authors is functionally more
  established than one traceable to a single obscure mention; this lets the corpus's own
  redundancy stand in for an authority judgment instead of someone asserting which sources count
  more, operationalizing "mostly true, with exceptions" without hand-curating a source-trust list.
- **`T = max(L, S·W)`** — a ceiling-raise, not a blend. A pair the literal check already grounds
  stays grounded no matter what the corpus channel says; this can only add confidence to an
  otherwise-ungrounded pair, never take confidence away from a grounded one.

Full write-up, cross-referenced from here and there: `docs/foundations/parameter_synergies.md` §8.

## 3. Capability used / added

| Piece | Where |
|---|---|
| Corpus query | `hesperia/modules/tfp/data/tfp_v1/postgres/corpus_grounding.py::corpus_support()` |
| dict_b label lookup | same file, `load_concept_labels()` — reads whatever `dict_b.jsonl` `resolve_dict_file()` currently resolves to |
| Wiring into reconciliation | `runtime/pipeline/run_tfp_file_pipeline.py::_build_contradiction_reconciliation()` — new `dict_b_path` parameter, per-pair `truth_point` block in `per_contradiction_audit`, session-level `truth_point_accumulation` in `lexical_support` |
| Storage queried | `tfp_corpus.document_chunk` (Postgres), `fts_ru`/`ts_rank_cd` — **not** `similarity()`/trigram: tried first, `EXPLAIN ANALYZE` showed the trigram index pre-filter returning thousands of loosely-matching rows before scoring (~4s/concept); FTS's `@@` is a real boolean index condition (~14ms/concept, ~100x faster) and does genuine Russian lexeme stemming instead of raw character-trigram overlap. |
| Tests | `tests/test_tfp_corpus_grounding.py` |

## 4. Config

No new env vars. `corpus_grounding.py`'s `DSN` is a hardcoded loopback-dev connection
(`127.0.0.1:5433`, role `tfp_corpus_rw`) matching `SPEC-ETHAN-TFP-CORPUS-POSTGRES.md`'s Phase 0/1
provisioning — same posture as that spec, not a new secrets surface.

## 5. Invocation

Automatic — runs as part of `_build_contradiction_reconciliation()`, which every
`gena_tfp_bundle_run.py` / `run_tfp_file_pipeline.py` invocation already calls when producing
`13_contradiction_reconciliation.json`. Nothing extra to pass.

```bash
HESPERIA_DLCR_STRUCTURAL=1 HESPERIA_CALIB_DICT_VERSION=v0_6_0_clr_v052_5 \
python3 tools/gena_tfp_bundle_run.py -i <input.md> --with-kme --with-triz --with-topology \
  --gate-profile internal_review
```

## 6. Expected output shape

`13_contradiction_reconciliation.json` → `sessions[].lexical_support.truth_point_accumulation`
(session-level, mean `T` across all canonical contradictions) and, per pair, `per_contradiction_audit[].truth_point`:

```json
{"L": 0.0, "S": 0.411765, "W": 1.0, "T": 0.411765, "corpus_status": ["ok", "ok"]}
```

`corpus_status` per concept is one of `ok` (query ran, may still be S=0 if nothing matched),
`no_label` (concept not in the currently-resolved dict_b), `unavailable` (Postgres unreachable —
fails open, `S=W=0`, `T` reduces to `L`), `query_error`.

## 7. Validation evidence

- `tests/test_tfp_corpus_grounding.py` (3 cases: no-round-trip-without-a-label,
  missing-file-handling, first-label-wins) + `tests/test_tfp_contradiction_family_grounding.py` +
  `tests/test_calibration_release_gate.py` — 12 passed, re-run same session as this recipe.
  Broader calibration suite (`test_dict_calibration_golden`, `test_field_dynamics_calibration`,
  `test_threshold_calibration`, `test_tfp_file_pipeline_load`) also green, no regressions.
- Real end-to-end runs, two different real sessions (2026-08-18, not synthetic fixtures):
  - `1-11-09-2023`: `truth_point_accumulation=0.460456`, 46/340 pairs rescued (`T>L`).
  - `14-12-2023`: `truth_point_accumulation=0.082802`, 74/391 pairs rescued, but starting from a
    much worse `zero_lexical_evidence_share=0.928389` — the metric tracks the underlying
    grounding gap's direction across genuinely different sessions, not a constant.
- **Honest limit, stated plainly, not glossed over**: observed `S` values ran small (~0.001–0.4),
  so `S·W` rarely approaches 1.0 in practice — this is a real, differentiated diagnostic signal
  today, not yet strong enough to flip a gate verdict on its own. `T` is **not** wired into
  `calibration_release_gate.py`'s pass/fail logic, deliberately, pending real calibration evidence
  on what `S`'s scale should mean (same "don't gate on an unvalidated number" discipline as every
  other threshold decision this repo has made this week).

## 8. Rollback

No rollback needed to *disable* — if `tfp_corpus`/Postgres is ever unreachable, every concept
gets `S=0`/`W=0`/`status=unavailable` automatically and `T` reduces to `L` everywhere, i.e. the
pipeline behaves exactly as it did before this tweak existed. To remove the code path entirely:
revert Hesperia commit `89b644e0`.

---
SIGNED: Chiron | Claude Code context (Felix engine) | 2026-08-18 | first Chiron-tweaks recipe
