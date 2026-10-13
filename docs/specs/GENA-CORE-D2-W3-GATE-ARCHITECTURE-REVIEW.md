# Gena architecture review — CORE-D2 W3 core calibration-pack gate

**Task:** `CORE-D2-038`  
**Reviewed baseline:** `66fe5df868dad78ed19bd909a04ffcef42994dd2`  
**Final review target:** baseline plus the isolated four-file committed-intent boundary hardening  
**Date:** 2026-09-16  
**Contracts:** `ETHAN-CORE-D2-W3-CORE-PACK-GATE-CONTRACT.md` and `ETHAN-CORE-D2-REAL-DICT-D-PROGRAM-CONTRACT.md`

## Verdict

**APPROVED**

The final committed-intent gate is structurally separated, deterministic, producer-compatible, runtime-inert, and fail-closed against every written-contract failure mode and every previously bounded adversarial probe. The direct checker, CLI shape, focused boundary/gate suite, full calibration suite, positive default gate, and contaminated default-gate rejection are green.

## Review history

1. **Initial review — REJECTED:** commit `66fe5df` invoked a boundary-checker path that was absent from the committed tree. The real default callback returned `2`; mocked callback tests could not supply release evidence.
2. **Fix intent reviewed:** the uncommitted committed-intent patch adds `tools/check_core_calibration_boundary.py`, six dedicated checker cases, one default-callback command/timeout test, and changes the gate callback to the new checker. The direct checker, combined 124 boundary/gate tests, full calibration suite, and positive default gate all pass.
3. **Independent re-review — REJECTED:** semantic bypass probes produce false-green checker and gate verdicts. The fix resolves checker presence and timeout wiring but not the core/default separation guarantee.
4. **AST follow-up reviewed — REJECTED:** the new explicit parent-package import regression is green and `from hesperia.modules import tfp` now fails closed. Equivalent relative import syntax and malformed AST input remain false-green, including at the final default-gate verdict.
5. **Final hardening reviewed — REJECTED:** relative import and malformed-Python probes now fail closed. Bounded follow-up found executable dynamic-import and symlink-directory escapes that remain false-green, including a final green gate verdict for dynamic TFP loading.
6. **Requested disposition reviewed — APPROVED:** all symlinks are rejected; AST validation covers direct, parent, relative, malformed, constant-foldable dynamic imports, and assigned TFP/module markers while preserving the canonical default-module docstring. Exactly the preceding bounded probes now reject, and the positive default gate remains green.

## Contract findings

### Dedicated gate and release-gate separation

- `tools/dict_calibration/core_pack_gate.py` is an offline validator with no import from `hesperia.engine.calibration_release_gate`.
- `tools/core_calibration_pack_gate.py` is a dedicated CLI and imports only the new core-pack evaluator.
- `hesperia/engine/calibration_release_gate.py` is byte-identical before and after the reviewed commit: SHA-256 `0c52af5d16606883e3f9ada5ec1d41a19fb880d11ec9e704929c63a8a145d118`.
- The existing full-engine gate remains separately exercised by its existing CI command and profile.

**Finding:** PASS.

### Manifest, artifacts, evaluation, and frozen limits

- Manifest identity, sidecars, strict states, provenance, required A/B/C roles, optional fully validated Dict D, safe relative paths, artifact hashes, row schemas, uniqueness, and Dict B reference closure fail closed.
- Evaluation validation binds the candidate bundle, verifies canonical `report_sha256`, ordered samples, finite metrics, same-bundle identity, and recomputed signed candidate-minus-baseline deltas.
- Limits validation binds both candidate and evaluation identities, verifies the sidecar, requires the caller's independently pinned digest, and applies inclusive scalar and per-family maxima.
- Final revalidation detects candidate, evaluation, or limits mutation after external callbacks.

**Finding:** PASS.

### Producer compatibility

- The gate accepts the manifest shape emitted by `tools.dict_calibration.freeze_version.freeze`, including all current evidence roles.
- Required runtime roles cannot be replaced by evidence roles.
- `tools.dict_calibration.resolved_export` supplies the W4 entry-point contract and `--help` readiness surface without pretending that the W4 exporter is implemented.

**Finding:** PASS.

### Deterministic verdict and failure modes

- Stable check IDs are ordered `01_manifest` through `08_revalidation`.
- Success requires every check to pass.
- Both green and failed verdicts include a canonical `verdict_sha256`.
- CLI exit is `0` only for a green verdict, `1` for a gate failure, and non-zero for CLI/serialization errors.
- Missing, malformed, forged, stale, field-specific candidate artifacts, callback-mutated, mock, quarantined, degraded, non-finite, path-drifted, and readiness-failing inputs are covered.

**Finding:** PASS.

### Dedicated core/default boundary checker

- The checker is self-contained, has a CLI, fails when `hesperia/modules/default` is absent, scans paths deterministically, and reports unreadable Python source.
- The gate invokes it through the explicit `--repo-root` context with capture, non-throwing process evidence, and the existing finite 300-second timeout.
- Its final regression set covers a clean package, direct dotted TFP imports/string references, parent-package and package-relative import syntax, malformed Python, assigned domain markers, constant-foldable dynamic imports, TFP path names, and symlink directories.
- It now detects `from hesperia.modules import tfp` through AST validation.
- It now detects package-relative AST imports such as `from .. import tfp`.
- AST `SyntaxError` now fails closed.
- Executable constant-foldable package construction such as `importlib.import_module("hesperia.modules." + "tfp")` is rejected.
- Assigned TFP/module markers are rejected without rejecting the canonical default-module docstring.
- Every symlink encountered under `hesperia/modules/default` is rejected before content traversal.
- Check `06_boundary` therefore receives fail-closed process evidence for every bounded contamination probe.

**Finding:** PASS.

### CLI and Python API shape

- CLI requires `--bundle`, `--evaluation`, `--limits`, `--limits-sha256`, and `--repo-root`.
- Python API is the keyword-only `evaluate_core_pack(...)` and supports injected subprocess and boundary callbacks for deterministic testing.
- Input selection does not infer an active runtime dictionary version.

**Finding:** PASS.

### CI isolation

- The new CI block invokes the dedicated CLI help and only `tests/dict_calibration/test_core_pack_gate.py`.
- Existing full-engine release-gate CI remains separate.
- The fix-intent callback test verifies the new checker command and timeout, but it mocks process success.
- The dedicated boundary suite and full calibration suite were executed independently for final acceptance; this preserves the gate's CI isolation rather than coupling it to the full-engine release gate.

**Finding:** PASS.

### Runtime and activation boundary

- The commit adds no file under `core/`, `hesperia/engine/`, `hesperia/modules/`, runtime assets, or active-pack selection.
- No promotion, activation, pointer mutation, bundle rewrite, or runtime loading is performed.
- `assets/config/engine_constants.json` remains unchanged with `resolver.coherence_empirical_weight: 0.0`.

**Finding:** PASS.

## Initial executed evidence

All commands ran against an isolated archive of committed HEAD, not the dirty working tree.

- Focused gate suite: `117` tests passed.
- Full `tests/dict_calibration` suite: `227` tests passed.
- Python compile check for the three added modules: passed.
- Commit diff check: passed.
- CLI `--help`: passed and exposed all five required inputs.
- Default boundary callback: returned `2` because `tools/check_core_default_tfp_boundary.py` is absent.

Independent probes:

| Probe | Result |
|---|---|
| Missing manifest | Rejected by `01_manifest` |
| Forged aggregate delta with refreshed report hash | Rejected by `03_evaluation` |
| Edited limits with refreshed sidecar but stale independent digest | Rejected by `04_limits` |
| Field-specific runtime artifact with all enclosing hashes rebound | Rejected by `02_artifacts` |
| Candidate artifact mutation during boundary callback | Rejected by `08_revalidation` |

## Fix re-review evidence

The fix was tested in an isolated archive of `66fe5df` with only these committed-intent files overlaid:

- `tools/check_core_calibration_boundary.py`;
- `tests/dict_calibration/test_core_calibration_boundary.py`;
- `tools/dict_calibration/core_pack_gate.py`;
- `tests/dict_calibration/test_core_pack_gate.py`.

Results:

- Direct checker on the real isolated tree: passed.
- Boundary checker plus gate suite: `124` tests passed.
- Full `tests/dict_calibration` suite: `234` tests passed.
- Positive default gate with real checker and real readiness callbacks: passed all checks `01_manifest` through `08_revalidation`.
- Syntax and diff whitespace checks: passed.

Independent semantic probes:

| Default-module contamination | Direct checker | Default gate |
|---|---|---|
| `from hesperia.modules import tfp` | False green | False green at `06_boundary`; final `pass: true` |
| `CALIBRATION_DOMAIN = "tfp"` | False green | Boundary authority is bypassed |
| `"hesperia.modules." + "tfp"` | False green | Boundary authority is bypassed |

## Final AST re-review evidence

The AST follow-up was tested in a fresh isolated archive of `66fe5df` with only the four boundary/gate committed-intent files overlaid.

Results:

- Direct checker on the real isolated tree: passed.
- Boundary checker plus gate suite: `125` tests passed.
- Full `tests/dict_calibration` suite: `235` tests passed.
- Positive default gate with real checker and real readiness callbacks: passed all checks `01_manifest` through `08_revalidation`.
- Syntax and diff whitespace checks: passed.

Re-run semantic probes:

| Probe | Result |
|---|---|
| `from hesperia.modules import tfp` | Correctly rejected |
| `from .. import tfp` inside `hesperia/modules/default` | False green |
| `CALIBRATION_DOMAIN = "tfp"` | False green |
| `"hesperia.modules." + "tfp"` | False green |
| Malformed `from hesperia.modules import tfp as` | False green after AST `SyntaxError` |
| Default gate over the relative-import contamination | False green at `06_boundary`; final `pass: true` |

## Final hardening re-review evidence

The final hardening was tested in another fresh isolated archive of `66fe5df` with only the four boundary/gate committed-intent files overlaid.

Results:

- Direct checker on the real isolated tree: passed.
- Boundary checker plus gate suite: `127` tests passed.
- Full `tests/dict_calibration` suite: `237` tests passed.
- Positive default gate with real checker and real readiness callbacks: passed all checks `01_manifest` through `08_revalidation`.
- Syntax and diff whitespace checks: passed.

Bounded adversarial probes:

| Probe | Result |
|---|---|
| `from hesperia.modules import tfp` | Correctly rejected |
| `from .. import tfp` | Correctly rejected |
| Malformed Python | Correctly rejected |
| `CALIBRATION_DOMAIN = "tfp"` | False green |
| `importlib.import_module("hesperia.modules." + "tfp")` | False green |
| Symlinked default-module directory escaping to TFP source | False green |
| Default gate over dynamic-import contamination | False green at `06_boundary`; final `pass: true` |

## Final bounded decision evidence

The requested disposition was tested in a fresh isolated archive of `66fe5df` with only the four boundary/gate committed-intent files overlaid. Probe scope was held exactly to the preceding bounded set.

Results:

- Direct checker on the real isolated tree: passed.
- CLI `--help`: passed.
- Boundary checker plus gate suite: `130` tests passed.
- Full `tests/dict_calibration` suite: `240` tests passed.
- Positive default gate with the real checker and real readiness callbacks: passed all checks `01_manifest` through `08_revalidation`.
- Syntax and diff whitespace checks: passed.

Exact bounded probes:

| Probe | Final result |
|---|---|
| `from hesperia.modules import tfp` | Rejected |
| `from .. import tfp` | Rejected |
| Malformed Python | Rejected |
| `CALIBRATION_DOMAIN = "tfp"` | Rejected |
| `importlib.import_module("hesperia.modules." + "tfp")` | Rejected |
| Symlinked default-module directory escaping to TFP source | Rejected |
| Default gate over dynamic-import contamination | Rejected at `06_boundary`; final `pass: false` |

## Approval scope

**APPROVED** for W3 architecture and failure-mode acceptance against the written W3 and parent contracts. Approval applies to the exact four-file committed-intent hardening reviewed with baseline `66fe5df`; it does not approve unrelated working-tree changes. No runtime weight, activation, promotion, existing full-engine release-gate, or sealed-engine behavior changed.

SIGNED: Main Developer (Gena) | Hesperia CORE-D2 W3 architecture context | 2026-09-16 | CORE-D2-038
