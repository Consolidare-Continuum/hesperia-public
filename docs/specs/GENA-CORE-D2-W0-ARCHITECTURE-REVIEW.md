# Gena review — CORE-D2 W0 resolver semantics and Class A boundary

**Task:** `CORE-D2-008`  
**Reviewed:** 2026-09-16  
**Contract:** `ETHAN-CORE-D2-REAL-DICT-D-PROGRAM-CONTRACT.md`

## Evidence

The pre-review implementation is inert and is not an acceptable model for the
real runtime path:

- `core/resolver/resolver.py` passes sibling candidates from one lexical hit to
  `coherence_from_empirical`;
- `core/resolver/context.py` computes over those sibling IDs;
- `core/resolver/dict_d_index.py` returns an empty index for a missing file and
  skips malformed rows instead of validating a manifest-pinned artifact;
- `tests/lexical_concept/test_dict_d_wire.py` proves weight-zero safety and the
  current sibling behavior, not paragraph-context correctness;
- required pair/version/hash/signal/weight/contribution trace fields are absent.

## Initial verdict

**REJECTED pending contract correction.** Sibling candidates are not resolved
paragraph evidence. Fail-open loading, undefined aggregation, per-hit loading,
mock/degraded inputs, and missing traces are forbidden implementation paths.

## Correction accepted into W0

The corrected Ethan contract now locks:

1. deterministic two-pass paragraph resolution with fixed baseline winners;
2. context from other resolved hits in the same paragraph, never siblings;
3. strongest-positive-edge aggregation with negative NPMI excluded from
   runtime penalty semantics;
4. identical immutable context input for both resolver call paths;
5. manifest-pinned, fail-closed loading and complete empirical traces;
6. Class A placement: pure lookup/scoring in `core/resolver/`, lifecycle and
   integration in default calibration, build/review/gate tooling outside core;
7. no field-specific corpus or branch behavior in the universal path.

## Final verdict

**ACCEPT W0 architecture contract.** This accepts the corrected design boundary,
not the current inert implementation. W1+ implementation remains gated and must
prove paragraph context, sibling exclusion, both call paths, trace completeness,
manifest integrity, malformed-input rejection, and strict weight-zero identity.

SIGNED: Main Developer / Architecture Reviewer (Gena) | Hesperia core/default context | 2026-09-16 | CORE-D2-008
