# Chiron independent verification — CORE-D2 W4 resolved-corpus exporter

**Task:** `CORE-D2-048`  
**Date:** 2026-09-16  
**Verdict:** **PASS**  
**Verified HEAD:** `bc80667678b007a4a2ae9505f732eb9c7f10d4b5`  
**Parent:** `2a57d70d64ed2d90a9c9c66efc7d0976a01395a5`

## Scope and isolation

Verified the committed tree from an isolated `git archive` of `bc80667`. Unrelated
working-tree changes were excluded and were not edited.

Contract authority:

- `docs/specs/ETHAN-CORE-D2-REAL-DICT-D-PROGRAM-CONTRACT.md`
- W4 tasks `CORE-D2-040..048` in the CORE-D2 program register

The verified commit changes only the exporter/resolver implementation and focused
tests:

- `tools/dict_calibration/resolved_export.py`
- `core/engine/lexical_concept/pipeline.py`
- `core/resolver/resolver.py`
- `core/resolver/score_rules.py`
- `tests/dict_calibration/test_resolved_export_schema.py`
- `tests/lexical_concept/test_dict_d_wire.py`

No calibration asset, active pointer, default module, or runtime weight file changed.
`assets/config/engine_constants.json` still records
`resolver.coherence_empirical_weight = 0.0`.

## Independent fixture proof

Constructed a new schema-valid frozen candidate without importing producer test
fixtures. It contained three matcher entries and three canonical concepts, a
candidate-state freeze manifest, exact artifact hashes, frozen source provenance,
resolver/configuration identity, and a valid manifest sidecar.

Candidate evidence:

```text
bundle_id=9016c073e8fb44e2c6ef179054f1773ff193cc373e1749b68ce214091463c9a3
manifest_sha256=eb4a6ab218d4f533ce3f6b3e8c30f48adcc89e3e6e4f7c8da3e11595ab9b9464
```

Constructed two corpus trees independently, with opposite file-creation order, using
two books and four frozen paragraphs. Raw source hashes were recomputed directly:

```text
01-first.md=60ac12479fd01b2eda2903be5eb6b4470da4fe0dbeccdaadd8f033be86371e33
nested/02-second.txt=7a61e465667d7e2df153ac495b98ff76dd9a36015ad4b5fbe8ef5f307252e130
corpus_snapshot_sha256=0a4c6f34d05d0e4e664f782bce9c0dbad8c2879c0e1920588789f09d249580bf
```

The real CLI and canonical resolver emitted:

```text
books=2
paragraphs=4
resolved_spans=6
unresolved_spans=2
resolved_export_sha256=24b1538e8071048a772b94575ead639d0f350c69ffc573cb8772aeaec8c8d9ce
```

Verified independently:

- source bytes and source SHA-256 values match;
- the corpus snapshot digest is the SHA-256 of the canonical ordered source-hash map;
- CRLF/blank-line segmentation produces the four expected paragraph texts;
- every paragraph ID equals
  `SHA256(source_book_sha256 + NUL + decimal_ordinal + NUL + paragraph_text)`;
- every resolved and unresolved offset slices the exact original paragraph surface;
- winners occur in their complete candidate-score vectors;
- the two below-threshold `gamma` spans appear once each in the unresolved partition,
  in canonical order, without overlap with resolved spans;
- candidate bundle ID, manifest hash, resolver version, canonical resolver authority,
  resolver implementation digest, effective configuration digest, segmentation rule,
  and export rule are recorded;
- `dict_d_enabled=false` and `dict_d_effective_weight=0.0`;
- public release export rejects caller-supplied resolver substitution.

## Repeatability and failure proof

Three real CLI runs were byte-identical while varying:

1. corpus argument order;
2. directory traversal/file-creation order;
3. `PYTHONHASHSEED` values `1`, `7`, and `314159`.

The common output digest was
`24b1538e8071048a772b94575ead639d0f350c69ffc573cb8772aeaec8c8d9ce`.

Focused adversarial tests passed for source content/symlink/membership mutation,
candidate manifest/A/B/C and snapshot mutation, resolver semantic-source mutation,
callback code-identity mutation, existing/indirect destinations, fsync plus atomic
install, and temporary-file cleanup after failed installation: **23 passed**.

A direct invalid-UTF-8 CLI run failed before publication, left no destination, and
left no destination-directory temporary file.

Focused provenance/order/canonical-number probes also passed: **6 passed**.

## Full suites

Executed against the isolated committed snapshot:

```text
python -m pytest -q tests/dict_calibration
356 passed

python -m pytest -q tests/lexical_concept
53 passed
```

The dictionary-calibration suite includes **116** resolved-export cases. Both suites
exited `0`.

## LIVE-06 inspection and CORE-D2-049 prerequisite

Real LIVE-06 generated artifacts exist only in the gitignored local work directory
`outputs/dict_calibration/live_v1_2026-09-14/`:

```text
dict_b_draft.jsonl: 63,856 rows
dict_b_anchored.jsonl: 53,272 rows
dict_a_to_b_links.jsonl: 63,104 rows
dict_a_engine.jsonl: 63,104 rows
```

However, no frozen LIVE-06 candidate bundle exists: the work directory has no
candidate `manifest.json`, no `manifest.json.sha256`, and no frozen Dict C artifact.
The tracked `v0_core_syzif_001` material remains the prior offline/mock seal and is
not eligible substitute evidence.

Therefore this report certifies the **W4 exporter implementation** for
`CORE-D2-048`; it does **not** claim a LIVE-06 full-corpus export or a green
`CORE-D2-049` full-corpus gate.

Before `CORE-D2-049` can execute, LIVE-06 A/B/C outputs must be promoted through the
W1 freeze contract into one immutable, schema-valid, non-mock candidate bundle with
artifact/source hashes and manifest sidecar. The exporter must then run over the
complete frozen core corpus, and the resulting canonical export and checksum must be
retained as gate evidence. Missing candidate or full-corpus evidence remains
`PAUSED`, never inferred green.

## Verdict

**PASS.** At committed HEAD `bc80667`, the W4 exporter satisfies the implementation
proof required by `CORE-D2-048`: frozen candidate binding, source and corpus hashes,
stable paragraphs and offsets, unresolved partition, complete provenance, forced
Dict D zero, byte-identical repeatability, mutation rejection, and atomic CLI
publication are green.

SIGNED: Independent Verifier (Chiron) | Hesperia CORE-D2 W4 verification context | 2026-09-16 | CORE-D2-048
