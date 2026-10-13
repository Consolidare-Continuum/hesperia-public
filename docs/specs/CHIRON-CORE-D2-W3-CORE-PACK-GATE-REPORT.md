# Chiron independent verification — CORE-D2 W3 core pack gate

**Task:** `CORE-D2-039`  
**Date:** 2026-09-16  
**Verdict:** **PASS**  
**Verified HEAD:** `830f4ffde653fa6b5d49c93f60512774a931f4a9`  
**Parent:** `66fe5df868dad78ed19bd909a04ffcef42994dd2`

## Scope and method

Verified the committed tree from an isolated `git archive` of `830f4ff`. Unrelated dirty files in the primary working tree were not copied into the verification tree and were not edited.

Contracts:

- `docs/specs/ETHAN-CORE-D2-W3-CORE-PACK-GATE-CONTRACT.md`
- `docs/specs/ETHAN-CORE-D2-REAL-DICT-D-PROGRAM-CONTRACT.md`

Committed delta:

- added `docs/specs/GENA-CORE-D2-W3-GATE-ARCHITECTURE-REVIEW.md`;
- added `tests/dict_calibration/test_core_calibration_boundary.py`;
- added `tools/check_core_calibration_boundary.py`;
- expanded `tests/dict_calibration/test_core_pack_gate.py`;
- changed the default callback in `tools/dict_calibration/core_pack_gate.py` to the committed dedicated checker.

## Commands and results

### Commit identity and isolation

```text
git rev-parse HEAD HEAD^
830f4ffde653fa6b5d49c93f60512774a931f4a9
66fe5df868dad78ed19bd909a04ffcef42994dd2

rm -rf /tmp/chiron-core-d2-w3-830f4ff
mkdir -p /tmp/chiron-core-d2-w3-830f4ff
git archive 830f4ff | tar -x -C /tmp/chiron-core-d2-w3-830f4ff
```

Result: clean committed snapshot created; primary-tree dirt excluded.

### Focused boundary and gate tests

```text
python -m pytest -q \
  tests/dict_calibration/test_core_calibration_boundary.py \
  tests/dict_calibration/test_core_pack_gate.py
```

Result: exit `0`; `130 passed` (`12` boundary-checker cases and `118` gate cases).

Collection evidence:

```text
python -m pytest --collect-only -q \
  tests/dict_calibration/test_core_calibration_boundary.py \
  tests/dict_calibration/test_core_pack_gate.py
```

Result:

```text
tests/dict_calibration/test_core_calibration_boundary.py: 12
tests/dict_calibration/test_core_pack_gate.py: 118
```

### Full dictionary-calibration suite

```text
python -m pytest -q tests/dict_calibration
```

Result: exit `0`; `240 passed`.

Collection evidence:

```text
tests/dict_calibration/test_core_calibration_boundary.py: 12
tests/dict_calibration/test_core_pack_gate.py: 118
tests/dict_calibration/test_evaluate_bundles.py: 52
tests/dict_calibration/test_freeze_version.py: 58
```

### Direct boundary checker

```text
python tools/check_core_calibration_boundary.py
```

Result: exit `0`.

```text
PASS: core calibration default-module boundary is clean
```

### CLI surface

```text
python tools/core_calibration_pack_gate.py --help
```

Result: exit `0`; help requires all contracted inputs:

```text
--bundle BUNDLE
--evaluation EVALUATION
--limits LIMITS
--limits-sha256 LIMITS_SHA256
--repo-root REPO_ROOT
```

### Explicit adversarial regression probes

```text
python -m pytest -q tests/dict_calibration/test_core_pack_gate.py -k \
  'missing_or_malformed_manifest or missing_or_failing_boundary_checker or
   explicit_provenance_mock_or_degraded_requires_exact_false or
   mock_quarantined_degraded_and_path_drift_are_rejected or
   reported_scalar_and_family_deltas_are_recomputed or
   external_expected_limits_digest_is_mandatory_and_exact or
   runtime_rows_reject_field_specific_markers or
   candidate_is_revalidated_after_external_callbacks or
   cli_requires_independent_limits_sha256_argument'
```

Result: exit `0`; `25 passed`.

This selection proves fail-closed behavior for missing manifest/checker evidence, mock or degraded provenance, forged scalar and family deltas, stale independently pinned limits identity, field-specific artifact contamination, callback mutation, and missing required CLI input.

```text
python -m pytest -q tests/dict_calibration/test_core_calibration_boundary.py \
  -k 'dynamic-import or relative-parent-import or symlink'
```

Result: exit `0`; `3 passed`.

This selection proves rejection of constant-foldable dynamic TFP import, relative TFP import, and symlink escape.

Direct missing-checker probe:

```text
python -c 'from pathlib import Path; from tools.dict_calibration.core_pack_gate import _default_boundary_checker,_validate_boundary; root=Path("/tmp/chiron-missing-checker-root"); root.mkdir(exist_ok=True); r=_default_boundary_checker(root); print(f"missing_checker_returncode={r.returncode}");
try: _validate_boundary(root,_default_boundary_checker)
except ValueError as e: print(f"missing_checker_fail_closed={e}")'
```

Observed result: checker process return code `2`; `_validate_boundary` raised `ValueError` with `core boundary checker failed`, so no green verdict was possible.

Direct missing-input probe:

```text
python tools/core_calibration_pack_gate.py \
  --bundle /tmp/no-bundle \
  --evaluation /tmp/no-eval \
  --limits /tmp/no-limits \
  --repo-root .
```

Result: exit `2`; argparse reported required `--limits-sha256`.

## Contract findings

- Dedicated core-pack gate remains separate from the numbered full-engine release gate.
- Required A/B/C artifacts, optional fully validated Dict D, strict schemas, sidecars, identities, safe paths, reference closure, finite metrics, frozen limits, deterministic checks, and final callback revalidation are exercised and green.
- Missing checker/input and all requested malformed, forged, stale, contaminated, dynamic-import, relative-import, symlink, and callback-mutation cases fail closed.
- Direct boundary checker passes the committed default package.
- CLI exposes the five required explicit inputs and does not infer an active dictionary selection.
- `assets/config/engine_constants.json` at `830f4ff` contains `resolver.coherence_empirical_weight = 0.0`.
- `git diff --name-only 66fe5df..830f4ff -- core hesperia/engine hesperia/modules assets/config` produced no paths.
- No activation, promotion, active-pointer mutation, runtime module change, or runtime asset change occurred in the committed delta.

## Bounded limitations

- Verification used the committed synthetic and producer-compatibility fixtures; it did not certify a future W4/W5 corpus or a production candidate bundle.
- No activation was attempted because W3 is contractually runtime-inert and activation is forbidden before W9.
- `git diff --check 66fe5df..830f4ff` reports four Markdown trailing-space lines in the added Gena review header. This is non-functional and does not affect gate behavior, deterministic JSON, imports, runtime state, or the PASS verdict.
- Unrelated primary-working-tree modifications and untracked files were excluded from the archived verification tree and remain outside this report.

## Verdict

**PASS.** Committed HEAD `830f4ff` satisfies the CORE-D2 W3 core calibration-pack gate contract and the applicable parent CORE-D2 constraints within the verified scope. The gate is fail-closed for the required adversarial cases, deterministic under its test contract, boundary-clean, runtime-inert, and leaves empirical resolver weight at `0.0`.

SIGNED: Independent Verifier (Chiron) | Hesperia CORE-D2 W3 verification context | 2026-09-16 | CORE-D2-039
