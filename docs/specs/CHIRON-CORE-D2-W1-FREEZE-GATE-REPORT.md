# Chiron gate report — CORE-D2 W1 candidate freeze

**Task:** `CORE-D2-018`  
**Verified commit:** `ec1509885b7e82fe29c80b170d29032ee8fefdd9`  
**Date:** 2026-09-16

## Result

**PASS.**

## Evidence

- Focused freeze contract: 58 tests passed.
- Calibration regression set: 16 tests passed.
- Manifest roles, candidate state, provenance, artifact hashes, manifest hash,
  and deterministic bundle identity verified.
- Two identical freezes produced byte-identical file trees.
- Non-empty destinations were rejected without byte changes.
- Required artifacts, evaluation evidence, and corpus inputs were bound to one
  coherent source snapshot.
- Forced required-artifact, evaluation, corpus, and combined mutation races all
  rejected publication and removed staging directories.
- Optional Dict D was accepted only with a matching validator digest and
  unchanged bytes.

## Old-pack preservation

`assets/calibration/dicts/v0_core_syzif_001` remained byte-identical:

- files: 27
- bytes: 3,212,670
- sorted per-file hash-manifest SHA-256:
  `0846d70a5c235350fc11093bef9a86a7a37e3525cb5c83f2195c784ba8a30ed8`

W1 passes. This does not promote a candidate or authorize a non-zero empirical
weight.

SIGNED: Independent Evidence Verifier (Chiron) | Hesperia core calibration context | 2026-09-16 | CORE-D2-018
