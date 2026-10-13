# Ethan contract — CORE-D2 W3 core calibration-pack gate

**Task:** `CORE-D2-030`  
**Date:** 2026-09-16  
**Parent contract:** `ETHAN-CORE-D2-REAL-DICT-D-PROGRAM-CONTRACT.md`

## Decision

Create a dedicated fail-closed gate for frozen core calibration packs. Do not adapt the numbered full-engine runtime-bundle gate and do not accept its degraded profile as evidence.

The gate evaluates one immutable candidate directory and one separately produced candidate-comparison report. It emits a deterministic JSON verdict. It never mutates, promotes, activates, or rewrites a bundle.

## Inputs

Required command inputs:

- `--bundle PATH`: immutable candidate root containing `manifest.json`;
- `--evaluation PATH`: W2 candidate-comparison report;
- `--limits PATH`: frozen W3 evaluation limits;
- `--limits-sha256 DIGEST`: independently recorded expected limits digest;
- `--repo-root PATH`: explicit Hesperia source root used for boundary and readiness evidence.

No input may be inferred from an environment-selected active dictionary version. All paths are resolved, regular, non-symlink files under their declared roots.

## Manifest and artifact gate

Hard-fail when the manifest is missing, malformed, has a bad sidecar or `bundle_id`, uses an unsupported schema/state, carries mock/quarantine/degraded provenance, or resolves an artifact outside the candidate root.

Validate every artifact declared by the manifest. Required roles at W3 are:

- `dict_a_matcher`;
- `dict_b_canonical`;
- `dict_c_runtime_conversion`.

`dict_d` is optional until W5. When declared, it receives full checksum and strict-schema validation; absence before W5 is not synthesized as success.

Every declared artifact requires:

- a safe relative path;
- exact SHA-256 bytes;
- role-appropriate status;
- non-empty canonical JSONL;
- role-specific row schema;
- deterministic uniqueness and referential-closure checks.

Unknown declared roles are rejected. Required roles cannot be replaced by evidence-only artifacts.

## Candidate-evaluation gate

The evaluation report must:

- use schema `hesperia.dict_calibration.bundle_comparison.v1`;
- bind the candidate `bundle_id` exactly;
- contain at least one stable ordered sample;
- pass its embedded canonical `report_sha256`;
- contain only finite metrics;
- satisfy the frozen limits file without modifying limits after observing the candidate;
- preserve strict identity when the baseline and candidate bundle IDs are equal.

Frozen W3 limits use schema `hesperia.dict_calibration.limits.v1`, bind the
candidate `bundle_id` and evaluation `report_sha256`, and carry a verified
SHA-256 sidecar. The caller supplies the independently recorded expected
limits digest; regenerating a sidecar after editing the limits cannot satisfy
this pin. They define explicit inclusive maxima for absolute accepted,
rejected, coverage, entropy, and per-family-distribution deltas. The gate
recomputes every delta from the baseline and candidate aggregates before
applying limits. Missing, edited, stale, or forged limits and metrics fail
closed.

## Core boundary

Candidate runtime artifacts and their rows must not contain field-specific package paths, corpus labels, modes, concept namespaces, or prompt provenance. The gate calls the dedicated core/default boundary checker; a missing checker or non-zero result is a failure.

This gate consumes the boundary result. It does not redefine the core/default architecture.

## Readiness evidence

The gate requires explicit successful evidence for:

- focused lexical matcher tests;
- focused resolver tests;
- candidate comparison tests;
- resolved-export entry-point availability.

W3 may prove entry-point readiness without producing the W4 corpus. Missing command evidence, failing tests, or a missing export entry point fails closed.

## Verdict contract

Output schema: `hesperia.core_calibration_pack_gate.v1`.

The output contains:

- candidate and evaluation identities;
- frozen limits identity;
- every check as a stable check ID with `pass`, `reason`, and evidence fields;
- `pass: true` only when every required check passes;
- a canonical `verdict_sha256`.

Exit code is `0` only for `pass: true`; all gate failures use a non-zero code. Tool/runtime errors cannot produce a green verdict.

## Separation and authority

- The existing full-engine release gate remains unchanged and authoritative only for its own bundle format.
- The W3 gate is authoritative only for core calibration packs.
- `exploratory_allow_degraded` and equivalent degraded profiles are forbidden as release evidence.
- Felix implements and tests.
- Gena reviews architecture and failure modes.
- Chiron independently proves fail-closed behavior and deterministic verdicts.
- Grace releases W4 only after both reviews are green.

W3 does not change `resolver.coherence_empirical_weight`; it remains `0.0`.

SIGNED: Team Lead (Ethan) | Hesperia CORE-D2 W3 contract context | 2026-09-16 | CORE-D2-030
